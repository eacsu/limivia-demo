"""语音算术闪灯，次数上限由 MAX_BLINKS 配置。

参数见根目录 config.py / .env；运行 python demos/demo05.py。
"""

# Allow direct file execution as well as python -m demos.demoXX.
if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    __package__ = "demos"


import json
from fractions import Fraction

from config import MAX_BLINKS

from .voice_common import launch, pulse, run_agent

TOOL = {
    "type": "function",
    "name": "calculate_and_blink",
    "description": "将用户明确说出的两数算式交给本地计算，并按结果闪灯。",
    "parameters": {
        "type": "object",
        "properties": {
            "a": {"type": "integer", "minimum": -10000, "maximum": 10000},
            "b": {"type": "integer", "minimum": -10000, "maximum": 10000},
            "operation": {"type": "string", "enum": ["add", "subtract", "multiply", "divide"]},
        },
        "required": ["a", "b", "operation"],
        "additionalProperties": False,
    },
}


def calculate(arguments):
    data = json.loads(arguments)
    a, b, op = data["a"], data["b"], data["operation"]
    if any(type(x) is not int or abs(x) > 10000 for x in (a, b)):
        raise ValueError("只接受 -10000 到 10000 的整数操作数。")
    if op == "add":
        result = Fraction(a + b)
    elif op == "subtract":
        result = Fraction(a - b)
    elif op == "multiply":
        result = Fraction(a * b)
    elif op == "divide" and b != 0:
        result = Fraction(a, b)
    else:
        raise ValueError("不支持的运算或除数为零。")
    if result < 0 or result.denominator != 1:
        raise ValueError(f"结果 {result} 不是非负整数，不能用闪烁次数表示。")
    return int(result), min(MAX_BLINKS, int(result))


async def handle(led, name, arguments):
    if name != "calculate_and_blink":
        raise ValueError("未知工具。")
    result, count = calculate(arguments)
    print(f"算术结果：{result}；闪烁 {count} 下（上限 {MAX_BLINKS}）。")
    for _ in range(count):
        await pulse(led, 0.125, 0.125)
    print("闪烁完成。")
    return {"result": result, "blinks": count, "completed": True}


async def main():
    await run_agent(
        "语音算术闪灯",
        "你是中文语音算术助手。仅当用户明确提出两个整数的加减乘除时，"
        "调用 calculate_and_blink 一次；准确提取操作数，不自行改写算式。"
        "每道题只调用一次，不重复。未听清、多个算式或非算术问题，用中文简短询问。"
        "不要根据噪声猜测，不要在未收到工具结果前声称已完成。",
        [TOOL],
        handle,
    )


if __name__ == "__main__":
    launch(main)
