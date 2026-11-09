"""Tkinter LED 控制面板：python demos/demotk.py。"""

import queue
import threading
import tkinter as tk
from time import monotonic
from tkinter import ttk

from config import BREATH_PERIOD, LED_PIN, POLL_INTERVAL, PORT
from led_common import breath_duty, open_led


class LedPanel:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.stop = threading.Event()
        self.lock = threading.Lock()
        self.settings = ("steady", 50.0, BREATH_PERIOD)
        self.messages = queue.Queue()
        self.mode = tk.StringVar(value="steady")
        self.brightness = tk.DoubleVar(value=50)
        self.period = tk.DoubleVar(value=max(0.2, min(10.0, BREATH_PERIOD)))
        self.status = tk.StringVar(value=f"正在连接 {PORT} / IO{LED_PIN}…")

        root.title("LED 控制")
        root.resizable(False, False)
        frame = ttk.Frame(root, padding=20)
        frame.grid(sticky="nsew")
        ttk.Label(frame, text="LED 控制", font=("", 16, "bold")).grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 12))
        ttk.Label(frame, textvariable=self.status, wraplength=360).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 12))
        for column, (label, value) in enumerate((("常亮", "steady"), ("亮度调节", "brightness"), ("呼吸灯", "breath"))):
            ttk.Radiobutton(frame, text=label, value=value, variable=self.mode, command=self.update_settings).grid(row=2, column=column, sticky="w", padx=(0, 12))
        ttk.Label(frame, text="亮度（%）").grid(row=3, column=0, sticky="w", pady=(16, 0))
        self.brightness_scale = ttk.Scale(frame, from_=0, to=100, variable=self.brightness, command=self.update_settings)
        self.brightness_scale.grid(row=4, column=0, columnspan=2, sticky="ew")
        self.brightness_label = ttk.Label(frame, width=8)
        self.brightness_label.grid(row=4, column=2, sticky="e")
        ttk.Label(frame, text="呼吸周期（秒，越短越快）").grid(row=5, column=0, columnspan=3, sticky="w", pady=(16, 0))
        self.period_scale = ttk.Scale(frame, from_=0.2, to=10, variable=self.period, command=self.update_settings)
        self.period_scale.grid(row=6, column=0, columnspan=2, sticky="ew")
        self.period_label = ttk.Label(frame, width=8)
        self.period_label.grid(row=6, column=2, sticky="e")
        ttk.Button(frame, text="关闭", command=self.close).grid(row=7, column=2, sticky="e", pady=(20, 0))
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.update_settings()
        self.worker = threading.Thread(target=self.run_device, name="led-device")
        self.worker.start()
        root.after(100, self.poll_messages)

    def update_settings(self, *_args) -> None:
        mode = self.mode.get()
        brightness = round(self.brightness.get(), 1)
        period = max(0.2, self.period.get())
        with self.lock:
            self.settings = (mode, brightness, period)
        self.brightness_label.config(text=f"{brightness:.0f}%")
        self.period_label.config(text=f"{period:.1f} 秒")
        self.brightness_scale.state(["!disabled"] if mode == "brightness" else ["disabled"])
        self.period_scale.state(["!disabled"] if mode == "breath" else ["disabled"])

    def run_device(self) -> None:
        try:
            with open_led() as led:
                self.messages.put(f"已连接 {PORT} / IO{LED_PIN}")
                phase = 0.0
                last_tick = monotonic()
                last_duty = None
                while not self.stop.is_set():
                    now = monotonic()
                    with self.lock:
                        mode, brightness, period = self.settings
                    phase = (phase + (now - last_tick) / period) % 1.0
                    last_tick = now
                    duty = 100 if mode == "steady" else brightness if mode == "brightness" else breath_duty(phase)
                    if duty != last_duty:
                        led.set_duty(duty)
                        last_duty = duty
                    self.stop.wait(POLL_INTERVAL)
        except Exception as exc:
            self.messages.put(f"设备错误：{exc}。请关闭窗口，检查连接后重试。")

    def poll_messages(self) -> None:
        try:
            while True:
                self.status.set(self.messages.get_nowait())
        except queue.Empty:
            pass
        if self.stop.is_set():
            if not self.worker.is_alive():
                self.root.destroy()
                return
        self.root.after(100, self.poll_messages)

    def close(self) -> None:
        self.status.set("正在关闭 LED 并释放设备…")
        self.stop.set()


def main() -> None:
    root = tk.Tk()
    LedPanel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
