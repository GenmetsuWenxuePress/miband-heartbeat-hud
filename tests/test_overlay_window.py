import pytest
import numpy as np
from PyQt6.QtCore import Qt, QPoint, QPointF, QEvent
from PyQt6.QtGui import QMouseEvent
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from hr_overlay.config import OverlayConfig, load_config
from hr_overlay.heart_model import HeartModel
from hr_overlay.overlay_window import OverlayWindow
from tests.conftest import qimage_to_numpy


def test_layout_card_heights(qapp, make_model):
    m1 = make_model(name="M1")
    m2 = make_model(name="M2")
    m3 = make_model(name="M3")
    m4 = make_model(name="M4")

    cfg = OverlayConfig()
    win = OverlayWindow([m1, m2, m3], cfg)
    assert win.height() == 3 * 100 - 4

    win.add_model(m4)
    assert win.height() == 4 * 100 - 4

    win.remove_model(m4)
    assert win.height() == 3 * 100 - 4

    win.remove_model(m3)
    assert win.height() == 2 * 100 - 4


def test_render_pixels_opacity(qapp, make_model):
    model = make_model()

    # opacity = 0
    cfg0 = OverlayConfig(opacity=0.0)
    win0 = OverlayWindow([model], cfg0)
    win0.show()
    qapp.processEvents()
    arr0 = qimage_to_numpy(win0.grab().toImage())
    bg0 = arr0[1:6, 20:180]
    assert np.all(bg0[:, :, 3] == 1)

    # opacity = 1
    cfg1 = OverlayConfig(opacity=1.0)
    win1 = OverlayWindow([model], cfg1)
    win1.show()
    qapp.processEvents()
    arr1 = qimage_to_numpy(win1.grab().toImage())
    bg1 = arr1[1:6, 20:180]
    assert np.all(bg1[:, :, 3] == 255)


def test_render_pixels_digits_opaque(qapp, make_model):
    model = make_model()
    model.set_status("connected")
    model.update_bpm(120)

    cfg = OverlayConfig(opacity=0.0)
    win = OverlayWindow([model], cfg)
    win.show()
    qapp.processEvents()
    arr = qimage_to_numpy(win.grab().toImage())

    # Background alpha <= 1
    bg = arr[1:6, 20:180]
    assert np.all(bg[:, :, 3] <= 1)

    # Digits/status dot/nickname present and opaque (alpha >= 250)
    assert np.any(arr[:, :, 3] >= 250)


def test_render_pixels_border_opacity(qapp, make_model):
    model = make_model()

    # Opacity = 0: stroke_alpha = 0, no border painted (card edges alpha <= 1, F7 disappeared)
    cfg0 = OverlayConfig(opacity=0.0)
    win0 = OverlayWindow([model], cfg0)
    win0.show()
    qapp.processEvents()
    arr0 = qimage_to_numpy(win0.grab().toImage())
    edges0 = np.concatenate([arr0[0, 20:180, 3], arr0[95, 20:180, 3], arr0[20:80, 0, 3], arr0[20:80, 199, 3]])
    assert np.all(edges0 <= 1)

    # Opacity = 1: stroke_alpha = 45, card border contains pixels with alpha >= 40 (stroke 45)
    cfg1 = OverlayConfig(opacity=1.0)
    win1 = OverlayWindow([model], cfg1)
    win1.show()
    qapp.processEvents()
    arr1 = qimage_to_numpy(win1.grab().toImage())
    edges1 = np.concatenate([arr1[0, 20:180, 3], arr1[95, 20:180, 3], arr1[20:80, 0, 3], arr1[20:80, 199, 3]])
    assert np.any(edges1 >= 40)


def test_render_pixels_theme(qapp, make_model):
    model = make_model()

    # Dark theme: RGB approx (16, 18, 24) +/- 5
    cfg_dark = OverlayConfig(opacity=1.0, theme="dark")
    win_dark = OverlayWindow([model], cfg_dark)
    win_dark.show()
    qapp.processEvents()
    arr_dark = qimage_to_numpy(win_dark.grab().toImage())
    bg_dark = arr_dark[1:6, 20:180, :3]
    mean_dark = bg_dark.mean(axis=(0, 1))
    assert abs(mean_dark[0] - 16) <= 5
    assert abs(mean_dark[1] - 18) <= 5
    assert abs(mean_dark[2] - 24) <= 5

    # Light theme: RGB approx (246, 247, 250) +/- 5
    cfg_light = OverlayConfig(opacity=1.0, theme="light")
    win_light = OverlayWindow([model], cfg_light)
    win_light.show()
    qapp.processEvents()
    arr_light = qimage_to_numpy(win_light.grab().toImage())
    bg_light = arr_light[1:6, 20:180, :3]
    mean_light = bg_light.mean(axis=(0, 1))
    assert abs(mean_light[0] - 246) <= 5
    assert abs(mean_light[1] - 247) <= 5
    assert abs(mean_light[2] - 250) <= 5


