"""固定速度呼吸灯；运行 python demos/demo03.py，Ctrl+C 退出。"""

from time import monotonic, sleep

from limivia import LimiviaError

from config import BREATH_PERIOD, LED_PIN, POLL_INTERVAL, PORT
from led_common import breath_duty, open_led


def main() -> None:
    with open_led() as led:
        print(f"已连接 {PORT} / IO{LED_PIN}，呼吸周期 {BREATH_PERIOD:g} 秒；Ctrl+C 退出。")
        started = monotonic()
        last_duty = None
        while True:
            duty = breath_duty(((monotonic() - started) / BREATH_PERIOD) % 1)
            if duty != last_duty:
                led.set_duty(duty)
                last_duty = duty
            sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("已停止呼吸灯。")
    except (LimiviaError, OSError, RuntimeError, ValueError) as exc:
        print(f"运行失败：{exc}")
        raise SystemExit(1) from None
