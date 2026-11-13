"""Open and close the LVGL cookbook in real SDL2/X11 windows.

    PYTHONPATH=. env/bin/python tests/lvgl_native_windows.py

X11 cases run on a private Xvfb server (skipped without Xvfb, xwininfo and
xwd or without the liblvgl_x11 build). SDL2 cases need the liblvgl_sdl2 build
and a usable SDL video driver (a desktop session, or SDL_VIDEODRIVER).
Each case runs the application in a child process: shutdown bugs show up as
crashes or exits that skip cleanup, which a child's exit status captures.
"""
import ctypes
import ctypes.util
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LVGL = ROOT / 'PUI' / 'lvgl'
DONE = 'exited cleanly'

# The child opens the cookbook, optionally opens the first menu (so its popup
# lives on the top layer while the window closes), and signals readiness.
CHILD = r'''
import os, sys
os.environ['PUI_BACKEND'] = 'lvgl'
from PUI.cookbook.app import Cookbook
from PUI.lvgl import MenuBar
from PUI.lvgl.base import runtime
from PUI.lvgl.testing import find
mode = sys.argv[1]
app = Cookbook()

def ready():
    if 'menu' in mode:
        find(app, lambda n: isinstance(n, MenuBar))._pressed(0)
    print('ready', flush=True)
    if mode == 'quit':
        app.quit()
    elif mode.startswith('sdl-close'):
        import ctypes, ctypes.util
        sdl = ctypes.CDLL(os.environ['PUI_TEST_SDL'])
        class Event(ctypes.Structure):
            _fields_ = [('type', ctypes.c_uint32), ('timestamp', ctypes.c_uint32),
                        ('windowID', ctypes.c_uint32), ('event', ctypes.c_uint8),
                        ('pad', ctypes.c_uint8 * 43)]
        for wid in range(1, 65):  # LVGL ignores ids that are not its window
            e = Event(type=0x200, windowID=wid, event=14)  # SDL_WINDOWEVENT_CLOSE
            sdl.SDL_PushEvent(ctypes.byref(e))
        sdl.SDL_PushEvent(ctypes.byref(Event(type=0x100)))  # SDL_QUIT

runtime.post_timer(1.0, ready)
runtime.post_timer(30, app.quit)  # safety net: never hang the test run
app.run()
print('exited cleanly', flush=True)
'''


def build(name):
    return any(p.name.startswith('liblvgl_' + name + '.') for p in LVGL.iterdir())


def tool(name):
    return shutil.which(name) or (f'/opt/X11/bin/{name}' if os.path.exists(f'/opt/X11/bin/{name}') else None)


