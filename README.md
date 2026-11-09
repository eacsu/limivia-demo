# LIMIVIA Demo

GPIO、PWM、麦克风和 OpenAI Realtime 语音控制示例。整理后的代码位于本项目根目录，原始临时文件不参与运行。

```text
config.py               统一配置，自动读取根目录 .env
.env.example            可提交的环境变量模板，不含密钥
.env                    本机配置，已被 Git 忽略
demos/
  demo01.py … demo07.py  七个独立示例
  voice_common.py       语音连接、录音和 LED 执行队列
pyproject.toml          Poetry 依赖与命令入口
poetry.lock             锁定依赖版本
```

## 安装与配置

支持 Python 3.10–3.12。连接安装了匹配固件的 LIMIVIA 板卡，安装依赖：

```powershell
poetry env use python3.10
poetry install
```

Windows 上若没有 `python3.10` 命令，可向 `poetry env use` 传入 Python 3.10 解释器的完整路径。

如果 `.env` 尚不存在，执行 `Copy-Item .env.example .env`，再编辑 `.env`：

```dotenv
OPENAI_API_KEY=
LIMIVIA_PORT=COM4
BUTTON_PIN=10
LED_PIN=6
```

语音 Demo 05–07 需要填写自己的 `OPENAI_API_KEY`；Demo 01–04 无需密钥。密钥只从环境变量读取，`config.py` 不包含密钥默认值。根目录 `.env` 自动注入，已有进程环境变量优先，加载路径不受工作目录影响。不要提交或分享 `.env`。

所有共享参数集中在 `config.py`：串口、按钮/LED 引脚、PWM 频率和分辨率、轮询/防抖时间、声音阈值、摩尔斯单位时长、闪烁次数上限和语音模型。可覆盖的变量见 `.env.example`；固定协议参数与呼吸周期也在 `config.py` 中维护。模型名称沿用原示例，使用前应确认账户支持该模型，必要时修改 `.env`。

## 运行

选择项目的 `.venv` 解释器后，可以直接在编辑器中点击“运行 Python 文件”，也可以在项目根目录执行：

```powershell
python demos/demo01.py
python demos/demo06.py
```

每个 Demo 都可独立运行，无需命令行参数。程序导入 `config.py` 时，通过 `from dotenv import load_dotenv` 和 `load_dotenv(ROOT_DIR / ".env", override=False)` 自动注入环境变量，无需调试模式或编辑器注入。即使从其他工作目录启动，仍加载项目根目录的 `.env`。

如果没有激活虚拟环境，可执行 `.venv\Scripts\python.exe demos\demo01.py`，或 `poetry run python demos/demo01.py`。也支持 `python -m demos.demo01`。

| 编号 | 功能 | 输入与输出 |
| --- | --- | --- |
| 1 | 按钮控制灯 | 按下亮，松开灭 |
| 2 | PWM 调光 | 每按一次增加 10%，100% 后回到 0% |
| 3 | 十档呼吸灯 | 每按一次加快一档，循环切换 |
| 4 | 声控亮度 | 麦克风音量映射为 PWM 占空比 |
| 5 | 语音算术 | 如“二加三”，LED 闪五下，默认最多二十下 |
| 6 | 语音开关 | 明确说“点亮”或“熄灭” |
| 7 | 英语摩尔斯灯 | 英语转写后逐词闪出摩尔斯码 |

默认接线：按钮一端 IO10、另一端 3.3V，输入使用内部下拉；外接 LED 接 IO6，并通过合适的限流电阻接 GND。实际端口和引脚以 `.env` 为准。一次运行一个 Demo，运行前先断开工作台或串口监视器中的设备连接。Ctrl+C 停止并释放资源。

Demo 04–07 使用系统默认麦克风，需要系统录音权限。Demo 04 不保存录音；Demo 05–07 会把麦克风音频发送给 OpenAI 官方 Realtime 接口，并产生账户对应的 API 费用。启动语音会话前会检查密钥，缺失时给出配置提示。

旧文件仍保留在被忽略的 `tmp_workspace/` 中供对照；请使用新入口。旧配置文件已移除明文密钥，但原始压缩包、缓存或历史备份可能仍包含旧值，已暴露的密钥应撤销并更换。
