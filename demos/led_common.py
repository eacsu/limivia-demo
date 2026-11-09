"""LED PWM 连接与呼吸亮度计算。"""

from contextlib import contextmanager
from math import cos, pi

from limivia import Limivia, TransportKind

from config import LED_PIN, PORT, PWM_FREQUENCY, PWM_RESOLUTION


@contextmanager
def open_led():
    """按配置连接板卡，退出时尝试关闭 LED 并释放资源。"""
    with Limivia() as client:
        devices = client.devices.list(kind=TransportKind.USB)
        if not any(device.id.casefold() == PORT.casefold() for device in devices):
            raise ValueError(f"未找到 {PORT}，请检查板卡 USB 连接。")
        with (
            client.devices.connect(kind=TransportKind.USB, target=PORT) as board,
            board.pwm.open(LED_PIN, frequency=PWM_FREQUENCY, duty=0, resolution=PWM_RESOLUTION) as led,
        ):
            try:
                yield led
            finally:
                led.set_duty(0)


def breath_duty(phase: float) -> float:
    """输入 0–1 的周期相位，返回经过亮度校正的 PWM 百分比。"""
    brightness = (1 - cos(2 * pi * phase)) / 2
    return round(100 * brightness**2.2, 1)
