# 💓 HR Overlay — 小米手环心率悬浮卡片

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/GenmetsuWenxuePress/miband-heartbeat-hud)](https://github.com/GenmetsuWenxuePress/miband-heartbeat-hud/releases)
[![Platform](https://img.shields.io/badge/Platform-Windows%2011-blue)]()
[![Tests](https://img.shields.io/badge/tests-24%20passed-green)]()

> [English](README.en.md) | **中文**

实时显示小米手环（需支持心率广播）心率的 Windows 桌面悬浮卡片。打恐怖游戏/健身游戏时的心跳 HUD，支持点击穿透、多设备、阈值闪烁提醒。

**[⬇ 下载 HR-Overlay.exe](https://github.com/GenmetsuWenxuePress/miband-heartbeat-hud/releases)**（免安装便携版，约 39MB）

---

## ✨ 功能一览

| 功能 | 说明 |
|------|------|
| 💗 BLE 心率采集 | 标准 0x180D/0x2A37，订阅 notify，约每秒 1 拍；8s 无数据自动重连 |
| 🃏 置顶悬浮卡片 | 无边框、置顶、不进任务栏；数字 + 心电图波形 + 设备昵称 |
| 🎚 透明度 | **只影响卡片背景与描边，数字/波形永不透明**；0% = 背景隐形，内容悬浮 |
| 🖱 点击穿透 | 默认关闭（可拖动）；双击托盘图标快速切换；穿透时鼠标直达游戏 |
| 🛡 防丢 | 拖动钳制在屏幕内（拖不出去）；托盘"重置位置"一键回主屏居中 |
| ⚡ 心率提醒 | 阈值 100/120/140/160/180，达到后数字 400ms 闪烁，回落/断连自动恢复 |
| 📈 心电图 | 固定刻度 40~200 BPM（绝对心率可见），小波动放大 6 倍（精细变化可见） |
| 🎨 主题 | 深色 / 浅色；数字与别名颜色自动随区间（绿/黄/红）或固定色 |
| 📱 多设备 | 多手环各一张卡片垂直堆叠；托盘菜单实时显示每台 BPM |
| 🔧 配对向导 | 8s 扫描 BLE 设备，★ 标小米系；不验证连接（保护手环广播状态） |

---

## 🚀 安装与运行

### 方式一：便携 exe（推荐）
从 [Releases](https://github.com/GenmetsuWenxuePress/miband-heartbeat-hud/releases) 下载 `HR-Overlay.exe`，双击运行。无需安装 Python。

### 方式二：源码运行（开发）
```bat
pip install -r requirements.txt
python -m hr_overlay.main
```
或双击 `start.bat`（pythonw 无窗口启动）。

### 打包 exe
双击 `build.bat`（自动装依赖 + PyInstaller 单文件打包），产物在 `dist/HR-Overlay.exe`。

> ⚠️ build.bat 内容为全英文——中文 Windows cmd 用 GBK 解析，UTF-8 中文注释会被拆成乱码命令。

### ⚠️ 使用前提
手环必须开启「心率广播」：手环设置 → 心率广播 打开（不开连不上，这是硬件开关不是软件 bug）。

> 🎮 **独占全屏游戏**：悬浮窗在"独占全屏"模式下会被游戏覆盖，请将游戏设为「无边框窗口化」或「窗口化」模式（多数游戏默认无边框，无需操作）。

---

## 🖱 托盘操作表

| 操作 | 效果 |
|------|------|
| 左键单击托盘图标 | 弹出菜单 |
| 双击托盘图标 | 切换点击穿透 |
| 显示/隐藏 | 切换悬浮卡片可见性 |
| 点击穿透 | 勾选后鼠标穿过卡片直达游戏 |
| 不透明度 | 0% / 50% / 75% / 93% / 100% |
| 主题 | 深色 / 浅色 |
| 数字颜色 | 自动（随心率区间）/ 绿 / 黄 / 红 / 白 |
| 心率提醒 | 关闭 / 100 / 120 / 140 / 160 / 180 |
| 添加设备… | 打开 BLE 扫描配对向导 |
| 管理设备 | 每台设备显示实时 BPM；可改别名 / 删除；底部"删除全部设备（N 台）" |
| 重新连接 | 手动触发重连当前设备 |
| 重置位置 | 回主屏居中 |
| 退出 | 保存位置并退出 |

**拖动卡片**：点击穿透关闭时，按住卡片任意位置拖动；拖到屏幕边缘会被自动钳制（不会丢失）。

---

## ⚙️ 配置

配置文件：`C:\Users\<用户名>\.hr-overlay\config.json`（自动创建）。

```json
{
  "window_x": 100, "window_y": 200,
  "opacity": 0.93, "width": 200, "height": 100, "font_size": 52,
  "zone_low": 100, "zone_high": 140,
  "click_through": false,
  "theme": "dark", "bpm_color": "", "alert_bpm": 0,
  "devices": [{"address": "AA:BB:CC:DD:EE:01", "name": "My Band"}]
}
```

| 字段 | 说明 |
|------|------|
| `opacity` | 卡片背景不透明度 0~1（内容不受影响） |
| `zone_low` / `zone_high` | 心率区间阈值（绿/黄/红） |
| `bpm_color` | 空 = 自动随区间；否则固定色（如 `"#facc15"`） |
| `alert_bpm` | 0 = 关；100/120/140/160/180 档位 |
| `devices` | 设备列表（address + 别名） |

---

## 🧪 测试

```bash
cd hr-overlay
QT_QPA_PLATFORM=offscreen /path/to/venv/bin/python -m pytest tests/ -q
```

覆盖：config 兼容/迁移、heart_model 信号与区间、多卡片布局、透明度像素级验证（0% 背景 alpha=1 钳制）、闪烁逻辑、拖动钳制、重置居中。**24 个用例全绿。**

---

## 📁 项目结构

```
hr-overlay/
├── run.py                  # PyInstaller 根入口
├── build.bat               # 一键打包（全英文）
├── start.bat               # pythonw 无窗口启动
├── requirements.txt
├── hr_overlay/
│   ├── main.py             # 组装：config → DeviceManager → OverlayWindow → TrayIcon
│   ├── config.py           # OverlayConfig + JSON 原子读写 + 旧字段迁移
│   ├── ble_reader.py       # QThread + asyncio BLE 采集（看门狗 + 退避）
│   ├── heart_model.py      # BPM/history/zone/status 数据模型
│   ├── device_manager.py   # 多设备管理（退休区安全回收）
│   ├── pairing_dialog.py   # BLE 扫描配对向导
│   ├── overlay_window.py   # 多卡片悬浮窗口（QPainter 自绘）
│   └── tray.py             # 系统托盘 + 全菜单
└── tests/                  # 24 个 pytest 用例
```

---

## 📜 许可证

[GPL-3.0](LICENSE) © 2026 GenmetsuWenxuePress

---

## 🔑 已知坑（实测验证，勿改动）

- 全透明窗口会被 Windows 判定"无可点击内容"→ 背景 alpha 钳制最小 1（`max(1, int(opacity*255))`）
- 描边 alpha 必须随 opacity 缩放（`int(45*opacity)`），否则 0% 时留幽灵边框
- 禁止 nativeEvent/ctypes 读 MSG 指针强制命中——PyQt6 上会访问违规崩溃
- 连接手环后 sleep 1s 再 start_notify（GATT 会话初始化）
- 托盘图标必须 16px+32px 双尺寸，单 32px 显示超小
