"""所有 Demo 的统一配置；进程环境变量优先于项目根目录的 .env。"""

import math
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env", override=False)


def _text(name: str, default: str) -> str:
    value = os.getenv(name, default).strip()
    if not value:
        raise ValueError(f"{name} 不能为空，请检查环境变量或 .env。")
    return value


def _number(name: str, default, convert, minimum=None, maximum=None):
    try:
        value = convert(os.getenv(name, str(default)))
    except ValueError:
        raise ValueError(f"{name} 必须是有效的数值。") from None
    if not math.isfinite(value) or (minimum is not None and value < minimum) or (
        maximum is not None and value > maximum
    ):
        raise ValueError(f"{name} 超出有效范围，请检查 config.py 中的限制。")
    return value


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
REALTIME_MODEL = _text("REALTIME_MODEL", "gpt-realtime-2.1")
TRANSCRIPTION_MODEL = _text("TRANSCRIPTION_MODEL", "gpt-4o-transcribe")
PORT = _text("LIMIVIA_PORT", "COM4")
LED_PIN = _number("LED_PIN", 13, int, 0)
PWM_FREQUENCY = _number("PWM_FREQUENCY", 1000, int, 1)
PWM_RESOLUTION = _number("PWM_RESOLUTION", 10, int, 1)
POLL_INTERVAL = _number("POLL_INTERVAL", 0.02, float, 0.001)
BLINK_PERIOD = _number("BLINK_PERIOD", 1.0, float, 0.05)
BREATH_PERIOD = _number("BREATH_PERIOD", 3.0, float, 0.1)
NOISE_DB = _number("NOISE_DB", -55.0, float)
LOUD_DB = _number("LOUD_DB", -15.0, float)
MORSE_UNIT = _number("MORSE_UNIT", 0.10, float, 0.001)
MAX_BLINKS = _number("MAX_BLINKS", 20, int, 1)
# Realtime PCM 输入固定为 24 kHz、单声道、PCM16；每块 20 ms。
VOICE_SAMPLE_RATE = 24000
VOICE_BLOCK_SIZE = 480
BREATH_PERIODS = (6.0, 5.0, 4.0, 3.2, 2.6, 2.1, 1.7, 1.4, 1.1, 0.8)

if LOUD_DB <= NOISE_DB:
    raise ValueError("LOUD_DB 必须大于 NOISE_DB。")


def require_api_key() -> str:
    if not OPENAI_API_KEY:
        raise ValueError("请在根目录 .env 或环境变量中设置 OPENAI_API_KEY。")
    return OPENAI_API_KEY
