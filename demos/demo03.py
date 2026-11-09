"""十档变速呼吸灯：每按一次加快一档。

参数见根目录 config.py / .env；运行 python demos/demo03.py。
"""

# Allow direct file execution as well as python -m demos.demoXX.
if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "demos"


from math import cos, pi
from time import monotonic, sleep

from limivia import Level, Limivia, LimiviaError, TransportKind

from config import (
    PORT, BUTTON_PIN, LED_PIN, PWM_FREQUENCY, PWM_RESOLUTION, POLL_INTERVAL, DEBOUNCE_SECONDS, BREATH_PERIODS,
)
from limivia.constants import Pull

# 一次完整“暗 → 亮 → 暗”的时间；PWM 载波频率始终为 1kHz。
PERIODS = BREATH_PERIODS


def show_speed(gear: int) -> None:
    period = PERIODS[gear]
    print(f"呼吸档位 {gear + 1}/10：每次 {period:g} 秒（{1 / period:.2f} Hz）")


def main() -> None:
    with Limivia() as client:
        devices = client.devices.list(kind=TransportKind.USB)
        if not any(device.id.casefold() == PORT.casefold() for device in devices):
            raise ValueError(f"未找到 {PORT}，请检查板卡 USB 连接。")

        with (
            client.devices.connect(kind=TransportKind.USB, target=PORT) as board,
            board.gpio.input(BUTTON_PIN, pull=Pull.DOWN) as button,
            board.pwm.open(LED_PIN, frequency=PWM_FREQUENCY, duty=0, resolution=PWM_RESOLUTION) as led,
        ):
            print(f"已连接 {PORT}：IO{LED_PIN} 呼吸灯，IO{BUTTON_PIN} 每按一次加快一档；Ctrl+C 退出。")
            gear = 0
            show_speed(gear)
            phase = 0.0
            last_tick = monotonic()
            changed_at = last_tick
            candidate = None
            stable = None
            armed = False
            last_duty = 0.0
            try:
                while True:
                    value = button.read()
                    if value not in (Level.LOW, Level.HIGH):
                        raise ValueError(f"IO{BUTTON_PIN} 返回无效电平：{value!r}")
                    now = monotonic()
                    # 用实际耗时推进相位，USB 调用延迟不会逐圈累积。
                    # 切档保留当前相位，因此亮度不会突然跳回起点。
                    phase = (phase + (now - last_tick) / PERIODS[gear]) % 1.0
                    last_tick = now

                    if value != candidate:
                        candidate, changed_at = value, now
                    if now - changed_at >= DEBOUNCE_SECONDS and value != stable:
                        stable = value
                        if stable == Level.LOW:
                            armed = True
                        elif armed:
                            gear = (gear + 1) % len(PERIODS)
                            armed = False
                            show_speed(gear)

                    # 余弦曲线平滑起落，再作亮度校正，让暗部变化更自然。
                    brightness = (1 - cos(2 * pi * phase)) / 2
                    duty = round(100 * brightness**2.2, 1)
                    if duty != last_duty:
                        led.set_duty(duty)
                        last_duty = duty
                    sleep(POLL_INTERVAL)
            except KeyboardInterrupt:
                led.set_duty(0)
                print("已关闭呼吸灯，正在释放资源。")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    except (LimiviaError, OSError, RuntimeError, ValueError) as exc:
        print(f"运行失败：{exc}")
        print("串口或引脚被占用时，请先结束其他 Demo 或断开工作台连接。")
        for note in getattr(exc, "__notes__", ()):
            print(note)
        raise SystemExit(1) from None
