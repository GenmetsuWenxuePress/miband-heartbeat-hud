import pytest
import numpy as np
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QImage
from hr_overlay.heart_model import HeartModel


@pytest.fixture(scope="session")
def qapp():
    """Session-level QApplication instance fixture. Reuse if existing."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


def qimage_to_numpy(image: QImage) -> np.ndarray:
    """Helper function to convert a QImage into a numpy uint8 RGBA array.
    Uses QImage.constBits() and handles bytesPerLine alignment.
    """
    image_rgba = image.convertToFormat(QImage.Format.Format_RGBA8888)
    w, h = image_rgba.width(), image_rgba.height()
    bpl = image_rgba.bytesPerLine()
    ptr = image_rgba.constBits()
    ptr.setsize(h * bpl)
    arr = np.frombuffer(ptr, dtype=np.uint8).reshape((h, bpl))
    return arr[:, : w * 4].reshape((h, w, 4))


@pytest.fixture
def make_model():
    """Factory fixture for creating parameterized HeartModel instances."""
    def _factory(name: str = "TestDevice", address: str = "AA:BB:CC:DD:EE:FF", **kwargs) -> HeartModel:
        return HeartModel(name=name, address=address, **kwargs)
    return _factory
