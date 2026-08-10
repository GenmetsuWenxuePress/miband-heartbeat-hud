from dataclasses import dataclass, field, asdict
import json
import os
import tempfile
from typing import Any, Union


@dataclass
class DeviceEntry:
    address: str
    name: str = ""


@dataclass
class OverlayConfig:
    window_x: Union[int, None] = None
    window_y: Union[int, None] = None
    opacity: float = 0.93
    width: int = 200
    height: int = 100
    font_size: int = 52
    zone_low: int = 100
    zone_high: int = 140
    device_address: str = ""
    auto_connect: bool = False
    click_through: bool = False
    theme: str = "dark"
    bpm_color: str = ""
    alert_bpm: int = 0
    devices: list[DeviceEntry] = field(default_factory=list)


def _safe_int(val: Any, default: int) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _safe_int_or_none(val: Any, default: Union[int, None]) -> Union[int, None]:
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _safe_float(val: Any, default: float) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _safe_bool(val: Any, default: bool) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes")
    return default


def load_config(path: Union[str, os.PathLike]) -> OverlayConfig:
    """Load configuration from JSON file safely without raising exceptions."""
    default_cfg = OverlayConfig()

    if not os.path.exists(path):
        return default_cfg

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return default_cfg

    if not isinstance(data, dict):
        return default_cfg

    opacity_val = _safe_float(data.get("opacity"), default_cfg.opacity)
    opacity_clamped = max(0.0, min(1.0, opacity_val))

    raw_devices = data.get("devices")
    devices: list[DeviceEntry] = []
    if isinstance(raw_devices, list):
        for item in raw_devices:
            if isinstance(item, dict):
                addr = str(item.get("address", "")).strip().upper()
                name = str(item.get("name", "")).strip()
                if addr:
                    devices.append(DeviceEntry(address=addr, name=name))

    dev_addr = str(data.get("device_address", default_cfg.device_address)).strip().upper()
    if dev_addr:
        if not any(d.address == dev_addr for d in devices):
            devices.append(DeviceEntry(address=dev_addr, name=""))

    return OverlayConfig(
        window_x=_safe_int_or_none(data.get("window_x"), default_cfg.window_x),
        window_y=_safe_int_or_none(data.get("window_y"), default_cfg.window_y),
        opacity=opacity_clamped,
        width=_safe_int(data.get("width"), default_cfg.width),
        height=_safe_int(data.get("height"), default_cfg.height),
        font_size=_safe_int(data.get("font_size"), default_cfg.font_size),
        zone_low=_safe_int(data.get("zone_low"), default_cfg.zone_low),
        zone_high=_safe_int(data.get("zone_high"), default_cfg.zone_high),
        device_address=dev_addr,
        auto_connect=_safe_bool(data.get("auto_connect"), default_cfg.auto_connect),
        click_through=_safe_bool(data.get("click_through"), default_cfg.click_through),
        theme=(
            data.get("theme")
            if isinstance(data.get("theme"), str) and data.get("theme")
            else default_cfg.theme
        ),
        bpm_color=(
            data.get("bpm_color")
            if isinstance(data.get("bpm_color"), str)
            else default_cfg.bpm_color
        ),
        alert_bpm=max(0, _safe_int(data.get("alert_bpm"), default_cfg.alert_bpm)),
        devices=devices,
    )


def save_config(path: Union[str, os.PathLike], cfg: OverlayConfig) -> None:
    """Atomic write configuration to JSON file."""
    abs_path = os.path.abspath(path)
    dir_name = os.path.dirname(abs_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)

    cfg_dict = asdict(cfg)
    cfg_dict["devices"] = [
        {"address": d.address, "name": d.name} for d in cfg.devices
    ]

    try:
        fd, temp_path = tempfile.mkstemp(dir=dir_name, prefix="cfg_", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cfg_dict, f, indent=2, ensure_ascii=False)
        os.replace(temp_path, abs_path)
    except Exception:
        if "temp_path" in locals() and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass
