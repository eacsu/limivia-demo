"""麦克风音量控制 PWM 亮度，录音仅在内存处理。

参数见根目录 demos/config.py / .env；运行 python demos/demo04.py。
"""


from math import exp, log10
from time import monotonic, sleep

import numpy as np
import sounddevice as sd
from limivia import Limivia, LimiviaError, TransportKind

from config import (
    PORT, LED_PIN, PWM_FREQUENCY, PWM_RESOLUTION, POLL_INTERVAL, NOISE_DB, LOUD_DB,
)

# dBFS 为数字音频相对满幅电平，不是声压级。降低 LOUD_DB 会更容易点亮。


def sound_to_duty(rms: float) -> float:
    db = 20 * log10(max(rms, 1e-9))
    return 100 * min(1.0, max(0.0, (db - NOISE_DB) / (LOUD_DB - NOISE_DB)))


def main() -> None:
    microphone = sd.query_devices(kind="input")
    sample_rate = int(microphone["default_samplerate"])
    # 回调只计算最新能量，不执行串口通信或打印，避免阻塞音频线程。
    latest = (0.0, monotonic(), False)

    def audio_callback(indata, frames, time_info, status):
        nonlocal latest
        rms = float(np.sqrt(np.mean(np.square(indata))))
        latest = (rms, monotonic(), bool(status))

    with Limivia() as client:
        devices = client.devices.list(kind=TransportKind.USB)
        if not any(device.id.casefold() == PORT.casefold() for device in devices):
            raise ValueError(f"未找到 {PORT}，请检查板卡 USB 连接。")
        with (
            client.devices.connect(kind=TransportKind.USB, target=PORT) as board,
            board.pwm.open(LED_PIN, frequency=PWM_FREQUENCY, duty=0, resolution=PWM_RESOLUTION) as led,
            sd.InputStream(
                samplerate=sample_rate,
                channels=1,
                dtype="float32",
                blocksize=0,
                callback=audio_callback,
            ) as microphone_stream,
        ):
            print(f"麦克风：{microphone['name']}")
            print(f"IO{LED_PIN} 声控灯已启动，说话越响越亮；Ctrl+C 关闭。")
            smoothed = 0.0
            last_duty = 0.0
            last_tick = monotonic()
            last_print = last_tick
            try:
                while True:
                    now = monotonic()
                    elapsed = now - last_tick
                    last_tick = now
                    rms, captured_at, audio_warning = latest
                    if not microphone_stream.active or now - captured_at > 1.0:
                        led.set_duty(0)
                        raise RuntimeError("麦克风采集已中断，已关闭 LED。")
                    target = sound_to_duty(rms)
                    # 快速变亮、缓慢熄灭，随音量跳动而不过分闪烁。
                    tau = 0.04 if target > smoothed else 0.20
                    smoothed += (target - smoothed) * (1 - exp(-elapsed / tau))
                    duty = round(smoothed, 1) if smoothed >= 0.5 else 0.0
                    if duty != last_duty:
                        led.set_duty(duty)
                        last_duty = duty
                    if now - last_print >= 0.5:
                        db = 20 * log10(max(rms, 1e-9))
                        print(f"声音 {db:6.1f} dBFS → PWM {duty:5.1f}%")
                        if audio_warning:
                            print("音频采集有丢帧，请减少其他程序负载。")
                        last_print = now
                    sleep(POLL_INTERVAL)
            except KeyboardInterrupt:
                led.set_duty(0)
                print("已关闭 LED，正在释放麦克风和 PWM 资源。")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    except (LimiviaError, sd.PortAudioError, OSError, RuntimeError, ValueError) as exc:
        print(f"运行失败：{exc}")
        print(f"请检查默认麦克风和麦克风权限，并结束占用 {PORT} 的其他程序。")
        for note in getattr(exc, "__notes__", ()):
            print(note)
        raise SystemExit(1) from None
