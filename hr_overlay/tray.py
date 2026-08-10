from typing import Callable, Optional
from PyQt6.QtCore import Qt, QObject, QTimer
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QPainterPath, QCursor, QAction
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu

from hr_overlay.config import save_config
from hr_overlay.device_manager import DeviceManager
from hr_overlay.overlay_window import OverlayWindow


def create_heart_icon(connected: bool = True) -> QIcon:
    """Create 16px + 32px dual-size heart QIcon."""
    icon = QIcon()
    for size in (16, 32):
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)

        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        s = size / 32.0
        path = QPainterPath()
        path.moveTo(16 * s, 29 * s)
        path.cubicTo(5 * s, 20 * s, 2 * s, 13 * s, 2 * s, 8.5 * s)
        path.cubicTo(2 * s, 4.5 * s, 5 * s, 2 * s, 9 * s, 2 * s)
        path.cubicTo(12.5 * s, 2 * s, 14.8 * s, 4 * s, 16 * s, 6.5 * s)
        path.cubicTo(17.2 * s, 4 * s, 19.5 * s, 2 * s, 23 * s, 2 * s)
        path.cubicTo(27 * s, 2 * s, 30 * s, 4.5 * s, 30 * s, 8.5 * s)
        path.cubicTo(30 * s, 13 * s, 27 * s, 20 * s, 16 * s, 29 * s)

        color = QColor("#ef4444") if connected else QColor("#94a3b8")
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(color))
        painter.drawPath(path)
        painter.end()

        icon.addPixmap(pm)
    return icon