class Child:
    def __init__(self, driver, mode, env=None):
        environment = dict(os.environ, PYTHONPATH=str(ROOT), PUI_LVGL_DRIVER=driver, **(env or {}))
        environment.pop('PUI_LVGL_LIB', None)
        self.process = subprocess.Popen([sys.executable, '-u', '-X', 'faulthandler', '-c', CHILD, mode],
                                        cwd=ROOT, env=environment, text=True,
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.output = ''

    def wait_ready(self, timeout=30):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            line = self.process.stdout.readline()
            if not line:
                break
            self.output += line
            if line.strip() == 'ready':
                return True
        return False

    def finish(self, timeout=30):
        try:
            rest, _ = self.process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            self.process.kill()
            rest, _ = self.process.communicate()
        self.output += rest
        return self.process.returncode


class NativeCase(unittest.TestCase):
    def assertClean(self, child, code):
        self.assertEqual(code, 0, child.output[-2000:])
        self.assertIn(DONE, child.output, child.output[-2000:])


@unittest.skipUnless(build('x11') and tool('Xvfb') and tool('xwininfo') and tool('xwd'),
                     'needs the liblvgl_x11 build, Xvfb, xwininfo and xwd')
class X11Windows(NativeCase):
    display = ':%d' % (90 + os.getpid() % 9)

    def setUp(self):
        self.server = subprocess.Popen([tool('Xvfb'), self.display, '-screen', '0', '1280x900x24'],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)
        self.env = {'DISPLAY': self.display}

    def tearDown(self):
        if self.server.poll() is None:
            self.server.kill()
        self.server.wait()

    def window(self):
        out = subprocess.run([tool('xwininfo'), '-root', '-tree'], env=dict(os.environ, **self.env),
                             capture_output=True, text=True).stdout
        match = re.search(r'(0x[0-9a-f]+) "Cookbook \(lvgl\)": \(\)\s+(\d+)x(\d+)', out)
        self.assertIsNotNone(match, 'no Cookbook window:\n' + out)
        return int(match.group(1), 16), int(match.group(2)), int(match.group(3))

    def child(self, mode):
        child = Child('x11', mode, self.env)
        self.assertTrue(child.wait_ready(), child.output)
        return child

    def test_window_created_at_declared_size(self):
        child = self.child('wait')
        _, width, height = self.window()
        self.assertEqual((width, height), (1024, 768))
        self.close_window()
        self.assertClean(child, child.finish())

    def test_first_frame_is_fully_drawn(self):
        child = self.child('wait')
        wid, width, height = self.window()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, 'w.xwd')
            subprocess.run([tool('xwd'), '-silent', '-id', hex(wid), '-out', path],
                           env=dict(os.environ, **self.env), check=True)
            pixels = read_xwd(path)
        # The dark "Code" pane must be on screen, not only the menu strip.
        code = [pixels(x, y) for x in range(200, 500, 10) for y in range(300, 600, 10)]
        dark = sum(1 for r, g, b in code if r + g + b < 240) / len(code)
        self.assertGreater(dark, 0.5)
        self.close_window()
        self.assertClean(child, child.finish())

    def test_quit(self):
        child = self.child('quit')
        self.assertClean(child, child.finish())

    def test_close_button(self):
        child = self.child('wait')
        self.close_window()
        self.assertClean(child, child.finish())

    def test_close_button_with_open_menu(self):
        child = self.child('wait-menu')
        self.close_window()
        self.assertClean(child, child.finish())

    def test_server_gone(self):
        child = self.child('wait')
        self.server.kill()
        code = child.finish()
        self.assertClean(child, code)
        self.assertIn('connection to the X server was lost', child.output)

    def close_window(self):
        """Send WM_DELETE_WINDOW, as a window manager's close button does."""
        wid, _, _ = self.window()
        x11 = ctypes.CDLL(ctypes.util.find_library('X11') or '/opt/X11/lib/libX11.dylib')
        x11.XOpenDisplay.restype = ctypes.c_void_p
        x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        x11.XInternAtom.restype = ctypes.c_ulong
        x11.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
        x11.XSendEvent.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_long, ctypes.c_void_p]
        x11.XFlush.argtypes = x11.XCloseDisplay.argtypes = [ctypes.c_void_p]

        class ClientMessage(ctypes.Structure):
            _fields_ = [('type', ctypes.c_int), ('serial', ctypes.c_ulong), ('send_event', ctypes.c_int),
                        ('display', ctypes.c_void_p), ('window', ctypes.c_ulong),
                        ('message_type', ctypes.c_ulong), ('format', ctypes.c_int), ('l', ctypes.c_long * 5)]

        class XEvent(ctypes.Union):
            _fields_ = [('xclient', ClientMessage), ('pad', ctypes.c_long * 24)]
        display = x11.XOpenDisplay(self.display.encode())
        event = XEvent()
        event.xclient.type = 33  # ClientMessage
        event.xclient.window = wid
        event.xclient.message_type = x11.XInternAtom(display, b'WM_PROTOCOLS', 0)
        event.xclient.format = 32
        event.xclient.l[0] = x11.XInternAtom(display, b'WM_DELETE_WINDOW', 0)
        x11.XSendEvent(display, wid, 0, 0, ctypes.byref(event))
        x11.XFlush(display)
        x11.XCloseDisplay(display)


def read_xwd(path):
    with open(path, 'rb') as f:
        data = f.read()
    header = struct.unpack('>25I', data[:100])
    size, width, height, byte_order, bpl, colors = header[0], header[4], header[5], header[7], header[12], header[19]
    pixels = data[size + colors * 12:]

    def pixel(x, y):
        p = pixels[y * bpl + x * 4:y * bpl + x * 4 + 4]
        return (p[2], p[1], p[0]) if byte_order == 0 else (p[1], p[2], p[3])
    return pixel


def sdl_library():
    path = ctypes.util.find_library('SDL2')
    if path:
        return path
    try:
        libdir = subprocess.check_output(['pkg-config', '--variable=libdir', 'sdl2'], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return None
    for name in ('libSDL2.dylib', 'libSDL2-2.0.so.0', 'libSDL2.so'):
        if os.path.exists(os.path.join(libdir, name)):
            return os.path.join(libdir, name)
    return None


@unittest.skipUnless(build('sdl2') and sdl_library(), 'needs the liblvgl_sdl2 build and libSDL2')
class SDL2Windows(NativeCase):
    def child(self, mode):
        child = Child('sdl2', mode, {'PUI_TEST_SDL': sdl_library()})
        if not child.wait_ready():
            child.finish()
            if 'Failed to initialize LVGL' in child.output:
                self.skipTest('no usable SDL video driver')
            self.fail(child.output)
        return child

    def test_quit(self):
        child = self.child('quit')
        self.assertClean(child, child.finish())

    def test_close_button(self):
        child = self.child('sdl-close')
        self.assertClean(child, child.finish())

    def test_close_button_with_open_menu(self):
        child = self.child('sdl-close-menu')
        self.assertClean(child, child.finish())


if __name__ == '__main__':
    unittest.main()
