#!/usr/bin/env python3
"""
WebSocket Benchmark Script
===========================
Opens N concurrent connections to a WebSocket endpoint,
sends M messages per connection, measures latency and errors.

Supports two protocols:
  --protocol envelope   (Aquilia: wraps in {"event":"echo","data":{...}})
  --protocol raw        (Sanic/FastAPI: sends raw JSON, expects raw echo)

Usage:
    python ws_bench.py --host 127.0.0.1 --port 8000 --path /ws \
                       --connections 50 --messages 100 --protocol envelope
"""
import argparse
import asyncio
import json
import statistics
import time
import sys

try:
    import websockets
except ImportError:
    print("ERROR: pip install websockets")
    sys.exit(1)


async def ws_client(
    uri: str,
    messages: int,
    results: list,
    errors: list,
    cid: int,
    protocol: str,
):
    """Single WebSocket client that sends `messages` payloads and measures RTT."""
    latencies = []
    try:
        async with websockets.connect(uri, open_timeout=10) as ws:
            # Read the initial "connected" message
            _ = await asyncio.wait_for(ws.recv(), timeout=5)

            for i in range(messages):
                inner = {"cid": cid, "seq": i, "ts": time.monotonic()}

                if protocol == "envelope":
                    # Aquilia envelope format
                    payload = json.dumps({
                        "event": "echo",
                        "data": inner,
                    })
                else:
                    # Raw JSON (Sanic / FastAPI)
                    payload = json.dumps(inner)

                t0 = time.monotonic()
                await ws.send(payload)
                resp = await asyncio.wait_for(ws.recv(), timeout=5)
                t1 = time.monotonic()
                latencies.append((t1 - t0) * 1000)  # ms

            results.extend(latencies)
    except Exception as e:
        errors.append(f"Client {cid}: {type(e).__name__}: {e}")


async def run_benchmark(
    host: str,
    port: int,
    path: str,
    connections: int,
    messages: int,
    protocol: str,
):
    uri = f"ws://{host}:{port}{path}"
    results = []
    errors_list = []

    print(f"=== WebSocket Benchmark ===")
    print(f"URI:         {uri}")
    print(f"Protocol:    {protocol}")
    print(f"Connections: {connections}")
    print(f"Messages:    {messages} per connection")
    print(f"Total msgs:  {connections * messages}")
    print()

    t_start = time.monotonic()

    tasks = [
        ws_client(uri, messages, results, errors_list, cid, protocol)
        for cid in range(connections)
    ]
    await asyncio.gather(*tasks)

    t_end = time.monotonic()
    elapsed = t_end - t_start
    total_messages = connections * messages
    successful = len(results)
    msg_per_sec = successful / elapsed if elapsed > 0 else 0

    print(f"Duration:     {elapsed:.2f}s")
    print(f"Successful:   {successful}/{total_messages} messages")
    print(f"Errors:       {len(errors_list)}")
    print(f"Msg/sec:      {msg_per_sec:.2f}")

    if results:
        results.sort()
        print(f"Latency p50:  {statistics.median(results):.3f} ms")
        p95_idx = min(int(len(results) * 0.95), len(results) - 1)
        p99_idx = min(int(len(results) * 0.99), len(results) - 1)
        print(f"Latency p95:  {results[p95_idx]:.3f} ms")
        print(f"Latency p99:  {results[p99_idx]:.3f} ms")
        print(f"Latency min:  {results[0]:.3f} ms")
        print(f"Latency max:  {results[-1]:.3f} ms")
        print(f"Latency avg:  {statistics.mean(results):.3f} ms")
    else:
        print("No successful messages!")

    if errors_list:
        print(f"\nError samples (first 10):")
        for e in errors_list[:10]:
            print(f"  {e}")


def main():
    parser = argparse.ArgumentParser(description="WebSocket benchmark")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--path", default="/ws")
    parser.add_argument("--connections", type=int, default=50)
    parser.add_argument("--messages", type=int, default=100)
    parser.add_argument(
        "--protocol",
        choices=["envelope", "raw"],
        default="raw",
        help="Message protocol: 'envelope' for Aquilia, 'raw' for Sanic/FastAPI",
    )
    args = parser.parse_args()

    asyncio.run(run_benchmark(
        args.host, args.port, args.path,
        args.connections, args.messages, args.protocol,
    ))


if __name__ == "__main__":
    main()
