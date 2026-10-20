from .config import *


class GridExample(PUIView):
    def content(self):
        Label('Manual Grid: tile coordinates and spans are explicit.')
        with Grid().layout(weight=1):
            for name, row, column, rows, columns, background, foreground in (
                ('A', 0, 0, 2, 1, 0x244B5A, 0xFFF7E6),
                ('B', 0, 1, 1, 2, 0xA84A3A, 0xFFF7E6),
                ('C', 1, 1, 1, 1, 0xD97B35, 0x1C2A30),
                ('D', 1, 2, 2, 1, 0xF2E6CF, 0x1C2A30),
                ('E', 2, 0, 1, 2, 0x8FA38A, 0x1C2A30),
            ):
                Label(f'{name}\nrow={row}, column={column}\nspan={rows} × {columns}').grid(
                    row=row, column=column, rowspan=rows, columnspan=columns,
                ).style(bgColor=background, color=foreground).layout(
                    padding=8, height=rows * 60,
                ).tStyle(bgColor=background, color=foreground).tLayout(height=rows * 4, padding=1)
