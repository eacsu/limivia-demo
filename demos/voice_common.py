"""Realtime 麦克风流与单 LED 执行队列。密钥仅发往 OpenAI 官方接口。

协议参考：https://developers.openai.com/api/docs/guides/realtime-conversations
使用 24kHz、单声道 PCM16，麦克风回调不执行网络或板卡操作。
"""

import asyncio
import base64
import json
import queue
from time import monotonic

import sounddevice as sd
from limivia import AsyncLimivia, Level
from config import (
    LED_PIN, OPENAI_API_KEY, PORT, REALTIME_MODEL, TRANSCRIPTION_MODEL,
    VOICE_SAMPLE_RATE, VOICE_BLOCK_SIZE, require_api_key,
)
from async_timeout import timeout
from websockets.asyncio.client import connect


def session_settings(instructions, tools, transcription_only=False):
    return {
        "type": "realtime",
        "output_modalities": ["text"],
        "instructions": instructions,
        "audio": {
            "input": {
                "format": {"type": "audio/pcm", "rate": VOICE_SAMPLE_RATE},
                "noise_reduction": {"type": "near_field"},
                "transcription": {
                    "model": TRANSCRIPTION_MODEL,
                    "language": "en" if transcription_only else "zh",
                },
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 400,
                    "create_response": not transcription_only,
                    "interrupt_response": False,
                },
            }
        },
        "tools": tools,
        "tool_choice": "auto",
    }


async def pulse(led, on_seconds, off_seconds):
    """在设备确认后计时，实际周期会附加少量 USB 往返延迟。"""
    await led.write(Level.HIGH)
    await asyncio.sleep(on_seconds)
    await led.write(Level.LOW)
    await asyncio.sleep(off_seconds)


async def run_agent(title, instructions, tools, handler, transcript_handler=None):
    require_api_key()
    sd.check_input_settings(samplerate=VOICE_SAMPLE_RATE, channels=1, dtype="int16")
    audio = queue.Queue(maxsize=100)  # 最多约两秒，网络堵塞时终止，不截断算式后继续。
    last_audio = monotonic()
    audio_fault = None
    actions = asyncio.Queue(maxsize=64)
    seen_calls = set()

    def callback(indata, frames, time_info, status):
        nonlocal last_audio, audio_fault
        last_audio = monotonic()
        if status:
            audio_fault = "麦克风采集丢帧，已停止；请重新运行。"
        try:
            audio.put_nowait(bytes(indata))
        except queue.Full:
            audio_fault = "网络发送跟不上录音，已停止；请重新运行。"

    async with connect(
        f"wss://api.openai.com/v1/realtime?model={REALTIME_MODEL}",
        additional_headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        open_timeout=20,
        max_size=4 * 1024 * 1024,
    ) as ws:

        async def send(event):
            await ws.send(json.dumps(event, ensure_ascii=False))

        await send(
            {
                "type": "session.update",
                "session": session_settings(
                    instructions,
                    tools,
                    transcript_handler is not None,
                ),
            }
        )
        # 先确认 API 会话配置有效，再申请 GPIO 和打开麦克风。
        async with timeout(20):
            while True:
                event = json.loads(await ws.recv())
                if event["type"] == "error":
                    raise RuntimeError(event["error"].get("message", "Realtime 配置失败"))
                if event["type"] == "session.updated":
                    break

        async with AsyncLimivia() as client:
            devices = await client.devices.list(kind="usb")
            if not any(device.id.casefold() == PORT.casefold() for device in devices):
                raise ValueError(f"未找到 {PORT}，请检查 USB 连接。")
            async with (
                client.devices.connect(kind="usb", target=PORT) as board,
                board.gpio.output(LED_PIN, value=Level.LOW) as led,
            ):

                async def transmit():
                    while True:
                        if audio_fault:
                            raise RuntimeError(audio_fault)
                        if monotonic() - last_audio > 3:
                            raise RuntimeError("麦克风停止提供音频。")
                        try:
                            chunk = audio.get_nowait()
                        except queue.Empty:
                            await asyncio.sleep(0.01)
                            continue
                        await send(
                            {
                                "type": "input_audio_buffer.append",
                                "audio": base64.b64encode(chunk).decode("ascii"),
                            }
                        )

                async def receive():
                    async for message in ws:
                        event = json.loads(message)
                        kind = event["type"]
                        if kind == "error":
                            raise RuntimeError(event["error"].get("message", "Realtime 错误"))
                        if kind == "response.function_call_arguments.done":
                            call_id = event["call_id"]
                            if call_id not in seen_calls:
                                seen_calls.add(call_id)
                                actions.put_nowait((call_id, event["name"], event["arguments"]))
                        elif kind.startswith("conversation.item.input_audio_transcription."):
                            if kind.endswith("failed"):
                                raise RuntimeError("语音转写失败，请重新运行。")
                            if transcript_handler:
                                for text in transcript_handler(event):
                                    actions.put_nowait((None, "morse", text))
                            elif kind.endswith("completed"):
                                print("听到：", event.get("transcript", ""))
                        elif kind == "response.output_text.done":
                            print("智能体：", event.get("text", ""))
                        elif kind == "response.done":
                            response = event["response"]
                            if response.get("status") == "failed":
                                raise RuntimeError(
                                    f"模型响应失败：{response.get('status_details')}"
                                )
                    raise RuntimeError("Realtime 连接已关闭。")

                async def execute():
                    while True:
                        call_id, name, arguments = await actions.get()
                        # 只将参数错误返回模型；设备通信错误终止，不重复闪灯。
                        try:
                            result = await handler(led, name, arguments)
                        except (ValueError, TypeError, KeyError) as exc:
                            result = {"error": str(exc)}
                            print("未执行：", exc)
                        if call_id:
                            await send(
                                {
                                    "type": "conversation.item.create",
                                    "item": {
                                        "type": "function_call_output",
                                        "call_id": call_id,
                                        "output": json.dumps(result, ensure_ascii=False),
                                    },
                                }
                            )
                        actions.task_done()

                tasks = []
                try:
                    last_audio = monotonic()
                    with sd.RawInputStream(
                        samplerate=VOICE_SAMPLE_RATE,
                        channels=1,
                        dtype="int16",
                        blocksize=VOICE_BLOCK_SIZE,
                        callback=callback,
                    ):
                        print(f"{title}：{PORT} / IO{LED_PIN}，已开始监听默认麦克风。")
                        print("语音实时发送至 OpenAI；Ctrl+C 停止。不要同时运行其他 Demo。")
                        tasks = [asyncio.create_task(fn()) for fn in (transmit, receive, execute)]
                        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                        for task in done:
                            task.result()
                finally:
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    try:
                        await led.write(Level.LOW)
                    except Exception:  # noqa: BLE001 — 清理错误不能覆盖原始失败。
                        print("关闭 LED 未获确认，请检查板卡状态。")


def launch(factory):
    try:
        asyncio.run(factory())
    except KeyboardInterrupt:
        print("已停止语音 Demo。")
    except Exception as exc:  # noqa: BLE001 — 顶层统一脱敏，避免认证信息进入堆栈。
        # 不打印完整堆栈或认证请求，防止泄露配置中的密钥。
        message = str(exc)
        if OPENAI_API_KEY:
            message = message.replace(OPENAI_API_KEY, "[密钥已隐藏]")
        print(f"运行失败：{message}")
        raise SystemExit(1) from None
