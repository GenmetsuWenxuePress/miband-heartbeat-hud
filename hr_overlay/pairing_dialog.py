import asyncio
from typing import Callable, Union, Optional
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QLabel,
    QWidget,
)

try:
    from bleak import BleakScanner
    HAS_BLEAK = True
except ImportError:
    HAS_BLEAK = False
    BleakScanner = None  # type: ignore


class ScanThread(QThread):
    """BLE device scanner background thread."""

    scan_finished = pyqtSignal(list, int)
    error_occurred = pyqtSignal(str, int)

    def __init__(self, generation: int = 0, parent: Optional[QThread] = None) -> None:
        super().__init__(parent)
        self.generation: int = generation

    def run(self) -> None:
        if not HAS_BLEAK:
            self.error_occurred.emit("bleak 未安装", self.generation)
            return

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                raw_results = loop.run_until_complete(
                    BleakScanner.discover(timeout=8.0, return_adv=True)
                )
            finally:
                loop.close()

            results: list[tuple[str, str, int]] = []
            if isinstance(raw_results, dict):
                for addr, (dev, adv) in raw_results.items():
                    name = (
                        getattr(adv, "local_name", None)
                        or getattr(dev, "name", None)
                        or ""
                    )
                    rssi = getattr(adv, "rssi", None)
                    if rssi is None:
                        rssi = getattr(dev, "rssi", -100)
                    results.append((str(addr), str(name), int(rssi)))
            elif isinstance(raw_results, (list, tuple)):
                for dev in raw_results:
                    addr = getattr(dev, "address", "")
                    name = getattr(dev, "name", "") or ""
                    rssi = getattr(dev, "rssi", -100)
                    results.append((str(addr), str(name), int(rssi)))

            results.sort(key=lambda x: x[2], reverse=True)
            self.scan_finished.emit(results, self.generation)
        except Exception as e:
            self.error_occurred.emit(f"扫描出错: {str(e)}", self.generation)


class PairingDialog(QDialog):
    """BLE heart rate device pairing wizard dialog."""

    def __init__(
        self,
        on_add: Callable[[str, str], bool],
        existing_addresses: Union[set[str], list[str], None] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.on_add: Callable[[str, str], bool] = on_add
        self.existing_addresses: set[str] = {
            str(a).strip().upper() for a in (existing_addresses or [])
        }

        self._scan_thread: Optional[ScanThread] = None
        self._scan_generation: int = 0

        self.setWindowTitle("添加 BLE 心率设备")
        self.resize(440, 380)
        self.setModal(True)

        layout = QVBoxLayout(self)

        self.info_label = QLabel("正在自动扫描附近的 BLE 心率手环与设备...")
        layout.addWidget(self.info_label)

        self.list_widget = QListWidget(self)
        layout.addWidget(self.list_widget)

        self.status_label = QLabel("", self)
        layout.addWidget(self.status_label)

        btn_layout = QHBoxLayout()
        self.btn_scan = QPushButton("开始扫描", self)
        self.btn_add = QPushButton("添加", self)
        self.btn_add.setEnabled(False)
        self.btn_cancel = QPushButton("取消", self)

        btn_layout.addWidget(self.btn_scan)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)

        self.btn_scan.clicked.connect(self.start_scan)
        self.btn_add.clicked.connect(self.add_selected)
        self.btn_cancel.clicked.connect(self.reject)

        self.list_widget.itemSelectionChanged.connect(self._on_selection_changed)
        self.list_widget.itemDoubleClicked.connect(self._on_item_double_clicked)

        self.start_scan()

    def start_scan(self) -> None:
        """Start or restart BLE scanning safely without crashing on repeat clicks."""
        if self._scan_thread is not None:
            try:
                self._scan_thread.scan_finished.disconnect()
            except Exception:
                pass
            try:
                self._scan_thread.error_occurred.disconnect()
            except Exception:
                pass

        self._scan_generation += 1
        self.btn_scan.setEnabled(False)
        self.btn_add.setEnabled(False)
        self.status_label.setText("正在扫描 BLE 设备 (约8s)...")

        self._scan_thread = ScanThread(generation=self._scan_generation, parent=self)
        self._scan_thread.scan_finished.connect(self._on_scan_finished)
        self._scan_thread.error_occurred.connect(self._on_scan_error)
        self._scan_thread.start()

    def _on_scan_finished(
        self, results: list[tuple[str, str, int]], gen: int
    ) -> None:
        if gen != self._scan_generation:
            return

        self.btn_scan.setEnabled(True)
        self.list_widget.clear()

        if not results:
            self.status_label.setText("未找到 BLE 设备，请点击重新扫描")
            return

        for addr, name, rssi in results:
            is_mi = "xiaomi" in name.lower() or "mi" in name.lower()
            prefix = "★ " if is_mi else ""
            display_name = name if name else "(未知设备)"
            text = f"{prefix}{display_name} ({addr}) [{rssi} dBm]"

            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, (addr, name))

            if addr.strip().upper() in self.existing_addresses:
                item.setText(text + " (已添加)")
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                item.setForeground(QBrush(QColor("#888888")))

            self.list_widget.addItem(item)

        self.status_label.setText(f"扫描完成，共找到 {len(results)} 个设备")

    def _on_scan_error(self, err_msg: str, gen: int) -> None:
        if gen != self._scan_generation:
            return

        self.btn_scan.setEnabled(True)
        self.status_label.setText(err_msg)

    def _on_selection_changed(self) -> None:
        items = self.list_widget.selectedItems()
        can_add = bool(items and (items[0].flags() & Qt.ItemFlag.ItemIsEnabled))
        self.btn_add.setEnabled(can_add)

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        if item and (item.flags() & Qt.ItemFlag.ItemIsEnabled):
            self.add_selected()

    def add_selected(self) -> None:
        """Add selected device and close dialog on success."""
        items = self.list_widget.selectedItems()
        if not items:
            return

        item = items[0]
        if not (item.flags() & Qt.ItemFlag.ItemIsEnabled):
            return

        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return

        addr, name = data
        success = self.on_add(addr, name)
        if success:
            self.accept()
        else:
            self.status_label.setText("添加设备失败")

    def reject(self) -> None:
        """Disconnect thread signals when closing."""
        if self._scan_thread is not None:
            try:
                self._scan_thread.scan_finished.disconnect()
            except Exception:
                pass
            try:
                self._scan_thread.error_occurred.disconnect()
            except Exception:
                pass
        super().reject()
