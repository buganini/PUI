"""A three-column Grid with two Labels and a TextField in each row.

Run from the repository root:
    env/bin/python -m PUI.examples.grid_sizing PySide6
    env/bin/python -m PUI.examples.grid_sizing web

Web requires `make web-build`; open the URL printed at startup.
Resize the window to observe how the Grid distributes its available width.
"""
import argparse
from importlib import import_module


def create_application(backend):
    ui = import_module('PUI.' + backend)

    class GridSizing(ui.Application):
        def setup(self):
            self.values = ui.State()
            self.values.first = 'One'
            self.values.second = 'A longer value'
            self.values.third = ''

        def content(self):
            with ui.Window(size=(900, 240)):
                with ui.Scroll():
                    # Leave widths, weights and column stretches to the backend.
                    with ui.Grid():
                        ui.Label('Item A').grid(row=0, column=0)
                        ui.Label(self.values.first).id('first-value').grid(row=0, column=1)
                        ui.TextField(self.values('first')).grid(row=0, column=2)

                        ui.Label('Longer item label').grid(row=1, column=0)
                        ui.Label(self.values.second).id('second-value').grid(row=1, column=1)
                        ui.TextField(self.values('second')).grid(row=1, column=2)

                        ui.Label('Item C').grid(row=2, column=0)
                        ui.Label(self.values.third).id('third-value').grid(row=2, column=1)
                        ui.TextField(self.values('third')).grid(row=2, column=2)

    return GridSizing(title='Grid sizing')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('backend', nargs='?', default='PySide6',
                        choices=('PySide6', 'web', 'wx', 'tkinter', 'textual'))
    parser.add_argument('--bind', default='127.0.0.1:0', help='Web listener (default: 127.0.0.1:0)')
    args = parser.parse_args(argv)
    app = create_application(args.backend)
    if args.backend == 'web':
        app.start(bind=args.bind, passthru=True)
    else:
        app.start()


if __name__ == '__main__':
    main()
