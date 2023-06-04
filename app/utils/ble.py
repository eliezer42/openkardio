import asyncio
import bleak
import pickle
from kivy.logger import Logger
import struct
from kivymd.toast import toast
from kivymd.app import MDApp
from enum import Enum

class State(Enum):
    IDLE = 1
    CONNECTING = 2
    CONNECTED = 3
    XMIT = 4

class BleHandler:
    def __init__(self, frame_handler) -> None:
        self.frame_handler = frame_handler
        self.device = None
        self.cmd = 0
        self.current_state = State.IDLE

    def toogle_reception(self):
        if self.run_ble.is_set():
            if self.start_exam.is_set():
                self.finish_exam.set()
            else:
                self.start_exam.set()
        else:
            toast("OpenKardio not connected")

    def connect(self):
        self.run_ble.set()
    
    def parse_device_info(self, value):
        assert len(value) == 16
        self.battery_level = value[0]
        self.samples_per_frame = value[1]
        self.sample_rate = int.from_bytes(value[2:4],'little')
        self.lead_count = value[4]
        self.resolution = value[5]
        self.fw_version = str(value[6]) + '.' + str(value[7])
        self.conversion_factor = struct.unpack('d', value[8:])
        Logger.info(f"FW: {self.fw_version}")
        Logger.info(f"LC: {self.lead_count}")
        Logger.info(f"BR: {self.resolution}")
        Logger.info(f"SR: {self.sample_rate}")
        Logger.info(f"SF: {self.samples_per_frame}")
        Logger.info(f"BL: {self.battery_level}")
        Logger.info(f"CV: {self.conversion_factor}")


    async def connection_handler(self):
        self.run_ble = asyncio.Event()
        self.finish_exam = asyncio.Event()
        self.start_exam = asyncio.Event()
        while MDApp.get_running_app().running:
            await self.run_ble.wait()                               ## WAIT EVENT
            try:
                Logger.info("Scanning")
                scanned_devices = await bleak.BleakScanner.discover(1)
                if len(scanned_devices) == 0:
                    raise bleak.exc.BleakError("No devices found")
                scanned_devices.sort(key=lambda device: -device.rssi)
                for device in scanned_devices:
                    Logger.info(f"DEVICE: {device.name}")
                    if device.name == "OKDevice":
                        Logger.info(f"Connecting to {device.name}: {device.rssi} dB")
                        toast(f"Connecting to {device.name}: {device.rssi} dB")
                        self.device = device
                        break
                    raise bleak.exc.BleakError("No OpenKardio Device found")
            except bleak.exc.BleakError as e:
                Logger.warning(f"While scanning: {e}")
                toast(str(e))
                self.run_ble.clear()
                MDApp.get_running_app().root.ids.ok_device_panel.status = 'Desconectado'
                continue
            try:
                async with bleak.BleakClient(self.device) as client:
                    raw_device_info = await client.read_gatt_char("5e6c5002-05d8-463b-b21d-eed2204c2002")
                    self.parse_device_info(raw_device_info)
                    MDApp.get_running_app().root.ids.new_ekg.sample_rate = self.sample_rate
                    Logger.warning("Control Value: {0}".format(self.sample_rate))
                    await self.start_exam.wait()                    ## WAIT EVENT
                    await client.start_notify("5e6c5001-05d8-463b-b21d-eed2204c2002", self.frame_handler)
                    await asyncio.sleep(0.12)
                    await client.write_gatt_char("5e6c5002-05d8-463b-b21d-eed2204c2002", b'\x00')
                    await self.finish_exam.wait()
                    await client.write_gatt_char("5e6c5002-05d8-463b-b21d-eed2204c2002", b'\xff')
                    await client.stop_notify("5e6c5001-05d8-463b-b21d-eed2204c2002")
                    Logger.info("Exam finished")
                    self.start_exam.clear()
                    self.finish_exam.clear()
            except bleak.exc.BleakError as e:
                Logger.warning(f"Error while connecting: {pickle.dumps(e)}")
            except AssertionError as e:
                Logger.warning(f"Error while parsing device info: {e}")
            self.run_ble.clear()
