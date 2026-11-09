"""独立进程验证 .env 注入和密钥边界，不连接硬件或 API。"""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ConfigurationTests(unittest.TestCase):
    def run_config(self, dotenv="", overrides=None, code="import config"):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            demo_dir = folder / "demos"
            demo_dir.mkdir()
            shutil.copy2(ROOT / "demos" / "config.py", demo_dir / "config.py")
            (folder / ".env").write_text(dotenv, encoding="utf-8")
            # Prevent local settings from influencing isolated configuration checks.
            env = {key: value for key, value in os.environ.items()
                   if key not in {"OPENAI_API_KEY", "LIMIVIA_PORT", "LED_PIN",
                                  "NOISE_DB", "LOUD_DB"}}
            env.update(overrides or {})
            env["PYTHONPATH"] = str(demo_dir)
            env["PYTHONIOENCODING"] = "utf-8"
            return subprocess.run(
                [sys.executable, "-c", code], cwd=ROOT.parent, env=env,
                capture_output=True, text=True, encoding="utf-8",
            )

    def test_dotenv_loads_from_config_directory(self):
        result = self.run_config(
            "OPENAI_API_KEY=test-placeholder\nLIMIVIA_PORT=COM9\nLED_PIN=8\n",
            code="import config; assert config.PORT == 'COM9'; "
                 "assert config.LED_PIN == 8; "
                 "assert config.require_api_key() == 'test-placeholder'",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_environment_overrides_dotenv(self):
        result = self.run_config(
            "OPENAI_API_KEY=file-placeholder\nLIMIVIA_PORT=COM9\n",
            {"OPENAI_API_KEY": "env-placeholder", "LIMIVIA_PORT": "COM7"},
            "import config; assert config.PORT == 'COM7'; "
            "assert config.require_api_key() == 'env-placeholder'",
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_key_does_not_block_hardware_configuration(self):
        result = self.run_config(code="import config; assert config.PORT")
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.run_config(code="import config; config.require_api_key()")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("OPENAI_API_KEY", result.stderr)

    def test_invalid_values_do_not_echo_secrets(self):
        for name, value in [("LED_PIN", "private-placeholder"),
                            ("LOUD_DB", "-60"), ("LOUD_DB", "nan")]:
            with self.subTest(name=name, value=value):
                result = self.run_config(overrides={name: value})
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("private-placeholder", result.stderr)


if __name__ == "__main__":
    unittest.main()
