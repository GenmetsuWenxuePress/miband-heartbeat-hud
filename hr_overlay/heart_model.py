from collections import deque
from typing import Union
from PyQt6.QtCore import QObject, pyqtSignal


class HeartModel(QObject):
    bpm_changed = pyqtSignal(int)
    history_changed = pyqtSignal(list)
    zone_changed = pyqtSignal(str)
    status_changed = pyqtSignal(str)

    def __init__(
        self,
        zone_low: int = 100,
        zone_high: int = 140,
        history_size: int = 30,
        name: str = "",
        address: str = "",
        parent: Union[QObject, None] = None,
    ) -> None:
        super().__init__(parent)
        self._zone_low = zone_low
        self._zone_high = zone_high
        self.display_name: str = name
        self._address: str = address
        self._status: str = "disconnected"
        self._current_bpm: int = 0
        self._zone: str = "green"
        self._history: deque[int] = deque(maxlen=history_size)

    @property
    def address(self) -> str:
        return self._address

    def status(self) -> str:
        return self._status

    def current_bpm(self) -> int:
        return self._current_bpm

    def history(self) -> list[int]:
        return list(self._history)

    def zone(self) -> str:
        return self._zone

    def connected(self) -> bool:
        return self._status == "connected"

    def set_status(self, s: str) -> None:
        if s != self._status:
            self._status = s
            self.status_changed.emit(s)

    def update_bpm(self, bpm: int) -> None:
        self._current_bpm = bpm
        self._history.append(bpm)

        if bpm < self._zone_low:
            new_zone = "green"
        elif bpm < self._zone_high:
            new_zone = "yellow"
        else:
            new_zone = "red"

        zone_did_change = new_zone != self._zone
        self._zone = new_zone

        self.bpm_changed.emit(bpm)
        self.history_changed.emit(list(self._history))

        if zone_did_change:
            self.zone_changed.emit(new_zone)
