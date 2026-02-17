#!/usr/bin/env python3
"""
collect_results.py — Parse raw benchmark outputs and produce tables
===================================================================
Parses wrk, hey, upload, and WebSocket raw outputs.
Produces CSV and Markdown summary tables.

Usage:
    python benchmark/bench_scripts/collect_results.py
    python benchmark/bench_scripts/collect_results.py --results-dir benchmark/results
    python benchmark/bench_scripts/collect_results.py --output-format markdown
    python benchmark/bench_scripts/collect_results.py --output-format csv
"""
import argparse
import csv
import io
import os
import re
import statistics
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class RunResult:
    """Parsed result from a single benchmark run."""
    scenario: str = ""
    framework: str = ""
    run_num: int = 0
    requests_per_sec: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    errors: int = 0
    total_requests: int = 0
    transfer_per_sec: str = ""
    duration_s: float = 0.0


@dataclass
class AggResult:
    """Aggregated (median of N runs) result."""
    scenario: str = ""
    framework: str = ""
    req_s: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    errors: int = 0
    cpu_pct: str = "—"
    mem_mib: str = "—"
    runs: int = 0


def parse_wrk_output(text: str) -> RunResult:
    """Parse wrk --latency output."""
    r = RunResult()

    # Requests/sec
    m = re.search(r'Requests/sec:\s+([\d.]+)', text)
    if m:
        r.requests_per_sec = float(m.group(1))

    # Latency percentiles (from --latency output)
    # Format: 50%    1.23ms
    percentiles = re.findall(r'(\d+)%\s+([\d.]+)(us|ms|s)', text)
    for pct, val, unit in percentiles:
        ms = float(val)
        if unit == 'us':
            ms /= 1000
        elif unit == 's':
            ms *= 1000

        pct_int = int(pct)
        if pct_int == 50:
            r.p50_ms = ms
        elif pct_int == 90:
            pass  # skip
        elif pct_int == 99:
            r.p99_ms = ms

    # If p95 not directly available, estimate from p90 and p99
    # wrk reports 50%, 75%, 90%, 99% — let's capture 90% as p95 approximation
    p90_match = re.findall(r'90%\s+([\d.]+)(us|ms|s)', text)
    if p90_match:
        val, unit = p90_match[0]
        ms = float(val)
        if unit == 'us':
            ms /= 1000
        elif unit == 's':
            ms *= 1000
        r.p95_ms = ms  # Use 90th pct as p95 proxy (wrk doesn't give exact p95)

    # Total requests
    m = re.search(r'(\d+)\s+requests\s+in', text)
    if m:
        r.total_requests = int(m.group(1))

    # Socket errors
    errors = 0
    m = re.search(r'Socket errors:\s+connect\s+(\d+),\s+read\s+(\d+),\s+write\s+(\d+),\s+timeout\s+(\d+)', text)
    if m:
        errors = sum(int(m.group(i)) for i in range(1, 5))
    # Non-2xx responses
    m = re.search(r'Non-2xx or 3xx responses:\s+(\d+)', text)
    if m:
        errors += int(m.group(1))
    r.errors = errors

    # Transfer/sec
    m = re.search(r'Transfer/sec:\s+(.+)', text)
    if m:
        r.transfer_per_sec = m.group(1).strip()

    return r


def parse_hey_output(text: str) -> RunResult:
    """Parse hey output."""
    r = RunResult()

    # Requests/sec
    m = re.search(r'Requests/sec:\s+([\d.]+)', text)
    if m:
        r.requests_per_sec = float(m.group(1))

    # Latency distribution
    # hey outputs:  10% in X.XXXX secs
    pcts = re.findall(r'(\d+)%\s+in\s+([\d.]+)\s+secs', text)
    for pct, val in pcts:
        ms = float(val) * 1000
        pct_int = int(pct)
        if pct_int == 50:
            r.p50_ms = ms
        elif pct_int == 95:
            r.p95_ms = ms
        elif pct_int == 99:
            r.p99_ms = ms

    # Total requests
    m = re.search(r'Total:\s+(\d+)', text)
    if m:
        r.total_requests = int(m.group(1))
    else:
        m = re.search(r'\[(\d+)\]\s+responses', text)
        if m:
            r.total_requests = int(m.group(1))

    # Status codes
    status_200 = 0
    m = re.search(r'\[200\]\s+(\d+)\s+responses', text)
    if m:
        status_200 = int(m.group(1))
    m = re.search(r'\[201\]\s+(\d+)\s+responses', text)
    if m:
        status_200 += int(m.group(1))

    # Error count
    m = re.search(r'Error distribution:', text)
    if m:
        error_lines = re.findall(r'\[(\d+)\]\s+(\d+)', text)
        for code, count in error_lines:
            if int(code) >= 400:
                r.errors += int(count)

    return r


