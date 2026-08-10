# 💓 HR Overlay — Mi Band Heart-Rate Floating HUD

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/GenmetsuWenxuePress/hr-overlay)](https://github.com/GenmetsuWenxuePress/hr-overlay/releases)
[![Platform](https://img.shields.io/badge/Platform-Windows%2011-blue)]()
[![Tests](https://img.shields.io/badge/tests-24%20passed-green)]()

> **English** | [中文](README.md)

A floating desktop HUD that shows your live heart rate from a Xiaomi Mi Band 9 Pro on Windows. Perfect for horror games, fitness games, or any moment you want to watch your pulse climb. Supports click-through, multiple devices, and threshold blinking alerts.

**[⬇ Download HR-Overlay.exe](https://github.com/GenmetsuWenxuePress/hr-overlay/releases)** (portable, no Python required, ~39MB)

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 💗 BLE heart-rate collection | Standard 0x180D/0x2A37, notify subscription (~1 beat/sec); auto-reconnect after 8s of no data |
| 🃏 Always-on-top card | Frameless, top-most, no taskbar entry; big number + ECG waveform + device nickname |
| 🎚 Opacity | **Affects only the card background & border — digits/waveform stay fully opaque**; 0% = invisible background, floating content |
| 🖱 Click-through | Off by default (draggable); double-click the tray icon to toggle; lets clicks reach your game |
| 🛡 Anti-lost | Drag clamped inside the screen (can't drag it off); tray "Reset Position" returns it to primary-screen center |
| ⚡ Heart-rate alert | Threshold 100/120/140/160/180; digits blink at 400ms when exceeded; auto-stops when HR drops or device disconnects |
| 📈 ECG waveform | Fixed 40–200 BPM scale (absolute HR visible), small fluctuations amplified 6x (fine changes visible) |
| 🎨 Themes | Dark / Light; number & nickname color follows zone (green/yellow/red) or fixed color |
| 📱 Multiple devices | One card per band, stacked vertically; tray menu shows live BPM per device |
| 🔧 Pairing wizard | 8s BLE scan, ★ marks Xiaomi devices; no connection validation (protects the band's broadcast state) |

---

## 🚀 Install & Run

### Option 1: Portable exe (recommended)
Download `HR-Overlay.exe` from [Releases](https://github.com/GenmetsuWenxuePress/hr-overlay/releases) and double-click. No Python needed.

### Option 2: Run from source (development)
```bat
pip install -r requirements.txt
python -m hr_overlay.main
```
Or double-click `start.bat` (pythonw, no console window).

### Build the exe
Double-click `build.bat` (installs dependencies + PyInstaller single-file build). Output: `dist/HR-Overlay.exe`.

> ⚠️ build.bat contains only ASCII — Chinese Windows cmd parses with GBK and would mangle UTF-8 comments into broken commands.

### ⚠️ Prerequisite
The band must have **Heart Rate Broadcast** enabled: band settings → More → Heart Rate Broadcast. Without it the app cannot connect — it's a hardware switch, not a bug.

---

## 🖱 Tray Reference

| Action | Effect |
|--------|--------|
| Left-click tray icon | Open menu |
| Double-click tray icon | Toggle click-through |
| Show/Hide | Toggle card visibility |
| Click-through | Checked = mouse passes through to the game |
| Opacity | 0% / 50% / 75% / 93% / 100% |
| Theme | Dark / Light |
| Number color | Auto (zone) / Green / Yellow / Red / White |
| Heart-rate alert | Off / 100 / 120 / 140 / 160 / 180 |
| Add device… | Open BLE pairing wizard |
| Manage devices | Live BPM per device; rename / delete; "Delete all devices (N)" |
| Reconnect | Force reconnect current device |
| Reset position | Back to primary-screen center |
| Quit | Save position and exit |

**Dragging**: with click-through off, drag the card by holding anywhere on it. It clamps at screen edges so you can never lose it.

---

## ⚙️ Configuration

Config file: `C:\Users\<username>\.hr-overlay\config.json` (auto-created).

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

| Field | Meaning |
|-------|---------|
| `opacity` | Card background opacity 0~1 (content unaffected) |
| `zone_low` / `zone_high` | Heart-rate zone thresholds (green/yellow/red) |
| `bpm_color` | Empty = auto by zone; otherwise fixed color (e.g. `"#facc15"`) |
| `alert_bpm` | 0 = off; 100/120/140/160/180 presets |
| `devices` | Device list (address + nickname) |

---

## 🧪 Tests

```bash
cd hr-overlay
QT_QPA_PLATFORM=offscreen /path/to/venv/bin/python -m pytest tests/ -q
```

Covers: config compatibility/migration, heart_model signals & zones, multi-card layout, pixel-level opacity verification (0% background alpha=1 clamp), blinking logic, drag clamping, reset centering. **24 tests, all green.**

---

## 📁 Project Layout

```
hr-overlay/
├── run.py                  # PyInstaller root entry
├── build.bat               # One-click build (ASCII only)
├── start.bat               # pythonw launch without console
├── requirements.txt
├── hr_overlay/
│   ├── main.py             # Assembly: config → DeviceManager → OverlayWindow → TrayIcon
│   ├── config.py           # OverlayConfig + atomic JSON read/write + legacy migration
│   ├── ble_reader.py       # QThread + asyncio BLE reader (watchdog + backoff)
│   ├── heart_model.py      # BPM/history/zone/status data model
│   ├── device_manager.py   # Multi-device management (retirement-zone safe cleanup)
│   ├── pairing_dialog.py   # BLE scan pairing wizard
│   ├── overlay_window.py   # Multi-card overlay window (QPainter)
│   └── tray.py             # System tray + full menu
└── tests/                  # 24 pytest cases
```

---

## 📜 License

[GPL-3.0](LICENSE) © 2026 GenmetsuWenxuePress

---

## 🔑 Known Pitfalls (verified, do not change)

- A fully transparent window is judged "no clickable content" by Windows → background alpha clamped to min 1 (`max(1, int(opacity*255))`)
- Stroke alpha must scale with opacity (`int(45*opacity)`), otherwise a ghost outline remains at 0%
- NEVER read the MSG pointer via nativeEvent/ctypes to force hit-testing — it crashes PyQt6 with an access violation
- Sleep 1s after connecting before start_notify (GATT session init)
- Tray icon needs 16px + 32px dual sizes; a single 32px renders too small
