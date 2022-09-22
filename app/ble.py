import asyncio
import array
from random import sample
import bleak
import pickle
from kivy.logger import Logger
import logging
from kivymd.toast import toast
logging.Logger.manager.root = Logger
from kivymd.app import MDApp

class BleHandler:
    def __init__(self, app, samples_handler) -> None:
        self.samples_handler = samples_handler
        self.openkardio_device = None
        self.openkardio_cmd = 10

    def start_receiving(self, cmd):
        assert cmd > 0
        if(self.run_ble.is_set()):
            self.openkardio_cmd = min(cmd, 65535)
            self.start_exam.set()
        else:
            toast("OpenKardio not connected")

    def stop_receiving(self):
        self.finish_exam.set()

    def connect(self):
        self.run_ble.set()

    async def connection_handler(self):
        self.run_ble = asyncio.Event()
        self.finish_exam = asyncio.Event()
        self.start_exam = asyncio.Event()
        while MDApp.get_running_app().running:
            await self.run_ble.wait()
            try:
                logging.info("Scanning")
                scanned_devices = await bleak.BleakScanner.discover(1)
                if len(scanned_devices) == 0:
                    raise bleak.exc.BleakError("No devices found")
                scanned_devices.sort(key=lambda device: -device.rssi)
                for device in scanned_devices:
                    if device.name == "OKDevice":
                        logging.info(f"Connecting to {device.name}: {device.rssi} dB")
                        toast(f"Connecting to {device.name}: {device.rssi} dB")
                        self.openkardio_device = device
                        break
                    raise bleak.exc.BleakError("No OpenKardio Device found")
            except bleak.exc.BleakError as e:
                logging.warning(f"ERROR while scanning: {e}")
                toast(e)
            try:
                async with bleak.BleakClient(self.openkardio_device) as client:
                    openkardio_sample_rate = await client.read_gatt_char("55498abf-77df-4dc4-89b2-107dab085034")
                    MDApp.get_running_app().root.ids.new_ekg.sample_rate = int.from_bytes(openkardio_sample_rate, 'little')
                    logging.warning("Control Value: {0}".format(openkardio_sample_rate))
                    await self.start_exam.wait()
                    await client.start_notify("cba1d466-344c-4be3-ab3f-189f80dd7518", self.samples_handler)
                    await client.write_gatt_char("55498abf-77df-4dc4-89b2-107dab085034", self.openkardio_cmd.to_bytes(2,'little'))
                    await self.finish_exam.wait()
                    await client.stop_notify("cba1d466-344c-4be3-ab3f-189f80dd7518")
                    logging.info("Exam finished")
                    self.start_exam.clear()
                    self.finish_exam.clear()
            except bleak.exc.BleakError as e:
                logging.warning(f"Error while connecting: {pickle.dumps(e)}")
            self.run_ble.clear()
