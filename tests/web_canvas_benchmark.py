"""Compare full-frame and delta encoding with identical HeavyCanvas hover frames.

env/bin/python tests/web_canvas_benchmark.py [samples] [--moves 20] [--warmup 3]
Default: 1000 samples; use a supported Web HeavyCanvas count.
Both codecs keep the same 4 MiB zstd history and flush complete render batches.
"""
import argparse
import asyncio
import json
import os
import platform
import statistics
import sys
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['PUI_BACKEND'] = 'web'
import msgpack
import zstandard
from cookbook.heavycanvas import HeavyCanvasExample
from PUI.web import Application, Window
from PUI.web.protocol import StreamCodec
from PUI.web.render import RenderStream
from PUI.web.runtime import Runtime


class App(Application):
    def content(self):
        with Window():
            self.view = HeavyCanvasExample()


async def benchmark(count, moves=20, warmup=3):
    runtime = Runtime(asyncio.get_running_loop())
    stream, delta_codec, full_codec = RenderStream(), StreamCodec(), StreamCodec()
    times = {key: [] for key in ('painter_ms', 'snapshot_without_painter_ms', 'offer_ms',
                                'diff_ms', 'delta_encode_ms', 'full_encode_ms',
                                'delta_commands', 'delta_msgpack_bytes', 'full_msgpack_bytes',
                                'delta_wire_bytes', 'full_wire_bytes')}
    try:
        runtime.app = App(); runtime.app.sync()
        view = runtime.app.view
        view.state.samples = str(count); runtime.flush(); runtime.snapshot()
        runtime.canvas_control('measure', dict(node_id=view.canvas.ui.id, measure_rev=1,
                                              width=900, height=720, dpr=1, visible=True))
        def ack(body, frame):
            stream.acknowledge(render_rev=body['rev'], applied_rev=body['rev'], status='applied')
            runtime.canvas_control('canvas_ack', {key: frame[key] for key in
                ('node_id', 'frame_rev', 'measure_rev')} | {'status': 'drawn'})
        initial = runtime.snapshot(copy=False)
        stream.offer(initial, processed_seq=0, copy=False, trusted=True)
        body = stream.next_render(copy=False)
        message = dict(v=1, type='render', session='benchmark', seq=1, body=body)
        delta_codec.encode(message); full_codec.encode(message)
        ack(body, initial['canvases'][0])
        for i in range(moves + warmup):
            if i == warmup:
                for values in times.values():
                    values.clear()
            view.hover(SimpleNamespace(x=200 + i * 23, y=100 + i))
            runtime.flush()
            painter = view.canvas.painter
            def timed_painter(canvas, *args):
                start = time.perf_counter()
                result = painter(canvas, *args)
                times['painter_ms'].append((time.perf_counter() - start) * 1000)
                return result
            view.canvas.painter = timed_painter
            start = time.perf_counter()
            try:
                target = runtime.snapshot(copy=False)
            finally:
                view.canvas.painter = painter
            times['snapshot_without_painter_ms'].append((time.perf_counter() - start) * 1000 - times['painter_ms'][-1])
            start = time.perf_counter(); stream.offer(target, processed_seq=i + 1, copy=False, trusted=True)
            times['offer_ms'].append((time.perf_counter() - start) * 1000)
            start = time.perf_counter(); body = stream.next_render(copy=False)
            times['diff_ms'].append((time.perf_counter() - start) * 1000)
            frame = target['canvases'][0]
            full_body = dict(body, ops=[dict(op='put_canvas', frame=frame) if op['op'] == 'patch_canvas'
                                        else op for op in body['ops']])
            message = dict(v=1, type='render', session='benchmark', seq=i + 2, body=body)
            full_message = dict(message, body=full_body)
            for name, codec, value in (('delta', delta_codec, message), ('full', full_codec, full_message)):
                start = time.perf_counter(); packet = codec.encode(value)
                times[name + '_encode_ms'].append((time.perf_counter() - start) * 1000)
                times[name + '_wire_bytes'].append(len(packet))
                times[name + '_msgpack_bytes'].append(len(msgpack.packb(value, use_bin_type=True)))
            times['delta_commands'].append(sum(len(op['frame']['commands']) for op in body['ops']
                                              if op['op'] in ('put_canvas', 'patch_canvas')))
            ack(body, frame)
        return dict(samples=count, moves=moves, warmup=warmup,
                    environment=dict(python=platform.python_version(), platform=platform.platform(),
                                     msgpack=msgpack.__version__, zstandard=zstandard.__version__),
                    compression=dict(level=3, window_bytes=4 * 1024 * 1024),
                    dimensions=[900, 720], commands=len(frame['commands']),
                    medians={key: round(statistics.median(values), 3) for key, values in times.items()})
    finally:
        runtime.close(); delta_codec.close(); full_codec.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('samples', type=int, nargs='?', default=1000,
                        choices=HeavyCanvasExample.sample_counts())
    parser.add_argument('--moves', type=int, default=20)
    parser.add_argument('--warmup', type=int, default=3)
    args = parser.parse_args()
    if args.moves < 1 or args.warmup < 0:
        parser.error('--moves must be positive and --warmup must be nonnegative')
    print(json.dumps(asyncio.run(benchmark(args.samples, args.moves, args.warmup)), indent=2))
