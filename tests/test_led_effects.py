"""用模拟板卡验证无按钮效果及 PWM 资源释放。"""

from contextlib import contextmanager
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "demos"))

import demo01
import demo02
import demo03
import demotk
import led_common


class LedEffectsTests(unittest.TestCase):
    def test_steady_gpio_turns_on_and_off_without_button(self):
        client = MagicMock()
        board = MagicMock()
        led = MagicMock()
        client.devices.list.return_value = [MagicMock(id=demo01.PORT)]
        client.devices.connect.return_value.__enter__.return_value = board
        board.gpio.output.return_value.__enter__.return_value = led
        factory = MagicMock()
        factory.return_value.__enter__.return_value = client
        with patch.object(demo01, "Limivia", factory), patch.object(demo01, "sleep", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                demo01.main()
        self.assertEqual(led.write.call_args_list, [unittest.mock.call(demo01.Level.HIGH), unittest.mock.call(demo01.Level.LOW)])
        board.gpio.input.assert_not_called()

    def test_breath_curve(self):
        self.assertEqual(led_common.breath_duty(0), 0)
        self.assertEqual(led_common.breath_duty(0.5), 100)
        self.assertEqual(led_common.breath_duty(1), 0)

    def test_blink_runs_without_button_and_turns_on_immediately(self):
        led = MagicMock()

        @contextmanager
        def fake_open():
            yield led

        with patch.object(demo02, "open_led", fake_open), patch.object(demo02, "sleep", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                demo02.main()
        led.set_duty.assert_called_once_with(100)

    def test_breath_runs_without_button(self):
        led = MagicMock()

        @contextmanager
        def fake_open():
            yield led

        with patch.object(demo03, "open_led", fake_open), patch.object(demo03, "sleep", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                demo03.main()
        led.set_duty.assert_called_once()

    def test_device_is_turned_off_when_effect_fails(self):
        client = MagicMock()
        board = MagicMock()
        led = MagicMock()
        client.devices.list.return_value = [MagicMock(id=led_common.PORT)]
        client.devices.connect.return_value.__enter__.return_value = board
        board.pwm.open.return_value.__enter__.return_value = led
        factory = MagicMock()
        factory.return_value.__enter__.return_value = client
        with patch.object(led_common, "Limivia", factory):
            with self.assertRaisesRegex(RuntimeError, "effect failed"):
                with led_common.open_led():
                    raise RuntimeError("effect failed")
        led.set_duty.assert_called_once_with(0)
        board.pwm.open.return_value.__exit__.assert_called_once()

    def test_panel_worker_applies_selected_mode(self):
        for mode, brightness, expected in (("steady", 20, 100), ("brightness", 30, 30)):
            with self.subTest(mode=mode):
                panel = object.__new__(demotk.LedPanel)
                panel.stop = threading.Event()
                panel.lock = threading.Lock()
                panel.settings = (mode, brightness, 3.0)
                panel.messages = MagicMock()
                led = MagicMock()
                led.set_duty.side_effect = lambda _duty: panel.stop.set()

                @contextmanager
                def fake_open():
                    yield led

                with patch.object(demotk, "open_led", fake_open):
                    panel.run_device()
                led.set_duty.assert_called_once_with(expected)


if __name__ == "__main__":
    unittest.main()
