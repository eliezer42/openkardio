import asyncio
import bleak
from kivy.logger import Logger
import struct
from kivymd.toast import toast
from kivymd.app import MDApp
from enum import Enum
from kivy.base import EventDispatcher
from kivy.properties import ObjectProperty, StringProperty, NumericProperty

class ConnState(Enum):
    IDLE = 1
    SCANNING = 2
    CONNECTED = 3
    RECEIVING = 4

class BleHandler(EventDispatcher):
    state = ObjectProperty(ConnState.IDLE)
    battery_level = NumericProperty()
    sample_rate = NumericProperty()
    lead_count = NumericProperty()
    resolution = NumericProperty()
    fw_version = StringProperty("")
    conv_factor = NumericProperty(1.0)
    frame_handler = ObjectProperty()
    device = ObjectProperty()
    cmd = ObjectProperty()
    app = ObjectProperty()

    def __init__(self, **kwargs):
        super(BleHandler, self).__init__(**kwargs)
        self.app = MDApp.get_running_app()
        self.cmd = b'\x00'

    def parse_device_info(self, value):
        assert len(value) == 16
        try:
            self.battery_level = value[0]
            self.samples_per_frame = value[1]
            self.sample_rate = int.from_bytes(value[2:4],'little')
            self.lead_count = value[4]
            self.resolution = value[5]
            self.fw_version = str(value[6]) + '.' + str(value[7])
            self.conv_factor = struct.unpack('d', value[8:])[0]
            Logger.info(
                f"OKDevice: FW=v{self.fw_version} LC={self.lead_count} BR={self.resolution} SR={self.sample_rate} SF={self.samples_per_frame} BL={self.battery_level} CV={self.conv_factor}"
            )

        except IndexError as e:
            Logger.error(str(e))
            Logger.error(f"LENGHT: {len(value)}")


    def transition(self, target:ConnState):
        if self.state == ConnState.IDLE:
            if target == ConnState.SCANNING:
                self.event_start_scan.set()
        elif self.state == ConnState.SCANNING:
            if target == ConnState.CONNECTED:
                self.state = ConnState.CONNECTED
            elif target == ConnState.IDLE:
                self.state = ConnState.IDLE
        elif self.state == ConnState.CONNECTED:
            if target == ConnState.IDLE:
                self.event_disconnected.set()
            elif target == ConnState.RECEIVING:
                self.event_toggle_receive.set()
        elif self.state == ConnState.RECEIVING:
            if target == ConnState.IDLE:
                self.event_disconnected.set()
            elif target == ConnState.CONNECTED:
                self.event_toggle_receive.set()

    def toggle_reception(self):
        self.event_toggle_receive.set()
    
    def send_config(self):
        self.cmd = b'\xa3\x0a'
    
    async def connection_handler(self):
        self.event_start_scan = asyncio.Event()
        self.event_toggle_receive = asyncio.Event()
        self.event_disconnected = asyncio.Event()
        self.event_send_command = asyncio.Event()

        def disconnected_cb(client):
            self.state = ConnState.IDLE
            self.event_disconnected.set()

        while self.app.running:
            
            if self.state == ConnState.IDLE:
                await self.event_start_scan.wait()
                self.state = ConnState.SCANNING
                self.event_start_scan.clear()

            elif self.state == ConnState.SCANNING:
                try:
                    Logger.info("Scanning")
                    scanned_devices = await bleak.BleakScanner.find_device_by_name("OKDevice", timeout=3)
                    if scanned_devices is None:
                        raise bleak.exc.BleakError("No devices found")
                    self.device = scanned_devices
                    Logger.info(f"Connecting to {self.device.name}")
                    toast(f"Connecting to {self.device.name}: {self.device.rssi} dB")
                    self.transition(ConnState.CONNECTED)
                    #         toast(f"Connecting to {device.name}: {device.rssi} dB")
                    # scanned_devices.sort(key=lambda device: -device.rssi)
                    # for device in scanned_devices:
                    #     Logger.info(f"DEVICE: {device.name}")
                    #     if device.name == "OKDevice":
                    #         Logger.info(f"Connecting to {device.name}: {device.rssi} dB")
                    #         toast(f"Connecting to {device.name}: {device.rssi} dB")
                    #         self.device = device
                    #         self.transition(ConnState.CONNECTED)
                    #         break
                        # raise bleak.exc.BleakError("No OpenKardio Device found")
                except bleak.exc.BleakError as e:
                    Logger.error(f"SCANNING: {e}")
                    toast(str(e))
                    self.transition(ConnState.IDLE)

            elif self.state == ConnState.CONNECTED or self.state == ConnState.RECEIVING:
                try:
                    async with bleak.BleakClient(self.device, disconnected_callback=disconnected_cb) as client:
                        raw_device_info = await client.read_gatt_char("5e6c5002-05d8-463b-b21d-eed2204c2002")
                        self.parse_device_info(raw_device_info)
                        while self.state == ConnState.CONNECTED or self.state == ConnState.RECEIVING:
                            await asyncio.wait(
                                {
                                    self.event_toggle_receive.wait(),
                                    self.event_send_command.wait(),
                                    self.event_disconnected.wait()
                                },
                                return_when=asyncio.FIRST_COMPLETED)
                            Logger.info("EVENT TRIGGERED")
                            if self.event_toggle_receive.is_set():
                                self.event_toggle_receive.clear()
                                Logger.info("TOGGLE RECEIVE EVENT")
                                if self.state == ConnState.CONNECTED:
                                    Logger.info("About to start the exam")
                                    self.state = ConnState.RECEIVING
                                    await client.start_notify("5e6c5001-05d8-463b-b21d-eed2204c2002", self.frame_handler)
                                    await asyncio.sleep(0.12)
                                    await client.write_gatt_char("5e6c5002-05d8-463b-b21d-eed2204c2002", b'\x00')
                                    Logger.info("Exam started")
                                    
                                elif self.state == ConnState.RECEIVING:
                                    Logger.info("About to finish the exam")
                                    self.state = ConnState.CONNECTED
                                    await client.stop_notify("5e6c5001-05d8-463b-b21d-eed2204c2002")
                                    await client.write_gatt_char("5e6c5002-05d8-463b-b21d-eed2204c2002", b'\xff')
                                    Logger.info("Exam finished")
                                    
                            elif self.event_send_command.is_set():
                                self.event_send_command.clear()
                                Logger.info("SEND COMMAND EVENT")
                                await client.write_gatt_char("5e6c5002-05d8-463b-b21d-eed2204c2002", self.cmd)
                            elif self.event_disconnected.is_set():
                                self.event_disconnected.clear()
                                Logger.info("DISCONNECT EVENT")
                                self.state == ConnState.IDLE
                                break

                except (bleak.exc.BleakError,AssertionError) as e:
                    Logger.error(f"CONNECTED: {e}")
                    toast(str(e))
                    self.transition(ConnState.IDLE)
