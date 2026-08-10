import os
import json
import pytest
from hr_overlay.config import OverlayConfig, DeviceEntry, load_config, save_config


def test_default_config_nonexistent_path(tmp_path):
    config_file = tmp_path / "nonexistent_config.json"
    cfg = load_config(config_file)
    assert isinstance(cfg, OverlayConfig)
    assert cfg.opacity == 0.93
    assert cfg.theme == "dark"
    assert cfg.devices == []
    assert cfg.alert_bpm == 0
    assert cfg.click_through is False


def test_corrupt_json(tmp_path):
    config_file = tmp_path / "corrupt.json"
    config_file.write_text("{invalid_json: true, ", encoding="utf-8")
    cfg = load_config(config_file)
    assert isinstance(cfg, OverlayConfig)
    assert cfg.opacity == 0.93
    assert cfg.theme == "dark"
    assert cfg.devices == []


def test_missing_fields_silent_defaults(tmp_path):
    config_file = tmp_path / "partial.json"
    config_file.write_text(json.dumps({"opacity": 0.5}), encoding="utf-8")
    cfg = load_config(config_file)
    assert cfg.opacity == 0.5
    assert cfg.theme == "dark"
    assert cfg.devices == []
    assert cfg.alert_bpm == 0
    assert cfg.click_through is False


def test_legacy_device_address_migration(tmp_path):
    config_file = tmp_path / "legacy.json"
    legacy_addr = "AA:BB:CC:DD:EE:01"
    config_file.write_text(json.dumps({"device_address": legacy_addr}), encoding="utf-8")
    cfg = load_config(config_file)
    assert any(d.address == legacy_addr for d in cfg.devices)
    assert cfg.device_address == legacy_addr


def test_save_load_roundtrip(tmp_path):
    config_file = tmp_path / "roundtrip.json"
    original_cfg = OverlayConfig(
        opacity=0.75,
        theme="light",
        alert_bpm=120,
        click_through=True,
        devices=[DeviceEntry(address="AA:BB:CC:DD:EE:FF", name="MyBand")],
    )
    save_config(config_file, original_cfg)
    loaded_cfg = load_config(config_file)

    assert loaded_cfg.opacity == 0.75
    assert loaded_cfg.theme == "light"
    assert loaded_cfg.alert_bpm == 120
    assert loaded_cfg.click_through is True
    assert len(loaded_cfg.devices) == 1
    assert loaded_cfg.devices[0].address == "AA:BB:CC:DD:EE:FF"
    assert loaded_cfg.devices[0].name == "MyBand"


def test_opacity_clamping(tmp_path):
    file_over = tmp_path / "over.json"
    file_over.write_text(json.dumps({"opacity": 5}), encoding="utf-8")
    cfg_over = load_config(file_over)
    assert cfg_over.opacity == 1.0

    file_under = tmp_path / "under.json"
    file_under.write_text(json.dumps({"opacity": -1}), encoding="utf-8")
    cfg_under = load_config(file_under)
    assert cfg_under.opacity == 0.0


def test_atomic_write(tmp_path):
    config_file = tmp_path / "atomic.json"
    cfg = OverlayConfig(opacity=0.88, alert_bpm=140)
    save_config(config_file, cfg)

    assert os.path.exists(config_file)
    loaded = load_config(config_file)
    assert loaded.opacity == 0.88
    assert loaded.alert_bpm == 140
