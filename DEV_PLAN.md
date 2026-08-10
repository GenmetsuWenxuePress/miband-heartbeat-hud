# 💓 HR Overlay — 小米手环心率悬浮球（完整开发方案）

> 版本：v1.0（2026-08-10）| 状态：需求冻结，供新会话从头开发


---

## 1. 项目背景与目标

用户（Rodion）佩戴**小米手环 9 Pro**，打 Steam 游戏时希望屏幕上悬浮一个小卡片，**实时显示心率**（看恐怖游戏/健身游戏时的心跳变化）。手环通过**标准 BLE 心率广播**（Heart Rate Service `0x180D`，特征 `0x2A37`，手环 OTA 后官方支持"心率广播"功能，无需手机中转）把心跳发给电脑，电脑端应用订阅通知并显示。

**目标**：Windows 11 桌面小工具——置顶悬浮卡片 + 系统托盘控制 + 配对向导，可打包成免安装 exe。

**核心体验**（用户原话提炼）：
- 悬浮在 Steam 游戏上，不遮挡操作（可点击穿透）
- 0% 透明度时只剩数字+波形"裸悬浮"在游戏画面上
- 心跳飙高时数字闪烁提醒
- 卡片永远不会拖丢

## 2. 功能需求（完整清单）

### 2.1 核心功能
| 编号 | 需求 | 说明 |
|------|------|------|
| F1 | BLE 心率采集 | 标准 0x180D/0x2A37，订阅 notify（约每秒 1 拍），解析 flags+8/16bit BPM |
| F2 | 置顶悬浮卡片 | 无边框、置顶、工具窗口（不进任务栏）、半透明背景 |
| F3 | 实时显示 | 大数字 BPM + 心电图波形（最近 20 点，平滑曲线）|
| F4 | 断线重连 | 自动重连 + 指数退避（5s→30s 封顶）、8s 无数据看门狗主动重连 |

### 2.2 显示与交互（用户打磨过的行为契约，**必须遵守**）
| 编号 | 需求 | 精确语义 |
|------|------|----------|
| F5 | 透明度 | opacity 只影响**卡片背景与描边**，**绝不影响数字/波形/状态点**（0%=背景隐形，内容不透明）|
| F6 | 0% 可点击 | **背景 alpha 钳制最小 1**（`bg_alpha = max(1, int(opacity*255))`）——全透明窗口会被系统判定"无可点击内容"而点击穿透（拖不动、选中下层文字）|
| F7 | 边框随透明度 | 描边 alpha 随 opacity 缩放（`stroke_alpha = int(45*opacity)`）——0% 时边框完全消失 |
| F8 | 默认可拖 | 点击穿透默认**关**（可拖）；穿透开=鼠标穿透（游戏模式）。穿透关闭时点数字区域就能拖（因为数字不透明）|
| F9 | 拖动钳制 | 拖动时窗口**限制在当前鼠标所在屏幕可视区内**（彻底杜绝拖出屏幕外丢失）|
| F10 | 重置位置 | 托盘"重置位置"→ 回主屏居中并保存 |
| F11 | 位置记忆 | 退出/拖动后保存 window_x/window_y 到配置 |
| F12 | 主题 | 深色/浅色（深色卡片 #101218，浅色 #F6F7FA）|
| F13 | 数字颜色 | 自动（随心率区间变色：低绿 #4ade80 / 中黄 #facc15 / 高红 #f87171）或固定色（绿/黄/红/白）|
| F14 | 昵称显示 | 卡片左上显示设备别名（字号 9 小字）|


### 2.3 心率提醒
| 编号 | 需求 | 精确语义 |
|------|------|----------|
| F16 | 阈值闪烁 | 配置 `alert_bpm`（0=关，档位：100/120/140/160/180）|
| F17 | 闪烁方式 | 心率 ≥ 阈值且已连接 → 数字以 **400ms 明暗交替**闪烁；仅数字闪，ECG/状态点不受影响 |
| F18 | 自动恢复 | 心率回落或断连 → 停止闪烁 |

### 2.4 设备管理（多设备）
| 编号 | 需求 | 说明 |
|------|------|------|
| F19 | 配对向导 | 托盘"添加设备"→ 扫描 BLE（8s）→ 列表（★标小米系）→ 添加。**不验证连接**（避免消耗手环广播状态）|
| F20 | 多设备 | 支持多个手环，**每设备一张卡片垂直堆叠**（卡高 96px、间距 4px → 总高 N*100-4）|
| F21 | 管理设备 | 托盘子菜单：每设备「设置别名…/删除设备」+「删除全部设备（N 台）」；菜单标题实时显示每设备 BPM |
| F22 | 首启引导 | 无设备时启动 300ms 后自动弹配对向导 |

### 2.5 托盘控制
| 编号 | 需求 | 说明 |
|------|------|------|
| F23 | 菜单结构 | 显示/隐藏、点击穿透、不透明度(0/50/75/93/100%)、主题、数字颜色、心率提醒、添加设备、管理设备、重新连接、重置位置、退出 |
| F24 | 快捷操作 | 左键单击=弹菜单；**双击=切换点击穿透** |
| F25 | 托盘图标 | 红心图标，**16px+32px 双尺寸**（单 32px 在托盘显示会超小）|
| F26 | 图标语义 | 断开时灰心、连接时红心（可选增强，非必须）|

### 2.6 打包交付
| 编号 | 需求 | 说明 |
|------|------|------|
| F27 | 便携 exe | PyInstaller 单文件 `HR-Overlay.exe`，免 Python，双击即用 |
| F28 | 无控制台 | 最终版 `--noconsole`（pythonw 无黑窗）；开发版 `--console` 便于排障 |

## 3. 技术选型

| 层 | 选型 | 理由 |
|----|------|------|
| BLE | **bleak**（Python）| Windows 最成熟，WinRT 后端，notify 订阅简单 |
| UI | **PyQt6** | 透明置顶窗、QPainter 自绘（圆角卡片+波形）、QSystemTrayIcon、QThread |
| 打包 | PyInstaller | 单文件；必须 `--collect-all winrt` + `--collect-submodules bleak` + winrt hidden-import |
| 环境 | Windows 11 + Python 3.10+ | 用户笔记本/台式机均 Win11 |

## 4. 架构设计

### 4.1 目录树

```
hr-overlay/
├── run.py                      # PyInstaller 入口（根入口避免相对导入破坏）
├── build.bat                   # 一键打包（全英文内容！）
├── start.bat                   # pythonw 无窗口启动
├── requirements.txt            # bleak>=0.22,<1 / PyQt6>=6.7,<7
├── hr_overlay/
│   ├── __init__.py
│   ├── main.py                 # 组装：config→DeviceManager→OverlayWindow→TrayIcon
│   ├── config.py               # OverlayConfig dataclass + JSON 读写（原子写）
│   ├── ble_reader.py           # QThread + asyncio 的 BLE 采集线程
│   ├── heart_model.py          # 数据模型：BPM/history/zone/status + 信号
│   ├── device_manager.py       # 多设备：每设备 BleReader+HeartModel 配对管理
│   ├── pairing_dialog.py       # BLE 扫描配对向导（QThread 扫描）
│   ├── overlay_window.py       # 多卡片悬浮窗口（QPainter 自绘）
│   └── tray.py                 # 系统托盘 + 全菜单
```

### 4.2 模块接口契约（新会话按此实现，勿自创）

```python
# config.py
@dataclass
class DeviceEntry:
    address: str
    name: str = ""

@dataclass
class OverlayConfig:
    window_x: int | None = None
    window_y: int | None = None
    opacity: float = 0.93
    width: int = 200
    height: int = 100
    font_size: int = 52
    zone_low: int = 100          # 心率区间阈值（绿/黄/红）
    zone_high: int = 140
    device_address: str = ""     # 旧字段，加载时迁移到 devices
    auto_connect: bool = False   # 旧字段，兼容保留
    click_through: bool = False  # 默认关=可拖
    theme: str = "dark"          # dark | light
    bpm_color: str = ""          # 空=自动随区间
    alert_bpm: int = 0           # 0=关
    devices: list[DeviceEntry] = field(default_factory=list)

def load_config(path) -> OverlayConfig  # 缺失字段静默用默认值；device_address→devices 迁移
def save_config(path, cfg) -> None      # 原子写（tmp+replace）

# heart_model.py
class HeartModel(QObject):
    bpm_changed = pyqtSignal(int); history_changed = pyqtSignal(list)
    zone_changed = pyqtSignal(str); status_changed = pyqtSignal(str)
    def __init__(self, zone_low=100, zone_high=140, history_size=30, name="", address="", parent=None)
    # display_name / address 公开属性；status()/current_bpm()/history()/zone()/connected()
    # update_bpm(bpm) 更新历史+区间+发信号；set_status(s) 仅变化时发信号

# ble_reader.py
class BleReader(QThread):
    bpm_ready = pyqtSignal(int); connection_changed = pyqtSignal(bool); error_occurred = pyqtSignal(str)
    def __init__(self, address)   # run(): asyncio 循环：连接→sleep 1s→start_notify(0x2A37)→看门狗
    def stop(self)                # 设停止事件（线程安全）

# device_manager.py
class DeviceManager(QObject):
    device_added = pyqtSignal(object); device_removed = pyqtSignal(object); error_occurred = pyqtSignal(str)
    def __init__(self, cfg)
    def add_device(address, name="") -> HeartModel   # 幂等；启动 reader 线程
    def remove_device(address) -> HeartModel | None  # 断开信号→stop→退休区→finished 后 deleteLater
    def models() -> list[HeartModel]
    def stop_all()                                    # 退出时：全部 stop + wait(2000)
    def reconnect(address)

# pairing_dialog.py
class PairingDialog(QDialog):
    def __init__(self, on_add: Callable[[str,str],bool], existing_addresses=None)
    # ScanThread(QThread): asyncio.run(BleakScanner.discover(timeout=8, return_adv=True)) → [(addr,name,rssi)]

# overlay_window.py
class OverlayWindow(QWidget):
    def __init__(self, models: list, cfg)             # models: list[HeartModel]
    def add_model(model) / remove_model(model) / models()
    def _alert_active(model) -> bool                  # alert_bpm>0 and connected and bpm>=阈值
    def refresh_alert()                               # 托盘改阈值后调用
    def set_click_through(enabled)                    # Windows WS_EX 样式切换
    def reset_position() / save_position(cfg_path)

# tray.py
class TrayIcon(QSystemTrayIcon):
    def __init__(self, window, model, cfg_path, reconnector=None, pairing_callback=None,
                 device_remover=None, clear_all_remover=None, rename_callback=None, parent=None)
    # model 可能为 None（无设备）——所有访问必须防御
```

