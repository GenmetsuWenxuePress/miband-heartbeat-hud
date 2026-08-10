from typing import Union
from PyQt6.QtCore import QObject, pyqtSignal

from hr_overlay.config import OverlayConfig, DeviceEntry
from hr_overlay.heart_model import HeartModel
from hr_overlay.ble_reader import BleReader


class DeviceManager(QObject):
    device_added = pyqtSignal(object)
    device_removed = pyqtSignal(object)
    error_occurred = pyqtSignal(str)

    def __init__(
        self, cfg: OverlayConfig, parent: Union[QObject, None] = None
    ) -> None:
        super().__init__(parent)
        self.cfg: OverlayConfig = cfg
        self._devices: dict[str, tuple[HeartModel, BleReader]] = {}
        self._retired_readers: list[BleReader] = []

    def _cleanup_retired_reader(self, reader: BleReader) -> None:
        if reader in self._retired_readers:
            self._retired_readers.remove(reader)
        reader.deleteLater()

    def add_device(self, address: str, name: str = "") -> HeartModel:
        address = address.strip().upper()
        if address in self._devices:
            model, _ = self._devices[address]
            return model

        model = HeartModel(
            zone_low=self.cfg.zone_low,
            zone_high=self.cfg.zone_high,
            name=name,
            address=address,
            parent=self,
        )

        reader = self._create_reader(model, address)
        self._devices[address] = (model, reader)
        reader.start()

        found_cfg_entry = False
        for dev in self.cfg.devices:
            if dev.address.strip().upper() == address:
                found_cfg_entry = True
                if name:
                    dev.name = name
                break
        if not found_cfg_entry:
            self.cfg.devices.append(DeviceEntry(address=address, name=name))

        self.device_added.emit(model)
        return model

    def _create_reader(self, model: HeartModel, address: str) -> BleReader:
        """Create a BleReader wired to the given model's signals."""
        reader = BleReader(address=address)

        def _on_conn(connected: bool, m: HeartModel = model) -> None:
            m.set_status("connected" if connected else "disconnected")

        def _on_err(err_msg: str, m: HeartModel = model) -> None:
            m.set_status("error")
            self.error_occurred.emit(err_msg)

        reader.bpm_ready.connect(model.update_bpm)
        reader.connection_changed.connect(_on_conn)
        reader.error_occurred.connect(_on_err)
        return reader

    def remove_device(self, address: str) -> Union[HeartModel, None]:
        address = address.strip().upper()
        if address not in self._devices:
            return None

        model, reader = self._devices.pop(address)

        for sig in (reader.bpm_ready, reader.connection_changed, reader.error_occurred):
            try:
                sig.disconnect()
            except Exception:
                pass

        reader.stop()
        self._retired_readers.append(reader)
        reader.finished.connect(lambda r=reader: self._cleanup_retired_reader(r))

        self.cfg.devices = [
            d for d in self.cfg.devices if d.address.strip().upper() != address
        ]

        self.device_removed.emit(model)
        return model

    def models(self) -> list[HeartModel]:
        return [pair[0] for pair in self._devices.values()]

    def stop_all(self) -> None:
        all_readers: list[BleReader] = [pair[1] for pair in self._devices.values()]
        all_readers.extend(self._retired_readers)

        for reader in all_readers:
            reader.stop()

        survivors: list[BleReader] = []
        for reader in all_readers:
            if not reader.wait(2000):
                survivors.append(reader)

        self._devices.clear()
        self._retired_readers = survivors

    def reconnect(self, address: str) -> None:
        address = address.strip().upper()
        if address not in self._devices:
            return

        model, old_reader = self._devices.pop(address)

        for sig in (old_reader.bpm_ready, old_reader.connection_changed, old_reader.error_occurred):
            try:
                sig.disconnect()
            except Exception:
                pass

        old_reader.stop()
        self._retired_readers.append(old_reader)

        def _restart() -> None:
            self._cleanup_retired_reader(old_reader)
            # Do not resurrect a device removed while the reconnect was pending.
            if not any(d.address.strip().upper() == address for d in self.cfg.devices):
                return
            new_reader = self._create_reader(model, address)
            self._devices[address] = (model, new_reader)
            new_reader.start()

        old_reader.finished.connect(_restart)
