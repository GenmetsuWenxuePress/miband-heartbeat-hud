import asyncio
import threading
import time
from typing import Any, Union
from PyQt6.QtCore import QThread, pyqtSignal

try:
    from bleak import BleakClient, BleakError
    HAS_BLEAK = True
except ImportError:
    HAS_BLEAK = False
    BleakClient = None  # type: ignore
    BleakError = Exception  # type: ignore


class BleReader(QThread):
    bpm_ready = pyqtSignal(int)
    connection_changed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)

    def __init__(self, address: str, parent: Union[QThread, None] = None) -> None:
        super().__init__(parent)
        self.address: str = address
        self._stop_event: threading.Event = threading.Event()

    def stop(self) -> None:
        """Thread-safe request to stop the reader loop."""
        self._stop_event.set()

    def run(self) -> None:
        if not HAS_BLEAK:
            self.error_occurred.emit("bleak 未安装")
            self.connection_changed.emit(False)
            return

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_run())
        finally:
            loop.close()

    async def _async_run(self) -> None:
        HR_CHAR_UUID = "00002a37-0000-1000-8000-00805f9b34fb"
        consecutive_no_data_count = 0
        had_success = False
        current_backoff = 5.0

        async def _sleep_interruptible(seconds: float) -> bool:
            end_time = time.monotonic() + seconds
            while time.monotonic() < end_time:
                if self._stop_event.is_set():
                    return True
                await asyncio.sleep(min(0.2, max(0.05, end_time - time.monotonic())))
            return self._stop_event.is_set()

        while not self._stop_event.is_set():
            client: Union[BleakClient, None] = None
            connected_successfully = False
            received_data_in_session = False
            last_packet_time = 0.0

            def notification_handler(sender: Any, data: bytearray) -> None:
                nonlocal last_packet_time, received_data_in_session, had_success
                if not data or len(data) < 2:
                    return
                flags = data[0]
                if flags & 0x01:
                    if len(data) >= 3:
                        bpm = int.from_bytes(data[1:3], byteorder="little", signed=False)
                        last_packet_time = time.monotonic()
                        received_data_in_session = True
                        had_success = True
                        self.bpm_ready.emit(bpm)
                else:
                    bpm = int(data[1])
                    last_packet_time = time.monotonic()
                    received_data_in_session = True
                    had_success = True
                    self.bpm_ready.emit(bpm)

            try:
                client = BleakClient(self.address, timeout=10.0)
                await client.connect()

                if self._stop_event.is_set():
                    break

                connected_successfully = True
                self.connection_changed.emit(True)

                # K7: Sleep 1s before start_notify to allow band GATT session to initialize
                if await _sleep_interruptible(1.0):
                    break

                last_packet_time = time.monotonic()
                await client.start_notify(HR_CHAR_UUID, notification_handler)

                # Watchdog loop: 8s no data timeout
                while not self._stop_event.is_set():
                    await asyncio.sleep(0.5)
                    now = time.monotonic()
                    if now - last_packet_time > 8.0:
                        # Watchdog triggered: 8s no data -> break to reconnect
                        break

                try:
                    await client.stop_notify(HR_CHAR_UUID)
                except Exception:
                    pass

            except Exception as e:
                err_msg = str(e) or "连接异常"
                self.error_occurred.emit(f"BLE错误: {err_msg}")
            finally:
                if client is not None:
                    try:
                        if client.is_connected:
                            await client.disconnect()
                    except Exception:
                        pass
                if connected_successfully:
                    self.connection_changed.emit(False)

            if self._stop_event.is_set():
                break

            # Calculate reconnect backoff (K8)
            if received_data_in_session:
                consecutive_no_data_count = 0
                current_backoff = 2.0
            else:
                consecutive_no_data_count += 1
                if consecutive_no_data_count >= 3:
                    current_backoff = 30.0
                else:
                    if had_success:
                        current_backoff = min(30.0, current_backoff * 2.0)
                    else:
                        current_backoff = min(
                            30.0, max(5.0, current_backoff * 2.0)
                        )

            if await _sleep_interruptible(current_backoff):
                break
