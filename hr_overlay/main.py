import os
import sys
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QInputDialog, QSystemTrayIcon

from hr_overlay.config import load_config, save_config
from hr_overlay.device_manager import DeviceManager
from hr_overlay.overlay_window import OverlayWindow
from hr_overlay.pairing_dialog import PairingDialog
from hr_overlay.tray import TrayIcon


def main() -> None:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    user_dir = os.environ.get("USERPROFILE") or os.path.expanduser("~")
    config_dir = os.path.join(user_dir, ".hr-overlay")
    config_path = os.path.join(config_dir, "config.json")
    os.makedirs(config_dir, exist_ok=True)

    cfg = load_config(config_path)
    manager = DeviceManager(cfg)

    for dev in cfg.devices:
        if dev.address.strip():
            manager.add_device(dev.address.strip(), dev.name)

    window = OverlayWindow(manager.models(), cfg, cfg_path=config_path)
    window.show()

    def pairing_callback() -> None:
        existing = {m.address for m in manager.models()}

        def on_add(address: str, name: str) -> bool:
            clean_addr = address.strip().upper()
            if not clean_addr:
                return False
            manager.add_device(clean_addr, name.strip())
            save_config(config_path, cfg)
            return True

        dlg = PairingDialog(on_add=on_add, existing_addresses=existing, parent=window)
        dlg.exec()

    def reconnector() -> None:
        models = manager.models()
        if models:
            manager.reconnect(models[0].address)

    def device_remover(address: str) -> None:
        model = manager.remove_device(address)
        if model:
            window.remove_model(model)
            save_config(config_path, cfg)

    def clear_all_remover() -> None:
        for model in list(manager.models()):
            manager.remove_device(model.address)
            window.remove_model(model)
        save_config(config_path, cfg)

    def rename_callback(address: str) -> None:
        models = [m for m in manager.models() if m.address == address]
        if not models:
            return
        m = models[0]
        new_name, ok = QInputDialog.getText(
            window,
            "设置别名",
            f"请输入设备 ({address}) 的别名:",
            text=m.display_name,
        )
        if ok and new_name.strip() != m.display_name:
            m.display_name = new_name.strip()
            for dev in cfg.devices:
                if dev.address == address:
                    dev.name = m.display_name
                    break
            save_config(config_path, cfg)
            window.update()

    tray = TrayIcon(
        window=window,
        manager=manager,
        cfg_path=config_path,
        pairing_callback=pairing_callback,
        reconnector=reconnector,
        device_remover=device_remover,
        clear_all_remover=clear_all_remover,
        rename_callback=rename_callback,
    )
    tray.show()

    manager.device_added.connect(
        lambda model: (
            window.add_model(model),
            tray.update_icon(),
            model.status_changed.connect(lambda _: tray.update_icon()),
        )
    )
    manager.device_removed.connect(
        lambda model: (
            window.remove_model(model),
            tray.update_icon(),
        )
    )
    manager.error_occurred.connect(
        lambda msg: tray.showMessage(
            "HR Overlay", msg, QSystemTrayIcon.MessageIcon.Warning, 3000
        )
    )

    for m in manager.models():
        m.status_changed.connect(lambda _: tray.update_icon())
    tray.update_icon()

    if not cfg.devices:
        QTimer.singleShot(300, pairing_callback)

    def on_quit() -> None:
        window.save_position(config_path)
        manager.stop_all()

    app.aboutToQuit.connect(on_quit)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
