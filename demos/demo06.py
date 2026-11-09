"""语音开关灯：说“点亮”或“熄灭”。

参数见根目录 demos/config.py / .env；运行 python demos/demo06.py。
"""


import json

from voice_common import launch, run_agent

TOOL = {
    "type": "function",
    "name": "set_led",
    "description": "按照用户明确的点亮或熄灭命令设置 LED。",
    "parameters": {
        "type": "object",
        "properties": {"on": {"type": "boolean"}},
        "required": ["on"],
        "additionalProperties": False,
    },
}


async def handle(led, name, arguments):
    if name != "set_led":
        raise ValueError("未知工具。")
    on = json.loads(arguments)["on"]
    if type(on) is not bool:
        raise ValueError("on 必须是布尔值。")
    await led.write(1 if on else 0)
    print("LED 已点亮。" if on else "LED 已熄灭。")
    return {"on": on, "confirmed": True}


async def main():
    await run_agent(
        "语音开关灯",
        "你是中文 LED 语音开关。听到明确的点亮、开灯就调用 set_led(on=true)，"
        "熄灭、关灯就调用 set_led(on=false)。每个命令只调用一次。"
        "注意否定句：不要开灯不是开灯命令。未听清或有歧义时简短询问，不猜测。",
        [TOOL],
        handle,
    )


if __name__ == "__main__":
    launch(main)
