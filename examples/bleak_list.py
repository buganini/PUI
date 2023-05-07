import sys
sys.path.append("..")
import asyncio
from bleak import BleakClient
from bleak import BleakScanner
from PUI.PySide6 import *

async def Scanner(state):
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

class GUI(Application):
    def __init__(self, state):
        super().__init__()
        self.state = state

    def content(self):
        with Window(title="BLE List"):
            with VBox():
                Label(f"Found {len(self.state.scanned_devices)} devices")
                for device, advertising_data in self.state.scanned_devices:
                    DeviceView(device, advertising_data)


state = State()
state.scanned_devices = []

def bleak_thread():
    scanner = Scanner(state)
    loop = asyncio.new_event_loop()
    loop.create_task(scanner)
    loop.run_forever()

t = threading.Thread(target=bleak_thread)
t.start()
gui = GUI(state)
gui.run()
