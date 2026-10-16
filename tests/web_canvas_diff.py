"""Canvas splice equivalence, ACK baselines, cross-language fixtures and timing."""
from copy import deepcopy
import json
import random
import sys
import unittest

from PUI.web.render import RenderStream, diff, same
from web_render import apply, node, state


def frame(revision=1, count=30, **changes):
    result = dict(node_id='canvas', frame_rev=revision, measure_rev=1,
                  width=100, height=80, dpr=1, background='#ffffff', **{'continue': False},
                  commands=[['rect', float(2 + i % 10 * 9), float(2 + i // 10 * 10),
                             float(7 + i % 10 * 9), float(7 + i // 10 * 10),
                             '#ff0000', None, 1.0] for i in range(count)])
    result.update(changes)
    return result


def scene(value):
    canvas = node('canvas', kind='Canvas')
    canvas['layout'] = dict(width=value['width'], height=value['height'])
    result = state(canvas)
    result['canvases'] = [value]
    return result


def fixtures():
    stream = RenderStream()
    frames = [frame()]
    changed = deepcopy(frames[-1]); changed['frame_rev'] += 1
    changed['commands'][12][5] = '#0000ff'; frames.append(changed)
    added = deepcopy(changed); added['frame_rev'] += 1
    added['commands'].extend([added['commands'][-1][:5] + ['#00ff00'] + added['commands'][-1][6:]]); frames.append(added)
    removed = deepcopy(added); removed['frame_rev'] += 1
    del removed['commands'][6:10]; frames.append(removed)
    frames.append(dict(removed, frame_rev=5, background='#cccccc'))
    frames.append(dict(frames[-1], frame_rev=6, measure_rev=2, width=110))
    result = []
    for i, current in enumerate(frames):
        target = scene(current)
        stream.offer(target, processed_seq=i)
        body = stream.next_render()
        result.append(dict(body=body, target=target))
        stream.acknowledge(render_rev=body['rev'], applied_rev=body['rev'], status='applied')
    stream.resync(last_applied_rev=body['rev'])
    result.append(dict(body=stream.next_render(), target=target))
    return result


class CanvasDiffTests(unittest.TestCase):
    def test_native_tuple_splice_without_conversion(self):
        before = scene(frame())
        before['canvases'][0]['commands'] = [tuple(c) for c in before['canvases'][0]['commands']]
        after = deepcopy(before)
        current = after['canvases'][0]
        current['frame_rev'] += 1
        command = current['commands'][12]
        replacement = command[:5] + ('#0000ff',) + command[6:]
        current['commands'][12] = replacement
        stream = RenderStream()
        stream.offer(before, processed_seq=0, copy=False)
        stream.next_render(copy=False)
        stream.acknowledge(render_rev=1, applied_rev=1, status='applied')
        stream.offer(after, processed_seq=1, copy=False)
        body = stream.next_render(copy=False)
        patch = body['ops'][0]
        self.assertEqual((patch['op'], patch['start'], patch['delete_count']), ('patch_canvas', 12, 1))
        self.assertIs(patch['frame']['commands'][0], replacement)
        self.assertTrue(same(apply(before, body['ops']), after))
        self.assertFalse(same(('line', True), ('line', 1)))

    def test_splice_fixtures_and_full_resize_recovery(self):
        cases = fixtures()
        self.assertEqual(cases[0]['body']['mode'], 'snapshot')
        previous = cases[0]['target']
        for case in cases[1:-1]:
            self.assertTrue(same(apply(previous, case['body']['ops']), case['target']))
            previous = case['target']
        patches = [c['body']['ops'][0] for c in cases[1:5]]
        self.assertEqual([p['op'] for p in patches], ['patch_canvas'] * 4)
        self.assertEqual([len(p['frame']['commands']) for p in patches], [1, 1, 0, 0])
        self.assertEqual(patches[0]['start'], 12)
        self.assertEqual(patches[0]['delete_count'], 1)
        self.assertEqual(cases[-2]['body']['ops'][-1]['op'], 'put_canvas')
        self.assertEqual(cases[-1]['body']['mode'], 'snapshot')
        self.assertEqual(cases[-1]['body']['canvases'], previous['canvases'])

    def test_random_insert_delete_replace_and_empty_frames(self):
        rng = random.Random(42)
        before = scene(frame(count=100))
        for rev in range(2, 102):
            after = deepcopy(before)
            f = after['canvases'][0]; f['frame_rev'] = rev
            start = rng.randrange(len(f['commands']) + 1)
            end = start + rng.randrange(len(f['commands']) - start + 1)
            f['commands'][start:end] = frame(count=rng.randrange(20))['commands']
            saved = deepcopy((before, after))
            self.assertTrue(same(apply(before, diff(before, after)), after))
            self.assertEqual((before, after), saved)
            before = after
        self.assertEqual(diff(before, scene(frame(102, count=0)))[-1]['op'], 'put_canvas')

    def test_full_frame_fallback_and_output_isolation(self):
        before = scene(frame())
        for overrides in (dict(measure_rev=2), dict(width=200), dict(height=100),
                          dict(dpr=2), dict(commands=frame(count=1)['commands'])):
            after = scene(frame(2, **overrides))
            self.assertEqual(diff(before, after)[-1]['op'], 'put_canvas')
        after = scene(frame(2))
        for command in after['canvases'][0]['commands']:
            command[5] = '#000000'
        self.assertEqual(diff(before, after)[0]['op'], 'put_canvas')
        after['canvases'][0]['commands'] = deepcopy(before['canvases'][0]['commands'])
        after['canvases'][0]['commands'][0][5] = '#00ff00'
        update = diff(before, after)[0]
        update['frame']['commands'][0][5] = '#000000'
        self.assertEqual(after['canvases'][0]['commands'][0][5], '#00ff00')

    def test_only_acknowledged_frame_is_a_base_and_retry_is_immutable(self):
        stream = RenderStream()
        first = scene(frame())
        stream.offer(first, processed_seq=0)
        initial = stream.next_render()
        pending = scene(frame(2)); pending['canvases'][0]['commands'][4][5] = '#0000ff'
        stream.offer(pending, processed_seq=1)
        latest = scene(frame(3)); latest['canvases'][0]['commands'][7][5] = '#00ff00'
        stream.offer(latest, processed_seq=2)
        self.assertIsNone(stream.next_render())
        self.assertEqual(stream.retry(), initial)
        stream.acknowledge(render_rev=1, applied_rev=1, status='applied')
        changed = stream.next_render()
        self.assertEqual(changed['ops'][0]['base_frame_rev'], 1)
        self.assertTrue(same(apply(first, changed['ops']), latest))
        frozen = deepcopy(changed)
        stream.offer(scene(frame(4)), processed_seq=3)
        self.assertEqual(stream.retry(), frozen)
        changed['ops'][0]['frame']['commands'].clear()
        self.assertEqual(stream.retry(), frozen)
        stream.acknowledge(render_rev=2, applied_rev=1, status='discarded')
        self.assertIsNone(stream.next_render())
        stream.resync(last_applied_rev=1)
        self.assertEqual(stream.next_render()['mode'], 'snapshot')


if __name__ == '__main__':
    if '--fixtures' in sys.argv:
        print(json.dumps(fixtures()))
    else:
        unittest.main()