### 4.3 数据模型（用户真实配置示例）

```json
{
  "window_x": 100, "window_y": 200,
  "opacity": 0.93, "width": 200, "height": 100, "font_size": 52,
  "zone_low": 100, "zone_high": 140,
  "device_address": "3C:AF:B7:F6:8E:90",
  "auto_connect": true,
  "click_through": false,
  "theme": "dark", "bpm_color": "#facc15", "alert_bpm": 100,
  "devices": [{"address": "3C:AF:B7:F6:8E:90", "name": "Rodion"}]
}
```
配置路径：`C:\Users\Rodion\.hr-overlay\config.json`（用户手环 MAC：`3C:AF:B7:F6:8E:90`）

## 5. 关键技术点与已踩的坑（**必须遵守，全部实测验证过**）

| # | 坑/要点 | 正确做法 |
|---|---------|----------|
| K1 | 全透明窗口点击穿透 | 背景 alpha 钳制最小 1（F6）。**禁止**用 nativeEvent/ctypes 读 MSG 指针强制命中——实测 PyQt6 上会访问违规崩溃 |
| K2 | QThread 对象生命周期 | **禁止** `finished.connect(deleteLater)` 后继续访问 `isRunning()`（RuntimeError 崩溃）。线程结束后断开信号+放弃引用，GC 自然回收 |
| K3 | 托盘图标 | 必须 16+32 双尺寸 QIcon（心形 path 用 `s=size/32.0` 缩放） |
| K4 | .bat 文件编码 | **全英文内容**——中文 Windows cmd 用 GBK 解析，UTF-8 中文注释会被拆成乱码命令执行 |
| K5 | PyInstaller 相对导入 | 用根目录 `run.py` 入口，直接打包 `hr_overlay/main.py` 会破坏相对导入 |
| K6 | BLE 打包 | `--collect-all winrt` + `--collect-submodules bleak` + hidden-import `winrt.windows.devices.bluetooth.genericattributeprofile` + `winrt.windows.devices.radios` |
| K7 | 手环连接时序 | 连接后 **sleep 1s 再 start_notify**（给手环 GATT 会话初始化时间）；8s 无数据主动断开重连（触发手环重新广播）|
| K8 | 重连退避 | 5s→30s 指数封顶；连续 3 次无数据→30s 长退避；曾成功则 2s 基础冷却 |
| K9 | 配对不验证连接 | 向导只扫描+选择+添加，**不连验证**（避免消耗手环广播状态，广播状态有限）|
| K10 | 闪烁每卡独立 | `_flash_on: list[bool]` 与 models 等长；全局单 QTimer(400ms)，tick 只翻转触发卡 |
| K11 | 拖动钳制 | `QApplication.screenAt(光标位置) or primaryScreen` → availableGeometry 内 clamp（窗口完全不出屏）|
| K12 | 管理设备菜单 | aboutToShow 动态重建（clear 后重建）；QMenu 父子关系自动清理，安全 |
| K13 | 配置兼容 | 缺失字段**静默**用默认值（不打印警告）；`device_address` 旧字段迁移到 `devices` |
| K14 | 多卡片布局 | 卡高 96、间距 4 → 窗口高 `N*100-4`；每卡相对 y0=i*100 绘制 |
| K15 | 无 git | 项目无版本控制，**每次改动前备份文件到 /tmp** |

