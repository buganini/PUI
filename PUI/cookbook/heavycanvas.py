from .config import *


class HeavyCanvasExample(PUIView):
    """Synthetic market chart with a deliberately large Painter display list."""

    SAMPLE_COUNTS = (1000, 3000, 5000, 7500, 10000, 15000, 20000, 25000, 30000,
                     120000, 250000, 350000, 500000, 1000000)

    @classmethod
    def sample_counts(cls):
        # Browser display lists retain their existing command/transport budgets.
        if PUI_BACKEND in ('web', 'pyodide'):
            return tuple(count for count in cls.SAMPLE_COUNTS if count <= 30000)
        return cls.SAMPLE_COUNTS

    BACKGROUND = 0x101A2B
    GRID = 0x28374D
    MUTED = 0x94A6BE
    TEXT = 0xDCE5F2
    UP = 0xF07883
    DOWN = 0x45C6B0
    GOLD = 0xF5C45E
    BLUE = 0x71B7FF
    PURPLE = 0xBA95EF

    def setup(self):
        self.state = State()
        self.state.samples = str(self.sample_counts()[0])
        self.state.seed = 42
        self.state.continuous = False
        self.state.full_frame_changes = False
        self._paint_sequence = 0
        self.state.cursor = None
        self.state.viewport = None
        self.state("samples").change(self.reset_zoom)
        self._cache_key = None
        self._visible_key = None
        self._plot_size = (0, 0)

    def content(self):
        key = (int(self.state.samples), self.state.seed)
        if key != self._cache_key:
            self._data = self.generate(*key)
            self._cache_key = key
        start, stop = self.visible_bounds()
        visible_key = (key, start, stop)
        if visible_key != self._visible_key:
            self._visible_data = (self._data if start == 0 and stop == key[0]
                                  else self.chart_data(self._data["rows"][start:stop]))
            self._visible_key = visible_key
        rows = self._visible_data["rows"]
        with VBox().layout(weight=1):
            with HBox():
                Label("Sessions")
                with ComboBox(text_model=self.state("samples")):
                    for count in self.sample_counts():
                        ComboBoxItem(f"{count}")
                Button("Regenerate").click(self.regenerate)
                Button("Reset zoom").click(self.reset_zoom)
                if PUI_BACKEND in ('web', 'pyodide', 'PySide6', 'wx'):
                    Checkbox("Run continuously (FPS)", self.state("continuous"))
                    Checkbox("Full-frame changes", self.state("full_frame_changes"))
            Label(f"{key[0]:,} sessions | Seed {self.state.seed} | ~{9 * len(rows):,} draw calls")
            Label(f"Visible: {len(rows):,} / {key[0]:,} sessions | Zoom {key[0] / len(rows):.2f}x")
            Label("Synthetic data" if PUI_BACKEND == "tkinter"
                  else "Synthetic data / Hover to inspect / Wheel up to zoom in, down to zoom out")
            Label(f"{rows[0]['label']} - {rows[-1]['label']} | Last {rows[-1]['close']:,.2f}")
            with Scroll().layout(weight=1):
                self.canvas = (Canvas(self.paint, self._visible_data, self.state.cursor,
                    **({"show_fps": True} if PUI_BACKEND in ("web", "pyodide", "PySide6", "wx") else {}))
                    .layout(height=720, weight=1)
                    .style(bgColor=self.BACKGROUND)
                    .mousemove(self.hover).mouseleave(self.leave).wheel(self.zoom))

    def regenerate(self, event):
        self.state.seed += 1

    def visible_bounds(self):
        viewport = self.state.viewport
        # A new dataset always starts at its full extent.
        if viewport is not None and viewport[0] == self._cache_key:
            return viewport[1:]
        return 0, len(self._data["rows"])

    def reset_zoom(self, event):
        self.state.viewport = None

    def zoom(self, event):
        width, height = self._plot_size
        left, right = 62, width - 14
        if width < 320 or height < 360 or not left <= event.x <= right:
            return
        # Take direction only: wheel angles and pixel distances are distinct
        # units. Web also exposes native line/page deltas with the opposite sign.
        delta = getattr(event, "v_delta", 0) or getattr(event, "y_delta", 0)
        if not delta and getattr(event, "delta_mode", None) in ("line", "page"):
            delta = -event.delta_y
        if not delta:
            return
        start, stop = self.visible_bounds()
        total, count = len(self._data["rows"]), stop - start
        new_count = max(min(20, total), min(total, round(count * (0.8 if delta > 0 else 1.25))))
        if new_count == count:
            return
        anchor = (event.x - left) / (right - left)
        start = max(0, min(total - new_count, round(start + anchor * (count - new_count))))
        self.state.viewport = (self._cache_key, start, start + new_count)

    def hover(self, event):
        self.state.cursor = (event.x, event.y)

    def leave(self, event):
        self.state.cursor = None

    @staticmethod
    def sample_labels(count):
        """Include 20 warmup rows; large datasets use zero-based visible indices."""
        if count > 500000:
            for index in range(-20, count):
                yield f'{index:,}'
            return
        from datetime import date, timedelta
        dates = []
        day = date(2026, 10, 13)
        step = timedelta(days=-1)
        while len(dates) < count + 20:
            if day.weekday() < 5:
                dates.append(day.isoformat())
            day += step
        yield from reversed(dates)

    @staticmethod
    def generate(count, seed):
        """Seeded OHLCV; 20-session bands, smoothed stochastic 9, Wilder RSI 14."""
        from math import exp, sqrt
        from random import Random

        rng = Random(seed)
        rows = []
        close, k, d = 320.0, 50.0, 50.0
        gain = loss = 0.0
        for i, label in enumerate(HeavyCanvasExample.sample_labels(count)):
            opening = close * exp(rng.gauss(0, 0.003))
            closing = opening * exp(1.7 / count + rng.gauss(0, 0.014))
            high = max(opening, closing) * (1 + rng.uniform(0.001, 0.012))
            low = min(opening, closing) * (1 - rng.uniform(0.001, 0.012))
            volume = int(rng.lognormvariate(17.0, 0.45))
            row = dict(label=label, open=opening, high=high, low=low,
                       close=closing, volume=volume)
            rows.append(row)

            # Keep the full dataset and indicators outside State. Mouse movement
            # reuses these values; it only changes the small cursor tuple.
            window = rows[-20:]
            mid = sum(r["close"] for r in window) / len(window)
            sigma = sqrt(sum((r["close"] - mid) ** 2 for r in window) / len(window))
            recent = rows[-9:]
            floor = min(r["low"] for r in recent)
            ceiling = max(r["high"] for r in recent)
            raw_k = 100 * (closing - floor) / (ceiling - floor)
            k = (2 * k + raw_k) / 3
            d = (2 * d + k) / 3
            change = closing - close
            if i:
                period = min(i, 14)
                gain += (max(change, 0) - gain) / period
                loss += (max(-change, 0) - loss) / period
            rsi = 100 * gain / (gain + loss) if gain + loss else 50.0
            row.update(mid=mid, upper=mid + 2 * sigma, lower=mid - 2 * sigma,
                       k=k, d=d, rsi=rsi)
            close = closing

        return HeavyCanvasExample.chart_data(rows[20:])

    @staticmethod
    def chart_data(rows):
        """Autoscale the visible rows without recalculating their indicators."""
        low = min(min(r["low"], r["lower"]) for r in rows)
        high = max(max(r["high"], r["upper"]) for r in rows)
        padding = (high - low) * 0.06
        return dict(rows=rows, price_range=(low - padding, high + padding),
                    volume_max=max(r["volume"] for r in rows) * 1.05)

    def paint(self, canvas, data, cursor):
        # Change every command's explicit color without regenerating the data
        # or copying the completed command list. Geometry/workload stays fixed.
        self._paint_sequence += 1
        tint = self._paint_sequence % 16 if self.state.full_frame_changes else 0
        grid, muted, text, up, down, gold, blue, purple = (
            color ^ tint for color in (self.GRID, self.MUTED, self.TEXT,
                self.UP, self.DOWN, self.GOLD, self.BLUE, self.PURPLE))
        rows = data["rows"]
        width, height = canvas.width, canvas.height
        self._plot_size = (width, height)
        if width < 320 or height < 360:
            canvas.drawText(10, 10, "Enlarge the chart to view data.", size=9, color=text)
            return
        left, right = 62, width - 14
        step = (right - left) / len(rows)
        x = lambda i: left + (i + 0.5) * step
        # A requested height keeps all four panels legible in the cookbook's
        # scroll area. Width follows the available Canvas drawing space.
        unit = (height - 4 * 44 - 16) / 6
        panels = []
        top = 24
        for title, scale, limits in (
            ("Price / Bollinger 20", 3, data["price_range"]),
            ("Volume", 1, (0, data["volume_max"])),
            ("K / D (9, 3) - gold / blue", 1, (0, 100)),
            ("RSI 14", 1, (0, 100)),
        ):
            bottom = top + unit * scale
            panels.append((top, bottom, limits))
            canvas.drawText(left, top - 21, title, size=10, color=text)
            low, high = limits
            for fraction in (0, 0.5, 1):
                y = bottom - fraction * (bottom - top)
                value = low + fraction * (high - low)
                label = f"{value / 1e6:.1f}M" if title == "Volume" else f"{value:.1f}"
                canvas.drawLine(left, y, right, y, color=grid)
                canvas.drawText(3, y - 8, label, size=9, color=muted)
            ticks = (0, len(rows) // 2, len(rows) - 1) if width >= 430 else (0, len(rows) - 1)
            for i in ticks:
                label_x = max(left, min(x(i) - 34, right - 72))
                canvas.drawText(label_x, bottom + 7, rows[i]["label"], size=9, color=muted)
            top = bottom + 44

        def y(value, panel):
            top, bottom, (low, high) = panels[panel]
            return bottom - (value - low) / (high - low) * (bottom - top)

        # Native backends rasterize rectangle widths to integer pixels.
        body = max(1, min(5, int(step * 0.65)))
        for i, row in enumerate(rows):
            cx = x(i)
            color = up if row["close"] >= row["open"] else down
            canvas.drawLine(cx, y(row["low"], 0), cx, y(row["high"], 0), color=color)
            a, b = y(row["open"], 0), y(row["close"], 0)
            canvas.drawRect(cx - body / 2, min(a, b), cx + body / 2,
                            max(a, b) + 1, fill=color)
            canvas.drawRect(cx - body / 2, y(row["volume"], 1),
                            cx + body / 2, panels[1][1], fill=color)

        # Individual segments deliberately exercise thousands of Painter calls
        # instead of collapsing each indicator into a single polyline command.
        for key, panel, color in (
            ("upper", 0, blue), ("mid", 0, gold), ("lower", 0, purple),
            ("k", 2, gold), ("d", 2, blue), ("rsi", 3, gold),
        ):
            for i in range(1, len(rows)):
                canvas.drawLine(x(i - 1), y(rows[i - 1][key], panel),
                                x(i), y(rows[i][key], panel), color=color, width=2)

        if cursor is not None:
            mx, my = cursor
            if left <= mx <= right and panels[0][0] <= my <= panels[-1][1]:
                index = min(len(rows) - 1, int((mx - left) / step))
                self.tooltip(canvas, rows[index], x(index), my, left, right, panels, tint)

        # True requests the next frame through the backend's normal redraw/ACK
        # scheduling. No State writes or timers are needed to saturate painting.
        return self.state.continuous

    @classmethod
    def tooltip(cls, canvas, row, x, y, left, right, panels, tint=0):
        canvas.drawLine(x, panels[0][0], x, panels[-1][1], color=cls.MUTED ^ tint)
        if any(top <= y <= bottom for top, bottom, _ in panels):
            canvas.drawLine(left, y, right, y, color=cls.MUTED ^ tint)
        lines = (
            row["label"] + " | Synthetic OHLCV",
            f"Open {row['open']:,.2f}   High {row['high']:,.2f}",
            f"Low  {row['low']:,.2f}   Close {row['close']:,.2f}",
            f"Volume {row['volume']:,}",
            f"Band mid {row['mid']:,.2f}",
            f"Upper {row['upper']:,.2f}   Lower {row['lower']:,.2f}",
            f"K / D {row['k']:.2f} / {row['d']:.2f}   RSI {row['rsi']:.2f}",
        )
        box_width = min(330, canvas.width - 20)
        bx = min(x + 16, canvas.width - box_width - 10)
        if x + 16 + box_width > right:
            bx = max(10, x - box_width - 16)
        by = panels[0][0] + 6
        canvas.drawRect(bx, by, bx + box_width, by + 144, fill=0x25374E ^ tint)
        for i, line in enumerate(lines):
            canvas.drawText(bx + 10, by + 8 + i * 18, line, size=9, color=cls.TEXT ^ tint)
