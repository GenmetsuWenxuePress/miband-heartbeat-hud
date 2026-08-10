import sys
import ctypes
from typing import Union
from PyQt6.QtCore import Qt, QPoint, QPointF, QRectF, QTimer
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QFont,
    QFontMetrics,
    QPen,
    QBrush,
    QPainterPath,
    QMouseEvent,
    QMoveEvent,
)
from PyQt6.QtWidgets import QWidget, QApplication

from hr_overlay.config import OverlayConfig, save_config
from hr_overlay.heart_model import HeartModel

ECG_MIN_BPM = 40.0  # Fixed scale min (bottom edge)
ECG_MAX_BPM = 200.0  # Fixed scale max (top edge)
ECG_ZOOM = 22.0  # Fluctuation amplification: ~6 px per BPM deviation from mean
                 # (mean-anchored deviations are halved for alternating +-1 data,
                 #  so +-1 BPM alternation yields ~+-3 px steps — clearly visible)



class OverlayWindow(QWidget):
    """Floating multi-card overlay window rendered with QPainter."""

    def __init__(
        self,
        models: list[HeartModel],
        cfg: OverlayConfig,
        cfg_path: str = "",
        parent: Union[QWidget, None] = None,
    ) -> None:
        super().__init__(parent)
        self._cfg: OverlayConfig = cfg
        self._cfg_path: str = cfg_path
        self._models: list[HeartModel] = []
        self._connected_models: set[int] = set()

        self._flash_on: list[bool] = []
        self._flash_timer: QTimer = QTimer(self)
        self._flash_timer.setInterval(400)
        self._flash_timer.timeout.connect(self._on_flash_tick)

        self._click_through_enabled: Union[bool, None] = None
        self._drag_pos: Union[QPoint, None] = None

        # Window flags & attributes
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        # Initialize models
        for m in models:
            self.add_model(m)

        # Set size and restore position
        self._recalculate_size()
        self._restore_position()

        # Apply initial click through style
        self.set_click_through(self._cfg.click_through)

    def models(self) -> list[HeartModel]:
        """Return a copy of the heart models list."""
        return list(self._models)

    @property
    def cfg(self) -> OverlayConfig:
        """Public access to the shared config object."""
        return self._cfg

    def add_model(self, model: HeartModel) -> None:
        """Add a heart model and connect its signals idempotently."""
        if model in self._models:
            return

        self._models.append(model)
        self._flash_on.append(True)

        m_id = id(model)
        if m_id not in self._connected_models:
            self._connected_models.add(m_id)
            model.bpm_changed.connect(lambda _: self.refresh_alert())
            model.status_changed.connect(lambda _: self.refresh_alert())
            model.history_changed.connect(lambda _: self.update())
            model.zone_changed.connect(lambda _: self.update())

        self._recalculate_size()
        self.refresh_alert()

    def remove_model(self, model: HeartModel) -> None:
        """Remove a heart model and disconnect its signals."""
        if model not in self._models:
            return

        idx = self._models.index(model)
        self._models.remove(model)
        if idx < len(self._flash_on):
            self._flash_on.pop(idx)

        m_id = id(model)
        if m_id in self._connected_models:
            self._connected_models.discard(m_id)
            try:
                model.bpm_changed.disconnect()
            except Exception:
                pass
            try:
                model.status_changed.disconnect()
            except Exception:
                pass
            try:
                model.history_changed.disconnect()
            except Exception:
                pass
            try:
                model.zone_changed.disconnect()
            except Exception:
                pass

        self._recalculate_size()
        self.refresh_alert()

    def _alert_active(self, model: HeartModel) -> bool:
        """Check if high heart rate alert is active for given model."""
        return bool(
            self._cfg.alert_bpm > 0
            and model.connected()
            and model.current_bpm() >= self._cfg.alert_bpm
        )

    def refresh_alert(self) -> None:
        """Re-evaluate alert state across all cards and update timer."""
        any_alert = False
        for i, model in enumerate(self._models):
            active = self._alert_active(model)
            if active:
                any_alert = True
            else:
                if i < len(self._flash_on):
                    self._flash_on[i] = True

        if any_alert:
            if not self._flash_timer.isActive():
                self._flash_timer.start()
        else:
            if self._flash_timer.isActive():
                self._flash_timer.stop()
            for i in range(len(self._flash_on)):
                self._flash_on[i] = True

        self.update()

    def _on_flash_tick(self) -> None:
        """Timer tick handler: toggle _flash_on for cards triggering alert."""
        any_alert = False
        for i, model in enumerate(self._models):
            if self._alert_active(model):
                any_alert = True
                if i < len(self._flash_on):
                    self._flash_on[i] = not self._flash_on[i]
            else:
                if i < len(self._flash_on):
                    self._flash_on[i] = True

        if not any_alert:
            self._flash_timer.stop()
            for i in range(len(self._flash_on)):
                self._flash_on[i] = True

        self.update()

    def set_click_through(self, enabled: bool) -> None:
        """Set or unset click-through window style using Windows Win32 API."""
        enabled = bool(enabled)
        if self._click_through_enabled == enabled:
            return

        self._click_through_enabled = enabled
        self._cfg.click_through = enabled

        if sys.platform == "win32":
            try:
                hwnd = int(self.winId())
                user32 = ctypes.windll.user32
                gwl_exstyle = -20
                style = user32.GetWindowLongW(hwnd, gwl_exstyle)

                # WS_EX_TRANSPARENT (0x20) | WS_EX_NOACTIVATE (0x08000000)
                mask = 0x00000020 | 0x08000000
                if enabled:
                    style |= mask
                else:
                    style &= ~mask

                user32.SetWindowLongW(hwnd, gwl_exstyle, style)
                # 0x0023 = SWP_NOSIZE (0x0001) | SWP_NOMOVE (0x0002) | SWP_FRAMECHANGED (0x0020)
                user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0023)
            except Exception:
                pass

    def reset_position(self) -> None:
        """Reset window position to primary screen center."""
        screen = QApplication.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        w = self.width()
        h = self.height()
        center_x = geo.left() + (geo.width() - w) // 2
        center_y = geo.top() + (geo.height() - h) // 2
        self.move(center_x, center_y)
        self._cfg.window_x = center_x
        self._cfg.window_y = center_y
        if self._cfg_path:
            self.save_position()

    def save_position(self, cfg_path: Union[str, None] = None) -> None:
        """Save current window coordinates to config file."""
        target_path = cfg_path or self._cfg_path
        if target_path:
            self._cfg.window_x = self.x()
            self._cfg.window_y = self.y()
            save_config(target_path, self._cfg)

    def _recalculate_size(self) -> None:
        """Recalculate window size according to number of cards."""
        n = len(self._models)
        h = max(0, n * 100 - 4) if n > 0 else max(100, self._cfg.height)
        w = max(100, self._cfg.width)
        self.resize(w, h)

    def _restore_position(self) -> None:
        """Restore initial position clamped within available screen geometry."""
        if self._cfg.window_x is not None and self._cfg.window_y is not None:
            target_x = self._cfg.window_x
            target_y = self._cfg.window_y
            screen = (
                QApplication.screenAt(QPoint(target_x, target_y))
                or QApplication.primaryScreen()
            )
            if screen is not None:
                geo = screen.availableGeometry()
                clamped_x = max(geo.left(), min(target_x, geo.right() - self.width()))
                clamped_y = max(geo.top(), min(target_y, geo.bottom() - self.height()))
                self.move(clamped_x, clamped_y)
            else:
                self.move(target_x, target_y)
        else:
            self.reset_position()

    # --- Event Handlers ---

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self._click_through_enabled:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if (
            event.buttons() & Qt.MouseButton.LeftButton
            and self._drag_pos is not None
            and not self._click_through_enabled
        ):
            cursor_pos = event.globalPosition().toPoint()
            target_pos = cursor_pos - self._drag_pos
            screen = QApplication.screenAt(cursor_pos) or QApplication.primaryScreen()
            if screen is not None:
                geo = screen.availableGeometry()
                clamped_x = max(geo.left(), min(target_pos.x(), geo.right() - self.width()))
                clamped_y = max(geo.top(), min(target_pos.y(), geo.bottom() - self.height()))
                self.move(clamped_x, clamped_y)
                self._cfg.window_x = clamped_x
                self._cfg.window_y = clamped_y
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and not self._click_through_enabled:
            self._drag_pos = None
            if self._cfg_path:
                self.save_position()
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def moveEvent(self, event: QMoveEvent) -> None:
        super().moveEvent(event)
        self._cfg.window_x = self.x()
        self._cfg.window_y = self.y()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        card_width = float(self.width())
        is_light = self._cfg.theme == "light"

        # Base background & stroke colors
        bg_base = QColor(246, 247, 250) if is_light else QColor(16, 18, 24)
        stroke_base = QColor(50, 50, 50) if is_light else QColor(200, 200, 200)

        # F6: Background alpha clamped min 1 for clickability at opacity 0
        bg_alpha = max(1, int(self._cfg.opacity * 255))
        # F7: Stroke alpha scales with opacity (0 at opacity 0)
        stroke_alpha = int(45 * self._cfg.opacity)

        bg_color = QColor(bg_base.red(), bg_base.green(), bg_base.blue(), bg_alpha)
        stroke_color = QColor(
            stroke_base.red(), stroke_base.green(), stroke_base.blue(), stroke_alpha
        )

        for i, model in enumerate(self._models):
            y0 = float(i * 100)
            card_rect = QRectF(0.5, y0 + 0.5, card_width - 1.0, 95.0)

            # 1. Background & Stroke
            if stroke_alpha > 0:
                painter.setPen(QPen(stroke_color, 1.0))
            else:
                painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(bg_color))
            painter.drawRoundedRect(card_rect, 14.0, 14.0)

            # Determine Zone Color
            current_bpm = model.current_bpm()
            if current_bpm < self._cfg.zone_low:
                zone_color = QColor("#4ade80")
            elif current_bpm < self._cfg.zone_high:
                zone_color = QColor("#facc15")
            else:
                zone_color = QColor("#f87171")

            if self._cfg.bpm_color.strip():
                bpm_color = QColor(self._cfg.bpm_color.strip())
            else:
                bpm_color = zone_color

            # 2. Nickname (F14)
            if model.display_name:
                nick_font = QFont("Arial", 9)
                painter.setFont(nick_font)
                painter.setPen(bpm_color)
                painter.drawText(
                    QRectF(16.0, y0 + 8.0, card_width * 0.48 - 18.0, 18.0),
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    model.display_name,
                )

            # 3. Large BPM Number (F13 & Flashing)
            flash_show = self._flash_on[i] if i < len(self._flash_on) else True
            if not flash_show:
                bpm_str = ""
            elif current_bpm == 0:
                bpm_str = "--"
            else:
                bpm_str = str(current_bpm)

            if bpm_str:
                max_bpm_w = (card_width * 0.48) - 16.0
                font = QFont("Arial")
                font.setBold(True)
                curr_size = self._cfg.font_size
                font.setPixelSize(curr_size)

                while (
                    QFontMetrics(font).horizontalAdvance(bpm_str) > max_bpm_w
                    and curr_size > 10
                ):
                    curr_size -= 2
                    font.setPixelSize(curr_size)

                painter.setFont(font)
                painter.setPen(bpm_color)
                bpm_rect = QRectF(12.0, y0 + 22.0, max_bpm_w, 66.0)
                painter.drawText(
                    bpm_rect,
                    Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                    bpm_str,
                )

            # 5. ECG Waveform (Catmull-Rom smooth curve)
            history = model.history()
            if len(history) >= 2:
                pts_data = history[-20:]
                ecg_x0 = card_width * 0.48
                ecg_w = card_width - ecg_x0 - 12.0
                ecg_h = 54.0
                ecg_bottom = y0 + 82.0

                rng = ECG_MAX_BPM - ECG_MIN_BPM
                ecg_y0 = y0 + 28.0
                mean_val = sum(pts_data) / len(pts_data)
                # Baseline = fixed-scale absolute position of the window mean;
                # fluctuations around the mean are amplified so small changes are visible.
                slope = ((ecg_h - 10.0) / rng) * ECG_ZOOM
                baseline_y = ecg_bottom - ((mean_val - ECG_MIN_BPM) / rng) * (ecg_h - 10.0) - 5.0
                n_pts = len(pts_data)
                pts: list[QPointF] = []
                for k in range(n_pts):
                    val = float(pts_data[k])
                    px = ecg_x0 + (k / float(n_pts - 1)) * ecg_w
                    py = baseline_y - (val - mean_val) * slope
                    py = max(ecg_y0 + 2.0, min(ecg_bottom - 2.0, py))  # clamp into ECG area
                    pts.append(QPointF(px, py))

                # Catmull-Rom control points
                padded = [pts[0]] + pts + [pts[-1]]
                stroke_path = QPainterPath()
                stroke_path.moveTo(pts[0])
                for k in range(1, n_pts):
                    p0 = padded[k - 1]
                    p1 = padded[k]
                    p2 = padded[k + 1]
                    p3 = padded[k + 2]
                    c1 = QPointF(
                        p1.x() + (p2.x() - p0.x()) / 6.0,
                        p1.y() + (p2.y() - p0.y()) / 6.0,
                    )
                    c2 = QPointF(
                        p2.x() - (p3.x() - p1.x()) / 6.0,
                        p2.y() - (p3.y() - p1.y()) / 6.0,
                    )
                    stroke_path.cubicTo(c1, c2, p2)

                # Draw ECG stroke
                pen_ecg = QPen(zone_color, 2.0)
                pen_ecg.setCapStyle(Qt.PenCapStyle.RoundCap)
                pen_ecg.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
                painter.strokePath(stroke_path, pen_ecg)
