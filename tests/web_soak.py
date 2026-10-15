"""Optional Linux lifecycle/load check using real forked workers and WebSockets.

Run env/bin/python tests/web_soak.py --rounds 100 --clients 4.
No additional dependencies or external server are required.
"""
import argparse
import asyncio
import gc
import json
from pathlib import Path
import statistics
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import web_server


def rss(pid='self'):
    for line in Path('/proc/%s/status' % pid).read_text().splitlines():
        if line.startswith('VmRSS:'):
            return int(line.split()[1]) * 1024
    return 0


async def run(rounds, clients):
    probe = web_server.ServerTests()
    await probe.asyncSetUp()
    probe.gateway.sessions.session_ttl = .08
    metrics = {'rounds': rounds, 'clients_per_round': clients, 'resumed': 0, 'expired': 0,
               'snapshot_bytes': 0, 'patch_bytes': 0}
    latencies, memory, descriptors, worker_memory = [], [], [], []
    started = time.monotonic()

    async def cycle(index):
        ws = await probe.connect()
        ready, tree = await probe.read(ws), await probe.read(ws)
        key = ready['body']['resume_id']
        pid = probe.gateway.workers[key].process.pid
        worker_memory.append(rss(pid))
        metrics['snapshot_bytes'] += probe.last_wire_bytes[ws]
        before = time.monotonic()
        await probe.click_increment(ws, ready, tree)
        result, patch = await probe.read(ws), await probe.read(ws)
        probe.assertEqual(result['body']['status'], 'processed')
        probe.assertIn('count=1', str(patch))
        metrics['patch_bytes'] += probe.last_wire_bytes[ws]
        latencies.append(time.monotonic() - before)
        await probe.disconnect(ws)
        await probe.wait_until(lambda: key not in probe.gateway.workers or
                               probe.gateway.workers[key].websocket is None)
        # Immediate resume, expiry boundary and definitely-expired reconnects.
        await asyncio.sleep((0, .08, .12)[index % 3])
        again = await probe.connect(resume_id=key)
        restored, state = await probe.read(again), await probe.read(again)
        resumed = restored['body']['resumed']
        metrics['resumed' if resumed else 'expired'] += 1
        probe.assertIn('count=' + ('1' if resumed else '0'), str(state))
        current = probe.gateway.workers[restored['body']['resume_id']].process.pid
        probe.assertEqual(current == pid, resumed)
        await probe.disconnect(again)
        return pid, current

    try:
        for iteration in range(rounds):
            pids = await asyncio.gather(*(cycle(iteration + index) for index in range(clients)))
            await probe.wait_until(lambda: not probe.gateway.workers and not probe.gateway.reapers)
            for pair in pids:
                for pid in pair:
                    probe.assertFalse(Path('/proc/%s' % pid).exists())
            probe.sockets.clear()
            probe.assertEqual(len(probe.gateway.sessions), 0)
            gc.collect()
            descriptors.append(len(list(Path('/proc/self/fd').iterdir())))
            memory.append(rss())
            probe.assertLessEqual(descriptors[-1], descriptors[0] + 1)
        # Also close the gateway with a live connection and its unacknowledged render.
        active = await probe.connect()
        ready = await probe.read(active)
        await probe.read(active)
        pid = probe.gateway.workers[ready['body']['resume_id']].process.pid
        await asyncio.wait_for(probe.runner.cleanup(), 5)
        probe.assertFalse(Path('/proc/%s' % pid).exists())
    finally:
        await probe.asyncTearDown()
    ordered = sorted(latencies)
    metrics.update(elapsed_seconds=round(time.monotonic() - started, 3),
        fd_min=min(descriptors), fd_max=max(descriptors),
        gateway_rss_first=memory[0], gateway_rss_last=memory[-1], gateway_rss_max=max(memory),
        worker_rss_median=int(statistics.median(worker_memory)),
        local_action_p50_ms=round(statistics.median(ordered) * 1000, 3),
        local_action_p95_ms=round(ordered[min(len(ordered)-1, int(len(ordered)*.95))] * 1000, 3))
    print(json.dumps(metrics, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rounds', type=int, default=100)
    parser.add_argument('--clients', type=int, default=4)
    args = parser.parse_args()
    if args.rounds < 1 or not 1 <= args.clients <= 16:
        parser.error('rounds must be positive and clients must be between 1 and 16')
    asyncio.run(run(args.rounds, args.clients))
