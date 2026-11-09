"""GPIO 常亮灯：启动即点亮，Ctrl+C 后熄灭。"""

from time import sleep

from limivia import Level, Limivia, LimiviaError, TransportKind

from config import LED_PIN, PORT


def main() -> None:
    with Limivia() as client:
        devices = client.devices.list(kind=TransportKind.USB)
        if not any(device.id.casefold() == PORT.casefold() for device in devices):
            raise ValueError(f"未找到 {PORT}，请检查板卡 USB 连接。")
        with (
            client.devices.connect(kind=TransportKind.USB, target=PORT) as board,
            board.gpio.output(LED_PIN, value=Level.LOW) as led,
        ):
            try:
                led.write(Level.HIGH)
                print(f"已连接 {PORT} / IO{LED_PIN}，LED 已点亮；Ctrl+C 退出。")
                while True:
                    sleep(1)
            finally:
                led.write(Level.LOW)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("已熄灯，正在释放设备。")
    except (LimiviaError, OSError, RuntimeError, ValueError) as exc:
        print(f"运行失败：{exc}")
        print("请检查 USB 连接，并结束占用串口的其他程序。")
        raise SystemExit(1) from None