def test_flashing_behavior(qapp, make_model):
    model = make_model()
    cfg = OverlayConfig(alert_bpm=100, opacity=1.0)
    win = OverlayWindow([model], cfg)
    win.show()
    qapp.processEvents()

    # Case 1: Below threshold or disconnected -> No flashing
    model.set_status("connected")
    model.update_bpm(80)
    qapp.processEvents()
    assert win._flash_on[0] is True
    assert not win._flash_timer.isActive()

    # Case 2: Above threshold & connected -> Flashing active, off frames occur
    model.update_bpm(120)
    qapp.processEvents()
    assert win._flash_timer.isActive()

    # Grab frame on 'on' state (initial state before tick)
    arr_on = qimage_to_numpy(win.grab().toImage())

    # Wait for timer tick (400ms) and process events so paintEvent renders the off frame
    QTest.qWait(450)
    qapp.processEvents()

    assert win._flash_on[0] is False
    arr_off = qimage_to_numpy(win.grab().toImage())

    # Digit area (x in [12, 90], y in [22, 88]) pixel difference between ON and OFF frame is significant
    digit_region_on = arr_on[22:88, 12:90]
    digit_region_off = arr_off[22:88, 12:90]
    diff = np.abs(digit_region_on.astype(int) - digit_region_off.astype(int))
    assert np.max(diff) > 100

    # OFF frame has no alpha >= 250 in digit region (digits hidden)
    assert not np.any(digit_region_off[:, :, 3] >= 250)

    # Case 3: Recovery -> BPM back to 80 stops flashing and resets _flash_on to True
    model.update_bpm(80)
    qapp.processEvents()
    assert win._flash_on[0] is True
    assert not win._flash_timer.isActive()

    # Case 4: Disconnect while above threshold -> Resets _flash_on to True
    model.update_bpm(120)
    qapp.processEvents()
    assert win._flash_timer.isActive()

    model.set_status("disconnected")
    qapp.processEvents()
    assert win._flash_on[0] is True
    assert not win._flash_timer.isActive()


def test_drag_clamping(qapp, make_model):
    model = make_model()
    cfg = OverlayConfig()
    win = OverlayWindow([model], cfg)
    win.show()
    qapp.processEvents()

    screen = QApplication.primaryScreen()
    geo = screen.availableGeometry()

    press_event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(10, 10),
        QPointF(win.x() + 10, win.y() + 10),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(win, press_event)

    move_event = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(99999, 99999),
        QPointF(99999, 99999),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    QApplication.sendEvent(win, move_event)
    qapp.processEvents()

    frame_geo = win.frameGeometry()
    assert frame_geo.left() >= geo.left()
    assert frame_geo.top() >= geo.top()
    assert frame_geo.right() <= geo.right()
    assert frame_geo.bottom() <= geo.bottom()


def test_reset_position(qapp, make_model):
    model = make_model()
    cfg = OverlayConfig()
    win = OverlayWindow([model], cfg)
    win.show()
    qapp.processEvents()

    screen = QApplication.primaryScreen()
    geo = screen.availableGeometry()
    expected_x = (geo.width() - win.width()) // 2
    expected_y = (geo.height() - win.height()) // 2

    win.move(0, 0)
    win.reset_position()

    assert abs(win.x() - expected_x) <= 1
    assert abs(win.y() - expected_y) <= 1


def test_save_position(qapp, make_model, tmp_path):
    model = make_model()
    cfg_file = tmp_path / "win_config.json"
    cfg = OverlayConfig()
    win = OverlayWindow([model], cfg, cfg_path=str(cfg_file))
    win.show()
    qapp.processEvents()

    win.move(150, 250)
    win.save_position(str(cfg_file))

    loaded_cfg = load_config(cfg_file)
    assert loaded_cfg.window_x == 150
    assert loaded_cfg.window_y == 250
