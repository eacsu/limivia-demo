"""按钮控制 LED：按下点亮，松开熄灭。

参数见根目录 demos/config.py / .env；运行 python demos/demo01.py。
"""


from time import monotonic, sleep

from limivia import Level, Limivia, LimiviaError, TransportKind

from config import (
    PORT, BUTTON_PIN, LED_PIN, POLL_INTERVAL, DEBOUNCE_SECONDS,
)
from limivia.constants import Pull


def main() -> None:
    # 扫描和连接必须使用同一个 SDK 实例，保留候选设备缓存。
    with Limivia() as client:
        devices = client.devices.list(kind=TransportKind.USB)
        if not any(device.id.casefold() == PORT.casefold() for device in devices):
            names = ", ".join(device.id for device in devices) or "无"
            raise ValueError(f"未找到 {PORT}，请检查 USB 连接；当前候选：{names}")

        with (
            client.devices.connect(kind=TransportKind.USB, target=PORT) as board,
            board.gpio.input(BUTTON_PIN, pull=Pull.DOWN) as signal,
            board.gpio.output(LED_PIN, value=Level.LOW) as led,
        ):
            print(f"已连接 {PORT}：IO{BUTTON_PIN} → IO{LED_PIN}，按下亮、松开灭，Ctrl+C 退出。")
            candidate = None
            changed_at = monotonic()
            confirmed = None
            try:
                while True:
                    value = signal.read()
                    if value not in (Level.LOW, Level.HIGH):
                        raise ValueError(f"IO{BUTTON_PIN} 返回无效电平：{value!r}")
                    now = monotonic()
                    if value != candidate:
                        candidate, changed_at = value, now
                    # 输入稳定达到配置的防抖时间后再更新，减少机械按键抖动。
                    if now - changed_at >= DEBOUNCE_SECONDS and value != confirmed:
                        led.write(value)
                        confirmed = value
                        print(f"IO{BUTTON_PIN}={value} → IO{LED_PIN}={value}")
                    sleep(POLL_INTERVAL)
            except KeyboardInterrupt:
                # 正常退出时先关灯，再由上下文释放本次创建的资源。
                led.write(Level.LOW)
                print("已关闭输出，正在释放资源。")
            # 其他异常交给 SDK 上下文清理，不自动重试失败的写操作。


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    except (LimiviaError, OSError, RuntimeError, ValueError) as exc:
        print(f"运行失败：{exc}")
        print("若串口拒绝访问，请先在工作台断开设备，或关闭串口监视器。")
        for note in getattr(exc, "__notes__", ()):
            print(note)
        raise SystemExit(1) from None
