"""PySide6 on the main thread and Web on another thread, sharing one State.

From the repository root, after installing the PySide6 and Web dependencies:
    make web-build
    env/bin/python -m PUI.examples.dual_backend

Optionally expose the Web UI through a relay using --wstunnel-url and
--wstunnel-token. --wstunnel-bind selects its TCP or Unix socket listener.

The OS assigns an available port. Open the printed URL.
Edit the text, increment the counter, or hover over the curve in either UI;
both display the same State object. Close the desktop window to stop both.
State operations are synchronized. Use with state: for compound updates shared
between threads; native widget operations still belong to their UI thread.
"""
import argparse
import math
from threading import Thread

from PUI import State
from PUI import PySide6
from PUI import web


CURVE = tuple(math.sin(i / 18) + 0.3 * math.cos(i / 7) for i in range(201))


class DualBackend:
    def __init__(self, state):
        super().__init__(title='Shared State · ' + self.backend_name)
        self.state = state
        self._plot_bounds = None

    def increment(self, event):
        with self.state:
            self.state.count += 1

    def hover_curve(self, event):
        if self._plot_bounds is None:
            return
        left, right = self._plot_bounds
        fraction = min(1.0, max(0.0, (event.x - left) / (right - left)))
        # Shared State should use a representation that works across coordinate
        # systems (a data index, domain value, or normalized position). Store the
        # sample index here; each backend maps it to its own canvas coordinates.
        self.state.cursor_index = round(fraction * (len(CURVE) - 1))

    def paint_curve(self, canvas, index):
        canvas.drawRect(0, 0, canvas.width, canvas.height, fill=0x0F172A)
        left, right = 42, canvas.width - 18
        top, bottom = 20, canvas.height - 30
        if right <= left or bottom <= top:
            self._plot_bounds = None
            return
        self._plot_bounds = (left, right)
        for value in (-1, 0, 1):
            y = top + (1.5 - value) / 3 * (bottom - top)
            canvas.drawLine(left, y, right, y, color=0x334155)
            canvas.drawText(8, y - 8, str(value), color=0x94A3B8, size=10)
        points = [(left + i / (len(CURVE) - 1) * (right - left),
                   top + (1.5 - value) / 3 * (bottom - top))
                  for i, value in enumerate(CURVE)]
        canvas.drawPolyline(points, color=0x38BDF8, width=2)
        canvas.drawText(left, bottom + 8, '0', color=0x94A3B8, size=10)
        canvas.drawText(right - 24, bottom + 8, str(len(CURVE) - 1), color=0x94A3B8, size=10)
        if index is not None:
            x, y = points[index]
            canvas.drawLine(x, top, x, bottom, color=0xFBBF24)
            canvas.drawEllipse(x, y, 5, 5, fill=0xFBBF24)
            box_width, box_height = 150, 54
            bx = x + 16
            if bx + box_width > right:
                bx = x - box_width - 16
            bx = max(10, min(bx, canvas.width - box_width - 10))
            by = top + 6
            canvas.drawRect(bx, by, bx + box_width, by + box_height, fill=0x25374E)
            canvas.drawText(bx + 10, by + 8, f'Index: {index}', size=10, color=0xFBBF24)
            canvas.drawText(bx + 10, by + 30, f'Value: {CURVE[index]:.3f}', size=10, color=0xE2E8F0)
        else:
            canvas.drawText(left, top + 6, 'Hover to inspect a sample', size=10, color=0x94A3B8)

    def content(self):
        ui = self.backend
        with ui.Window(size=(680, 560)):
            with ui.VBox().layout(padding=16):
                ui.Label(self.backend_name)
                ui.TextField(self.state('text')).id('text')
                ui.Label('Text: ' + self.state.text).id('text_value')
                ui.Label('Count: ' + str(self.state.count)).id('count')
                ui.Button('Increment').click(self.increment).id('increment')
                index = self.state.cursor_index
                (ui.Canvas(self.paint_curve, index).id('curve')
                 .layout(weight=1).style(bgColor=0x0F172A)
                 .mousemove(self.hover_curve))


class DesktopApp(DualBackend, PySide6.Application):
    backend = PySide6
    backend_name = 'PySide6 · main thread'


class WebApp(DualBackend, web.Application):
    backend = web
    backend_name = 'Web · background thread'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--wstunnel-url', help='Relay ws:// or wss:// URL, including any routing path')
    parser.add_argument('--wstunnel-bind', help='Relay listener (default: tcp://127.0.0.1:0)')
    parser.add_argument('--wstunnel-token', help='Relay HTTP Upgrade path token')
    args = parser.parse_args(argv)
    options = None
    if any(value is not None for value in (args.wstunnel_url, args.wstunnel_bind, args.wstunnel_token)):
        options = {'url': args.wstunnel_url, 'token': args.wstunnel_token}
        if args.wstunnel_bind is not None:
            options['bind'] = args.wstunnel_bind
    state = State()
    state.text = 'Hello from both backends'
    state.count = 0
    # A sample index remains meaningful across different canvas sizes and DPI.
    state.cursor_index = None
    desktop = DesktopApp(state)
    web_app = WebApp(state)
    thread = Thread(target=web_app.start, name='pui-web',
                    kwargs=dict(bind='127.0.0.1:0', passthru=True, wstunnel=options))
    thread.start()
    try:
        web_app.wait_started()
        desktop.start()
    finally:
        try:
            web_app.stop()
        finally:
            thread.join()


if __name__ == '__main__':
    main()