def parse_upload_output(text: str) -> RunResult:
    """Parse custom upload benchmark output."""
    r = RunResult()

    m = re.search(r'Requests/sec:\s+([\d.]+)', text)
    if m:
        r.requests_per_sec = float(m.group(1))

    m = re.search(r'Total requests:\s+(\d+)', text)
    if m:
        r.total_requests = int(m.group(1))

    m = re.search(r'Errors:\s+(\d+)', text)
    if m:
        r.errors = int(m.group(1))

    m = re.search(r'Elapsed:\s+([\d.]+)s', text)
    if m:
        r.duration_s = float(m.group(1))

    return r


def parse_ws_output(text: str) -> RunResult:
    """Parse WebSocket benchmark output."""
    r = RunResult()

    m = re.search(r'Msg/sec:\s+([\d.]+)', text)
    if m:
        r.requests_per_sec = float(m.group(1))

    m = re.search(r'Latency p50:\s+([\d.]+)', text)
    if m:
        r.p50_ms = float(m.group(1))

    m = re.search(r'Latency p95:\s+([\d.]+)', text)
    if m:
        r.p95_ms = float(m.group(1))

    m = re.search(r'Latency p99:\s+([\d.]+)', text)
    if m:
        r.p99_ms = float(m.group(1))

    m = re.search(r'Errors:\s+(\d+)', text)
    if m:
        r.errors = int(m.group(1))

    m = re.search(r'Successful:\s+(\d+)/(\d+)', text)
    if m:
        r.total_requests = int(m.group(2))

    return r


def parse_docker_stats(text: str) -> dict:
    """Parse docker stats --no-stream output."""
    result = {"cpu": "—", "mem": "—"}
    lines = text.strip().split("\n")
    if len(lines) >= 2:
        parts = lines[1].split()
        if len(parts) >= 4:
            result["cpu"] = parts[2]  # CPU %
            result["mem"] = parts[3]  # MEM USAGE
    return result


def aggregate_runs(runs: list[RunResult]) -> AggResult:
    """Take median of N runs."""
    if not runs:
        return AggResult()

    agg = AggResult(
        scenario=runs[0].scenario,
        framework=runs[0].framework,
        runs=len(runs),
    )

    rps_list = [r.requests_per_sec for r in runs if r.requests_per_sec > 0]
    p50_list = [r.p50_ms for r in runs if r.p50_ms > 0]
    p95_list = [r.p95_ms for r in runs if r.p95_ms > 0]
    p99_list = [r.p99_ms for r in runs if r.p99_ms > 0]

    agg.req_s = statistics.median(rps_list) if rps_list else 0
    agg.p50_ms = statistics.median(p50_list) if p50_list else 0
    agg.p95_ms = statistics.median(p95_list) if p95_list else 0
    agg.p99_ms = statistics.median(p99_list) if p99_list else 0
    agg.errors = sum(r.errors for r in runs)

    return agg


def scan_results(results_dir: str) -> list[AggResult]:
    """Scan results directory and aggregate."""
    results_path = Path(results_dir)
    all_agg = []

    frameworks = ["aquilia", "sanic", "fastapi"]
    scenarios = [
        "ping", "json", "json-large", "html", "path", "query",
        "db-read", "db-write", "upload", "stream", "sse",
        "websocket", "static", "background",
    ]

    # Determine parser by scenario
    post_scenarios = {"db-write"}
    upload_scenarios = {"upload"}
    ws_scenarios = {"websocket"}

    for fw in frameworks:
        fw_path = results_path / fw

        # Load docker stats if available
        docker_stats = {"cpu": "—", "mem": "—"}
        stats_file = fw_path / "docker_stats" / "snapshot.txt"
        if stats_file.exists():
            docker_stats = parse_docker_stats(stats_file.read_text())

        for scenario in scenarios:
            scenario_path = fw_path / scenario
            if not scenario_path.exists():
                continue

            runs = []
            for run_file in sorted(scenario_path.glob("run*.txt")):
                text = run_file.read_text()
                run_num = int(re.search(r'run(\d+)', run_file.name).group(1))

                if scenario in ws_scenarios:
                    r = parse_ws_output(text)
                elif scenario in upload_scenarios:
                    r = parse_upload_output(text)
                elif scenario in post_scenarios:
                    r = parse_hey_output(text)
                else:
                    r = parse_wrk_output(text)

                r.scenario = scenario
                r.framework = fw
                r.run_num = run_num
                runs.append(r)

            if runs:
                agg = aggregate_runs(runs)
                agg.cpu_pct = docker_stats["cpu"]
                agg.mem_mib = docker_stats["mem"]
                all_agg.append(agg)

    return all_agg


