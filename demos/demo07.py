"""英文语音增量转写为摩尔斯电码，完成事件补发尾词。

参数见根目录 demos/config.py / .env；运行 python demos/demo07.py。
"""


import re

from voice_common import launch, pulse, run_agent

from config import MORSE_UNIT

UNIT = MORSE_UNIT
MORSE = dict(
    zip(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,?!'-/",
        [
            ".-",
            "-...",
            "-.-.",
            "-..",
            ".",
            "..-.",
            "--.",
            "....",
            "..",
            ".---",
            "-.-",
            ".-..",
            "--",
            "-.",
            "---",
            ".--.",
            "--.-",
            ".-.",
            "...",
            "-",
            "..-",
            "...-",
            ".--",
            "-..-",
            "-.--",
            "--..",
            "-----",
            ".----",
            "..---",
            "...--",
            "....-",
            ".....",
            "-....",
            "--...",
            "---..",
            "----.",
            ".-.-.-",
            "--..--",
            "..--..",
            "-.-.--",
            ".----.",
            "-....-",
            "-..-.",
        ],
        strict=True,
    )
)


class Words:
    """按语音条目保留增量尾词，完成事件只补发尾词，不重放前文。"""

    def __init__(self):
        self.buffers = {}
        self.completed = set()

    def __call__(self, event):
        kind = event["type"].rsplit(".", 1)[-1]
        if kind not in ("delta", "completed"):
            return []
        item_id = event["item_id"]
        if item_id in self.completed:
            return []
        state = self.buffers.setdefault(item_id, {"tail": "", "emitted": ""})
        if kind == "delta":
            state["tail"] += event.get("delta", "")
        else:
            # 最终文本可补全或修正尚未发送的尾词，已经闪出的前文不重放。
            final = event.get("transcript", "")
            if final.startswith(state["emitted"]):
                state["tail"] = final[len(state["emitted"]) :]
            else:
                print("最终转写修正了已发送的前文，已发出的摩尔斯码不重放。")
            state["tail"] += " "
            self.completed.add(item_id)
        words = []
        while match := re.match(r"^\s*(\S+)\s+", state["tail"]):
            words.append(match[1])
            state["emitted"] += state["tail"][: match.end()]
            state["tail"] = state["tail"][match.end() :]
        if kind == "completed":
            del self.buffers[item_id]
        return words


def encode(word):
    word = word.upper().replace("’", "'").replace("—", "-")
    return [(char, MORSE[char]) for char in word if char in MORSE]


async def handle(led, name, word):
    letters = encode(word)
    if not letters:
        print(f"跳过不支持的文字：{word}")
        return {}
    print(f"{word} → {' '.join(code for _, code in letters)}")
    for index, (_, code) in enumerate(letters):
        for symbol_index, symbol in enumerate(code):
            if symbol_index < len(code) - 1:
                gap = 1
            else:
                gap = 7 if index == len(letters) - 1 else 3
            await pulse(led, UNIT * (1 if symbol == "." else 3), UNIT * gap)
    return {"sent": word}


async def main():
    await run_agent(
        "英语摩尔斯灯",
        "Transcribe English faithfully; do not translate.",
        [],
        handle,
        transcript_handler=Words(),
    )


if __name__ == "__main__":
    launch(main)