class TrayIcon(QSystemTrayIcon):
    """System tray icon and full context menu controller for multi-device HR Overlay."""

    def __init__(
        self,
        window: OverlayWindow,
        manager: Optional[DeviceManager],
        cfg_path: str,
        pairing_callback: Optional[Callable[[], None]] = None,
        reconnector: Optional[Callable[[], None]] = None,
        device_remover: Optional[Callable[[str], None]] = None,
        clear_all_remover: Optional[Callable[[], None]] = None,
        rename_callback: Optional[Callable[[str], None]] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self._window: OverlayWindow = window
        self._manager: Optional[DeviceManager] = manager
        self._cfg_path: str = cfg_path

        self._pairing_callback: Optional[Callable[[], None]] = pairing_callback
        self._reconnector: Optional[Callable[[], None]] = reconnector
        self._device_remover: Optional[Callable[[str], None]] = device_remover
        self._clear_all_remover: Optional[Callable[[], None]] = clear_all_remover
        self._rename_callback: Optional[Callable[[str], None]] = rename_callback

        self.update_icon()

        # Build Context Menu
        self._menu = QMenu()
        self.setContextMenu(self._menu)

        # 1. Visible
        self.action_toggle_visible = QAction("显示/隐藏", self)
        self.action_toggle_visible.setCheckable(True)
        self.action_toggle_visible.triggered.connect(self._on_toggle_visible)
        self._menu.addAction(self.action_toggle_visible)

        # 2. Click Through
        self.action_click_through = QAction("点击穿透", self)
        self.action_click_through.setCheckable(True)
        self.action_click_through.triggered.connect(self._on_toggle_click_through)
        self._menu.addAction(self.action_click_through)

        # 3. Opacity Submenu
        self.menu_opacity = self._menu.addMenu("不透明度")
        self._opacity_actions: dict[float, QAction] = {}
        for label, val in [
            ("0%", 0.0),
            ("50%", 0.5),
            ("75%", 0.75),
            ("93%", 0.93),
            ("100%", 1.0),
        ]:
            act = self.menu_opacity.addAction(label)
            act.setCheckable(True)
            act.triggered.connect(lambda _, v=val: self._on_set_opacity(v))
            self._opacity_actions[val] = act

        # 4. Theme Submenu
        self.menu_theme = self._menu.addMenu("主题")
        self._theme_actions: dict[str, QAction] = {}
        for label, t_key in [("深色", "dark"), ("浅色", "light")]:
            act = self.menu_theme.addAction(label)
            act.setCheckable(True)
            act.triggered.connect(lambda _, tk=t_key: self._on_set_theme(tk))
            self._theme_actions[t_key] = act

        # 5. Color Submenu
        self.menu_color = self._menu.addMenu("数字颜色")
        self._color_actions: dict[str, QAction] = {}
        for label, c_val in [
            ("自动", ""),
            ("绿", "#4ade80"),
            ("黄", "#facc15"),
            ("红", "#f87171"),
            ("白", "#ffffff"),
        ]:
            act = self.menu_color.addAction(label)
            act.setCheckable(True)
            act.triggered.connect(lambda _, cv=c_val: self._on_set_color(cv))
            self._color_actions[c_val] = act

        # 6. Heart Rate Alert Submenu
        self.menu_alert = self._menu.addMenu("心率提醒")
        self._alert_actions: dict[int, QAction] = {}
        for label, a_val in [
            ("关闭", 0),
            ("100", 100),
            ("120", 120),
            ("140", 140),
            ("160", 160),
            ("180", 180),
        ]:
            act = self.menu_alert.addAction(label)
            act.setCheckable(True)
            act.triggered.connect(lambda _, av=a_val: self._on_set_alert(av))
            self._alert_actions[a_val] = act

        self._menu.addSeparator()

        # 7. Add Device
        self.action_add_device = self._menu.addAction("添加设备…")
        self.action_add_device.triggered.connect(self._on_add_device)

        # 8. Manage Devices Submenu (Rebuilt on aboutToShow)
        self.menu_device_mgmt = self._menu.addMenu("管理设备")

        # 9. Reconnect
        self.action_reconnect = self._menu.addAction("重新连接")
        self.action_reconnect.triggered.connect(self._on_reconnect)

        self._menu.addSeparator()

        # 10. Reset Position
        self.action_reset_pos = self._menu.addAction("重置位置")
        self.action_reset_pos.triggered.connect(self._on_reset_position)

        # 11. Quit
        self.action_quit = self._menu.addAction("退出")
        self.action_quit.triggered.connect(self._on_quit)

        # Signal connections
        self._menu.aboutToShow.connect(self._on_menu_about_to_show)
        self.activated.connect(self._on_activated)

        # Delayed popup: single-click opens the menu, but a double-click
        # (toggle click-through) cancels the pending popup.
        self._popup_timer = QTimer(self)
        self._popup_timer.setSingleShot(True)
        self._popup_timer.setInterval(220)
        self._popup_timer.timeout.connect(self._do_popup)

    def update_icon(self) -> None:
        """Update tray icon color according to device connection states."""
        connected = False
        if self._manager is not None:
            models = self._manager.models()
            connected = any(m.connected() for m in models)
        self.setIcon(create_heart_icon(connected=connected))

    def _on_menu_about_to_show(self) -> None:
        self._update_menu_states()
        self._rebuild_device_menu()

    def _update_menu_states(self) -> None:
        cfg = self._window.cfg
        self.action_toggle_visible.setChecked(self._window.isVisible())
        self.action_click_through.setChecked(cfg.click_through)

        for val, act in self._opacity_actions.items():
            act.setChecked(abs(cfg.opacity - val) < 0.01)

        for t_key, act in self._theme_actions.items():
            act.setChecked(cfg.theme == t_key)

        for c_val, act in self._color_actions.items():
            act.setChecked(cfg.bpm_color == c_val)

        for a_val, act in self._alert_actions.items():
            act.setChecked(cfg.alert_bpm == a_val)

        has_devices = bool(self._manager and self._manager.models())
        self.action_reconnect.setEnabled(has_devices)

    def _rebuild_device_menu(self) -> None:
        self.menu_device_mgmt.clear()
        models = self._manager.models() if self._manager is not None else []

        if not models:
            no_dev = self.menu_device_mgmt.addAction("无设备")
            no_dev.setEnabled(False)
        else:
            for model in models:
                bpm_val = model.current_bpm()
                bpm_str = str(bpm_val) if bpm_val > 0 else "--"
                name_str = model.display_name or model.address
                title = f"{name_str} · {bpm_str}"

                sub = self.menu_device_mgmt.addMenu(title)

                act_rename = sub.addAction("设置别名…")
                act_rename.triggered.connect(
                    lambda _, addr=model.address: self._on_rename(addr)
                )

                act_del = sub.addAction("删除设备")
                act_del.triggered.connect(
                    lambda _, addr=model.address: self._on_remove_device(addr)
                )

        self.menu_device_mgmt.addSeparator()

        act_clear = self.menu_device_mgmt.addAction(
            f"删除全部设备 ({len(models)} 台)"
        )
        act_clear.setEnabled(len(models) > 0)
        act_clear.triggered.connect(self._on_clear_all)

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._popup_timer.start()
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._popup_timer.stop()
            new_val = not self._window.cfg.click_through
            self._window.set_click_through(new_val)
            save_config(self._cfg_path, self._window.cfg)
            self._update_menu_states()

    def _do_popup(self) -> None:
        self._menu.popup(QCursor.pos())

    def _on_toggle_visible(self) -> None:
        self._window.setVisible(not self._window.isVisible())
        self._update_menu_states()

    def _on_toggle_click_through(self) -> None:
        new_val = not self._window.cfg.click_through
        self._window.set_click_through(new_val)
        save_config(self._cfg_path, self._window.cfg)
        self._update_menu_states()

    def _on_set_opacity(self, val: float) -> None:
        self._window.cfg.opacity = val
        save_config(self._cfg_path, self._window.cfg)
        self._window.update()
        self._update_menu_states()

    def _on_set_theme(self, theme_key: str) -> None:
        self._window.cfg.theme = theme_key
        save_config(self._cfg_path, self._window.cfg)
        self._window.update()
        self._update_menu_states()

    def _on_set_color(self, color_val: str) -> None:
        self._window.cfg.bpm_color = color_val
        save_config(self._cfg_path, self._window.cfg)
        self._window.update()
        self._update_menu_states()

    def _on_set_alert(self, alert_val: int) -> None:
        self._window.cfg.alert_bpm = alert_val
        save_config(self._cfg_path, self._window.cfg)
        self._window.refresh_alert()
        self._update_menu_states()

    def _on_add_device(self) -> None:
        if self._pairing_callback is not None:
            self._pairing_callback()

    def _on_reconnect(self) -> None:
        if self._reconnector is not None:
            self._reconnector()

    def _on_reset_position(self) -> None:
        self._window.reset_position()

    def _on_quit(self) -> None:
        self._window.save_position(self._cfg_path)
        from PyQt6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            app.quit()

    def _on_rename(self, address: str) -> None:
        if self._rename_callback is not None:
            self._rename_callback(address)

    def _on_remove_device(self, address: str) -> None:
        if self._device_remover is not None:
            self._device_remover(address)

    def _on_clear_all(self) -> None:
        if self._clear_all_remover is not None:
            self._clear_all_remover()