def format_markdown(results: list[AggResult]) -> str:
    """Produce Markdown table matching REPORT layout."""
    out = io.StringIO()

    out.write("# Framework Shootout — Benchmark Results\n\n")
    out.write(f"**Date:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    out.write(f"**Environment:** Docker (--cpus=2 --memory=512m), Python 3.11-slim, PostgreSQL 16\n")
    out.write(f"**Parameters:** {50} connections, 3 min steady-state, 30s warmup, 3 runs (median)\n")
    out.write(f"**Workers:** 4 per framework\n\n")

    # Group by scenario
    scenarios = {}
    for r in results:
        scenarios.setdefault(r.scenario, []).append(r)

    out.write("## Per-Scenario Results\n\n")
    out.write("| Scenario | Framework | Req/s | p50 (ms) | p95 (ms) | p99 (ms) | Errors | CPU% | Mem | Runs |\n")
    out.write("|----------|-----------|------:|--------:|--------:|--------:|-------:|------|-----|-----:|\n")

    for scenario_name in [
        "ping", "json", "json-large", "html", "path", "query",
        "db-read", "db-write", "upload", "stream", "sse",
        "websocket", "static", "background",
    ]:
        if scenario_name not in scenarios:
            continue

        # Sort by req/s descending (winner first)
        group = sorted(scenarios[scenario_name], key=lambda x: x.req_s, reverse=True)
        for i, r in enumerate(group):
            winner = " 🏆" if i == 0 and len(group) > 1 else ""
            out.write(
                f"| {r.scenario} | **{r.framework}**{winner} | "
                f"{r.req_s:,.0f} | {r.p50_ms:.2f} | {r.p95_ms:.2f} | {r.p99_ms:.2f} | "
                f"{r.errors} | {r.cpu_pct} | {r.mem_mib} | {r.runs} |\n"
            )
        # Separator between scenarios
        out.write("|---|---|---|---|---|---|---|---|---|---|\n")

    # Summary table
    out.write("\n## Executive Summary — Winners by Scenario\n\n")
    out.write("| Scenario | 🏆 Winner | Req/s | Runner-up | Req/s | Margin |\n")
    out.write("|----------|----------|------:|-----------|------:|-------:|\n")

    wins = {"aquilia": 0, "sanic": 0, "fastapi": 0}
    for scenario_name, group in scenarios.items():
        group_sorted = sorted(group, key=lambda x: x.req_s, reverse=True)
        if len(group_sorted) >= 2:
            w = group_sorted[0]
            ru = group_sorted[1]
            margin = ((w.req_s - ru.req_s) / ru.req_s * 100) if ru.req_s > 0 else 0
            wins[w.framework] = wins.get(w.framework, 0) + 1
            out.write(
                f"| {scenario_name} | **{w.framework}** | {w.req_s:,.0f} | "
                f"{ru.framework} | {ru.req_s:,.0f} | +{margin:.1f}% |\n"
            )
        elif group_sorted:
            w = group_sorted[0]
            wins[w.framework] = wins.get(w.framework, 0) + 1
            out.write(
                f"| {scenario_name} | **{w.framework}** | {w.req_s:,.0f} | — | — | — |\n"
            )

    out.write(f"\n### Overall Score\n\n")
    for fw, count in sorted(wins.items(), key=lambda x: x[1], reverse=True):
        out.write(f"- **{fw}**: {count} scenario wins\n")

    overall_winner = max(wins, key=wins.get) if wins else "N/A"
    out.write(f"\n**Overall Winner: {overall_winner}** 🏆\n")

    return out.getvalue()


def format_csv(results: list[AggResult]) -> str:
    """Produce CSV output."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow([
        "scenario", "framework", "req_s", "p50_ms", "p95_ms", "p99_ms",
        "errors", "cpu_pct", "mem_mib", "runs"
    ])
    for r in results:
        writer.writerow([
            r.scenario, r.framework, f"{r.req_s:.0f}",
            f"{r.p50_ms:.2f}", f"{r.p95_ms:.2f}", f"{r.p99_ms:.2f}",
            r.errors, r.cpu_pct, r.mem_mib, r.runs,
        ])
    return out.getvalue()


def main():
    parser = argparse.ArgumentParser(description="Collect and aggregate benchmark results")
    parser.add_argument("--results-dir", default="benchmark/results")
    parser.add_argument("--output-format", choices=["markdown", "csv", "both"], default="both")
    parser.add_argument("--output-dir", default="benchmark")
    args = parser.parse_args()

    if not Path(args.results_dir).exists():
        print(f"Results directory not found: {args.results_dir}")
        print("Run bench_all.sh first to generate results.")
        sys.exit(1)

    results = scan_results(args.results_dir)

    if not results:
        print("No results found. Run bench_all.sh first.")
        sys.exit(1)

    print(f"Parsed {len(results)} aggregated results")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.output_format in ("markdown", "both"):
        md = format_markdown(results)
        md_path = output_dir / "final_report.md"
        md_path.write_text(md)
        print(f"Markdown report: {md_path}")

    if args.output_format in ("csv", "both"):
        csv_text = format_csv(results)
        csv_path = output_dir / "results.csv"
        csv_path.write_text(csv_text)
        print(f"CSV report: {csv_path}")


if __name__ == "__main__":
    main()
