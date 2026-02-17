#!/usr/bin/env python3
"""
WebSocket benchmark client.

Usage:
    python ws_bench.py <host> <port> <num_connections> <duration_seconds>
"""

import asyncio
import json
import sys
import time
import statistics

try:
    import websockets
except ImportError:
    print("pip install websockets")
    sys.exit(1)


async def ws_client(host, port, client_id, duration, results):
    """Single WS client that sends/receives echo messages."""
    uri = f"ws://{host}:{port}/ws-echo"
    sent = 0
    received = 0
    latencies = []
    errors = 0

    try:
        async with websockets.connect(uri) as ws:
            deadline = time.monotonic() + duration
            while time.monotonic() < deadline:
                msg = f"ping-{client_id}-{sent}"
                t0 = time.perf_counter_ns()
                await ws.send(msg)
                reply = await asyncio.wait_for(ws.recv(), timeout=5.0)
                lat = (time.perf_counter_ns() - t0) / 1_000_000  # ms
                latencies.append(lat)
                sent += 1
                received += 1
                if reply != msg:
                    errors += 1
    except Exception as e:
        errors += 1

    results.append({
        "client_id": client_id,
        "sent": sent,
        "received": received,
        "errors": errors,
        "latencies": latencies,
    })


async def main():
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    num_conns = int(sys.argv[3]) if len(sys.argv) > 3 else 50
    duration = int(sys.argv[4]) if len(sys.argv) > 4 else 60

    print(f"WebSocket Bench: {num_conns} connections to ws://{host}:{port}/ws-echo for {duration}s")

    results = []
    tasks = [
        ws_client(host, port, i, duration, results)
        for i in range(num_conns)
    ]
    await asyncio.gather(*tasks, return_exceptions=True)

    # Aggregate
    total_sent = sum(r["sent"] for r in results)
    total_recv = sum(r["received"] for r in results)
    total_errors = sum(r["errors"] for r in results)
    all_latencies = []
    for r in results:
        all_latencies.extend(r["latencies"])

    if all_latencies:
        all_latencies.sort()
        p50 = all_latencies[len(all_latencies) // 2]
        p95 = all_latencies[int(len(all_latencies) * 0.95)]
        p99 = all_latencies[int(len(all_latencies) * 0.99)]
        mean_lat = statistics.mean(all_latencies)
    else:
        p50 = p95 = p99 = mean_lat = 0

    throughput = total_sent / duration if duration > 0 else 0

    print(f"\nResults:")
    print(f"  Connections: {num_conns}")
    print(f"  Duration:    {duration}s")
    print(f"  Messages:    {total_sent} sent, {total_recv} received, {total_errors} errors")
    print(f"  Throughput:  {throughput:,.0f} msg/s")
    print(f"  Latency:     p50={p50:.2f}ms  p95={p95:.2f}ms  p99={p99:.2f}ms  mean={mean_lat:.2f}ms")

    # Write JSON summary
    summary = {
        "connections": num_conns,
        "duration_s": duration,
        "total_sent": total_sent,
        "total_received": total_recv,
        "total_errors": total_errors,
        "throughput_msg_s": throughput,
        "latency_p50_ms": p50,
        "latency_p95_ms": p95,
        "latency_p99_ms": p99,
        "latency_mean_ms": mean_lat,
    }
    print(f"\n{json.dumps(summary, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())
