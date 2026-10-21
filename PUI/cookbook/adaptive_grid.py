from .config import *


class AdaptiveGridExample(PUIView):
    tiles = (
        ('A', 2, 1, 0x244B5A, 0xFFF7E6), ('B', 1, 1, 0xA84A3A, 0xFFF7E6),
        ('C', 3, 2, 0xD97B35, 0x1C2A30), ('D', 3, 1, 0xF2E6CF, 0x1C2A30),
        ('E', 1, 2, 0x8FA38A, 0x1C2A30), ('F', 1, 1, 0x366C91, 0xFFF7E6),
        ('G', 2, 2, 0xD3B98B, 0x1C2A30),
    )

    def setup(self):
        self.form = State()
        self.form.mode = 'ordered'
        self.form.show_c = True
        self.form.reverse = False
        self.form.text = 'This editor survives reflow'

    def reverse(self, event):
        self.form.reverse = not self.form.reverse

    def content(self):
        with VBox().layout(weight=1).tLayout(padding=1):
            Label('Adaptive Grid: 1–4 columns (labels: rows×cols).\nFour columns from 768 px / 77 cells.')
            Label('Watch blue F (original order; C shown):\nNone → row 4 | True → row 3 | False → row 5')
            with HVBox(minWidth=650, tMinWidth=70):
                RadioButton('Ordered (None)', 'ordered', self.form('mode'))
                RadioButton('Dense (True)', 'dense', self.form('mode'))
                RadioButton('Forward (False)', 'forward', self.form('mode'))
                Checkbox('Show C', self.form('show_c'))
                Button('Reverse tiles').click(self.reverse)
            backfill = {'ordered': None, 'dense': True, 'forward': False}[self.form.mode]
            with Scroll().layout(weight=1):
                grid = Grid().columns(1, dense=backfill).wideColumns(384, 2).wideColumns(576, 3).wideColumns(768, 4)
                grid.tWideColumns(38, 2).tWideColumns(58, 3).tWideColumns(77, 4)
                with grid:
                    tiles = list(reversed(self.tiles)) if self.form.reverse else self.tiles
                    for name, rows, columns, background, foreground in tiles:
                        Label(f'{name}\n{rows}×{columns}').id(name).grid(
                            rowspan=rows, columnspan=columns,
                        ).visible(name != 'C' or self.form.show_c).style(
                            bgColor=background, color=foreground,
                        ).layout(height=rows * 60, padding=6).tStyle(
                            bgColor=background, color=foreground,
                        ).tLayout(height=rows * 4, padding=1)
                    TextField(self.form('text')).id('editor').grid(columnspan=2)
