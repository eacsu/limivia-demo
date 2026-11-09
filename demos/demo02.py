"""固定频率闪灯；运行 python demos/demo02.py，Ctrl+C 退出。"""

from time import sleep

from limivia import LimiviaError

from config import BLINK_PERIOD, LED_PIN, PORT
from led_common import open_led


def main() -> None:
    with open_led() as led:
        print(f"已连接 {PORT} / IO{LED_PIN}，闪烁周期 {BLINK_PERIOD:g} 秒；Ctrl+C 退出。")
        while True:
            led.set_duty(100)
            sleep(BLINK_PERIOD / 4)
            led.set_duty(0)
            sleep(BLINK_PERIOD / 4)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("已停止闪灯。")
    except (LimiviaError, OSError, RuntimeError, ValueError) as exc:
        print(f"运行失败：{exc}")
        raise SystemExit(1) from None