## 6. 开发任务分解（建议顺序 + 依赖）

```
T1 脚手架（目录/requirements/run.py/config.py 数据模型）        ← 无依赖
T2 heart_model.py（纯逻辑，可独立测试）                          ← T1
T3 ble_reader.py（BLE 线程+看门狗+退避）                         ← T1
T4 overlay_window.py 单卡绘制（数字/ECG/状态点/透明度/主题/颜色）  ← T1+T2
T5 托盘基础（显示隐藏/穿透/透明度/主题/颜色/退出/左键菜单）        ← T1+T4
T6 闪烁提醒（alert_bpm 阈值+每卡独立闪烁）                       ← T2+T4
T7 位置保护（拖动钳制+重置位置+位置记忆）                        ← T4
T8 多设备（device_manager + 多卡片布局 + 管理设备菜单/别名/删除） ← T3+T4+T5
T9 配对向导（pairing_dialog + 首启引导 + 添加设备）              ← T3+T8
T10 打包（build.bat/run.py/start.bat + exe 实测）                ← 全部
```

**关键里程碑**：T5 完成后即可交付用户实测第一版（单卡悬浮球+托盘）；T9 后为完整版；T10 为交付版。

## 7. 测试与验收标准

### 单元/逻辑测试（WSL offscreen 可跑，QT_QPA_PLATFORM=offscreen）
- config：默认值、save/load 往返、旧字段迁移
- heart_model：BPM 更新、history 窗口、zone 判定、信号触发
- 闪烁：低于阈值不闪 / 达到启动 / 回落停止 / 断连停止 / 灭灯帧数字消失
- 布局：N 卡高度 = N*100-4、add/remove 后尺寸正确
- 渲染像素：opacity=0 背景 alpha=1（**采样卡顶 y1-6 x20-180 纯背景区，避开圆角/数字/ECG/状态点**）、数字不透明、边框随 opacity 消失
- 拖动钳制：拖到 (9999,9999) 被钳回屏幕内
- 重置位置：精确居中

### Windows 实测清单（最终验收）
- [ ] `python -m hr_overlay.main` 启动，悬浮球出现，自动连接手环（心率跳动）
- [ ] 配对向导：扫描→添加→再点"开始扫描"**不崩溃**（重复扫描）
- [ ] 托盘：全部子菜单切换生效、勾选同步、双击切穿透
- [ ] opacity=0%：背景隐形、数字可见、**点数字能拖动**
- [ ] 心率提醒：设置 100 → 运动到 100+ → 数字闪烁 → 回落停止
- [ ] 拖动到屏幕边缘 → 拖不出去；托盘"重置位置"回中
- [ ] 多设备：添加第二台 → 两张卡片；管理设备改名/删除
- [ ] 打包：`build.bat` → exe 双击运行、BLE 正常、无黑窗（最终版）

## 8. 交付物清单

1. 源码（hr_overlay 包 + run.py + build.bat + start.bat + requirements.txt）
2. `dist/HR-Overlay.exe`（单文件便携版，~39MB）
3. README（安装/使用/托盘操作表）
4. 测试脚本（/tmp 下，随项目保存到 `tests/` 更佳）

## 9. 给新会话代理的开发纪律（来自上一会话的血泪教训）

1. **先读本文档再动手**；动手前 `search_files` 检查目标目录现有文件（可能是旧版，确认是否复用）
2. **完整读取再覆盖**：`write_file` 前必须 `read_file` 读完整文件
3. **多文件一致性**：改 UI 前确认 main.py 怎么构造它（参数形状）；单设备/多设备 API 混用 = 启动崩溃
4. **测试脚本也是代码**：先确认环境（numpy/PyQt6 装没装）、API 签名（Qt 的 `actualSize(QSize)`、QPixmap 无 `.convert()`）、采样区语义
5. **最小改动**：只做需求清单里的，不加戏（换图标/改文案/重构 = 用户没要求 = 新风险）
6. **每个修复绑定验收**：compileall + 测试 + 冒烟，全绿才算完
7. **用户报错先复现**：跑一遍→根因→修复→验证，不猜不辩
8. 中文沟通；交付时附验证证据（测试数字/截图）
