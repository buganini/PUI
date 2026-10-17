"""Small managed child without a GUI, exercising the real IPC transport."""
import os
import threading
from PUI.ai.ipc import connect
from PUI.options import Options, load_environment
from PUI.state_refs import noop_publish

load_environment()
child = connect()
stop = threading.Event()
child.ready(lambda callback: callback(), stop.set)
noop_publish('example.count', int(Options.get('example.count', '0')) + 1)
noop_publish('example.special', '#hello=世界')
print('child ready', flush=True)
stop.wait(15)
child.close()
