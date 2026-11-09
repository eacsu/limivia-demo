"""按钮逐档调节 PWM 亮度，每按一次增加 10%。

参数见根目录 config.py / .env；运行 python demos/demo02.py。
"""

# Allow direct file execution as well as python -m demos.demoXX.
if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "demos"


from time import monotonic, sleep

from limivia import Level, Limivia, LimiviaError, TransportKind

from config import (
    PORT, BUTTON_PIN, LED_PIN, PWM_FREQUENCY, PWM_RESOLUTION, POLL_INTERVAL, DEBOUNCE_SECONDS,
)
from limivia.constants import Pull


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
            print(f"已连接 {PORT}：IO{BUTTON_PIN} 按钮 → IO{LED_PIN} PWM（{PWM_FREQUENCY}Hz）。")
            print("占空比 0%；每按一次增加 10%，100% 后回到 0%。Ctrl+C 退出。")
            duty = 0
            candidate = None
            stable = None
            changed_at = monotonic()
            # 启动时若按钮已按住，先等松开，避免把初始状态算作一次按下。
            armed = False
            try:
                while True:
                    value = button.read()
                    if value not in (Level.LOW, Level.HIGH):
                        raise ValueError(f"IO{BUTTON_PIN} 返回无效电平：{value!r}")
                    now = monotonic()
                    if value != candidate:
                        candidate, changed_at = value, now
                    # 按下和松开都需达到配置的防抖时间，过滤机械触点抖动。
                    if now - changed_at >= DEBOUNCE_SECONDS and value != stable:
                        stable = value
                        if stable == Level.LOW:
                            armed = True
                        elif armed:
                            next_duty = 0 if duty == 100 else duty + 10
                            led.set_duty(next_duty)  # 等待设备确认，失败时不自动重试。
                            duty = next_duty
                            armed = False
                            print(f"PWM 占空比：{duty}%")
                    sleep(POLL_INTERVAL)
            except KeyboardInterrupt:
                led.set_duty(0)
                print("已关闭 PWM 输出，正在释放资源。")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    except (LimiviaError, OSError, RuntimeError, ValueError) as exc:
        print(f"运行失败：{exc}")
        print("串口或引脚被占用时，请先结束 demo01 或断开工作台设备连接。")
        for note in getattr(exc, "__notes__", ()):
            print(note)
        raise SystemExit(1) from None
