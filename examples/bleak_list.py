import sys
sys.path.append("..")
import asyncio
from bleak import BleakClient
from bleak import BleakScanner
from PUI import *
from PUI.PySide6 import *

async def scanner(state):
    stop_event = asyncio.Event()

    def discovered(device, advertising_data):
        # if not device.name:
        #     return
        devs = [d for d in state.scanned_devices if d[0].address==device.address]
        if devs:
            devs[0][1] = advertising_data
        else:
            state.scanned_devices.append([device, advertising_data])
        # print(device)

    async with BleakScanner(discovered) as scanner:
        await stop_event.wait()


@PUI
def DeviceView(device, advertising_data):
    Label(f"{device.address} {device.name} {advertising_data.rssi}")

class GUI(Window):
    def __init__(self, state):
        super().__init__(title="BLE List")
        self.state = state

    def content(self):
        with VBox():
            Label(f"Found {len(self.state.scanned_devices)} devices")
            for device, advertising_data in self.state.scanned_devices:
                DeviceView(device, advertising_data)


state = State()
state.scanned_devices = []

gui = GUI(state)
loop = gui.get_event_loop()
loop.create_task(scanner(state))
loop.run_forever()