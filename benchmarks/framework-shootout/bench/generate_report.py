#!/usr/bin/env python3
"""
Generate benchmark report from raw results.

Parses wrk and hey output files, aggregates across runs,
produces markdown tables, CSV summary, and comparison charts.

Usage:
    python bench/generate_report.py [results_dir]
"""

import csv
import json
import os
import re
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


RESULTS_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("results")
REPORT_DIR = Path("report")
REPORT_DIR.mkdir(exist_ok=True)

FRAMEWORKS = ["flask", "django", "fastapi", "aquilia", "sanic", "tornado"]
SCENARIOS = ["ping", "json", "db-read", "db-write", "upload", "stream", "websocket"]


# ── Parsers ──────────────────────────────────────────────────────────────────

def parse_wrk(filepath: Path) -> dict | None:
    """Parse wrk --latency output."""
    if not filepath.exists():
        return None
    text = filepath.read_text()

    result = {}

    # Requests/sec
    m = re.search(r"Requests/sec:\s+([\d.]+)", text)
    if m:
        result["req_s"] = float(m.group(1))

    # Latency distribution
    m = re.search(r"50%\s+([\d.]+)(us|ms|s)", text)
    if m:
        result["p50_ms"] = _to_ms(float(m.group(1)), m.group(2))

    m = re.search(r"75%\s+([\d.]+)(us|ms|s)", text)
    if m:
        result["p75_ms"] = _to_ms(float(m.group(1)), m.group(2))

    m = re.search(r"90%\s+([\d.]+)(us|ms|s)", text)
    if m:
        result["p90_ms"] = _to_ms(float(m.group(1)), m.group(2))

    m = re.search(r"99%\s+([\d.]+)(us|ms|s)", text)
    if m:
        result["p99_ms"] = _to_ms(float(m.group(1)), m.group(2))

    # Avg latency
    m = re.search(r"Latency\s+([\d.]+)(us|ms|s)", text)
    if m:
        result["avg_ms"] = _to_ms(float(m.group(1)), m.group(2))

    # Errors
    m = re.search(r"Non-2xx or 3xx responses:\s+(\d+)", text)
    result["errors"] = int(m.group(1)) if m else 0

    # Transfer
    m = re.search(r"Transfer/sec:\s+([\d.]+)(\w+)", text)
    if m:
        result["transfer_s"] = f"{m.group(1)}{m.group(2)}"

    return result if "req_s" in result else None


def parse_hey(filepath: Path) -> dict | None:
    """Parse hey output."""
    if not filepath.exists():
        return None
    text = filepath.read_text()

    result = {}

    # Requests/sec
    m = re.search(r"Requests/sec:\s+([\d.]+)", text)
    if m:
        result["req_s"] = float(m.group(1))

    # Latency percentiles from histogram or summary
    # hey format: "50% in X.XXXX secs"
    for pct, key in [("50", "p50_ms"), ("95", "p95_ms"), ("99", "p99_ms")]:
        m = re.search(rf"{pct}%\s+in\s+([\d.]+)\s+secs", text)
        if m:
            result[key] = float(m.group(1)) * 1000

    # Average
    m = re.search(r"Average:\s+([\d.]+)\s+secs", text)
    if m:
        result["avg_ms"] = float(m.group(1)) * 1000

    # Status code distribution
    m = re.search(r"\[200\]\s+(\d+) responses", text)
    ok_count = int(m.group(1)) if m else 0
    m = re.search(r"\[201\]\s+(\d+) responses", text)
    ok_count += int(m.group(1)) if m else 0

    # Error count
    m = re.search(r"Status code distribution.*", text, re.DOTALL)
    errors_section = m.group(0) if m else ""
    total_errs = 0
    for em in re.finditer(r"\[(\d+)\]\s+(\d+) responses", errors_section):
        code = int(em.group(1))
        if code >= 400:
            total_errs += int(em.group(2))
    result["errors"] = total_errs

    return result if "req_s" in result else None


def parse_ws(filepath: Path) -> dict | None:
    """Parse WebSocket benchmark JSON output."""
    if not filepath.exists():
        return None
    text = filepath.read_text()

    # Try to find JSON block
    try:
        # Find the last JSON object in the output
        json_start = text.rfind("{")
        json_end = text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            data = json.loads(text[json_start:json_end])
            return {
                "req_s": data.get("throughput_msg_s", 0),
                "p50_ms": data.get("latency_p50_ms", 0),
                "p95_ms": data.get("latency_p95_ms", 0),
                "p99_ms": data.get("latency_p99_ms", 0),
                "avg_ms": data.get("latency_mean_ms", 0),
                "errors": data.get("total_errors", 0),
            }
    except json.JSONDecodeError:
        pass
    return None


def _to_ms(value: float, unit: str) -> float:
    if unit == "us":
        return value / 1000
    elif unit == "s":
        return value * 1000
    return value  # already ms


# ── Aggregation ──────────────────────────────────────────────────────────────

def collect_all_results() -> list[dict]:
    """Collect and aggregate results across all runs."""
    rows = []

    for fw in FRAMEWORKS:
        for scenario in SCENARIOS:
            run_results = []
            for run_id in range(1, 10):  # Try up to 10 runs
                run_dir = RESULTS_DIR / fw / scenario / f"run{run_id}"
                if not run_dir.exists():
                    continue

                result = None
                # Try wrk first, then hey, then ws
                for parser, filename in [
                    (parse_wrk, "wrk_steady.txt"),
                    (parse_hey, "hey_steady.txt"),
                    (parse_ws, "ws_steady.txt"),
                ]:
                    path = run_dir / filename
                    if path.exists():
                        result = parser(path)
                        break

                if result:
                    result["run_id"] = run_id
                    run_results.append(result)

            if not run_results:
                continue

            # Aggregate: take median of each metric
            agg = {
                "framework": fw,
                "scenario": scenario,
                "runs": len(run_results),
            }

            for key in ["req_s", "p50_ms", "p95_ms", "p99_ms", "avg_ms", "errors"]:
                values = [r[key] for r in run_results if key in r]
                if values:
                    agg[key] = statistics.median(values)
                    if len(values) > 1:
                        agg[f"{key}_stdev"] = statistics.stdev(values)
                    else:
                        agg[f"{key}_stdev"] = 0
                else:
                    agg[key] = 0
                    agg[f"{key}_stdev"] = 0

            # Grab CPU/mem from stats files (last run)
            last_run = RESULTS_DIR / fw / scenario / f"run{len(run_results)}"
            stats_file = last_run / "stats_after.txt"
            if stats_file.exists():
                stats_text = stats_file.read_text()
                m = re.search(r"([\d.]+)%", stats_text)
                if m:
                    agg["cpu_pct"] = float(m.group(1))
                m = re.search(r"([\d.]+)(MiB|GiB)", stats_text)
                if m:
                    mem = float(m.group(1))
                    if m.group(2) == "GiB":
                        mem *= 1024
                    agg["mem_mib"] = mem
            else:
                agg["cpu_pct"] = 0
                agg["mem_mib"] = 0

            rows.append(agg)

    return rows


# ── Report Generation ────────────────────────────────────────────────────────

def generate_csv(rows: list[dict]):
    """Write summary CSV."""
    csv_path = REPORT_DIR / "summary.csv"
    if not rows:
        csv_path.write_text("No results found.\n")
        return

    fields = [
        "framework", "scenario", "runs", "req_s", "req_s_stdev",
        "p50_ms", "p95_ms", "p99_ms", "avg_ms", "errors",
        "cpu_pct", "mem_mib",
    ]

    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in sorted(rows, key=lambda r: (r["scenario"], -r.get("req_s", 0))):
            writer.writerow(row)

    print(f"  CSV → {csv_path}")


def generate_markdown(rows: list[dict]):
    """Generate markdown report with tables."""
    report_path = REPORT_DIR / "REPORT.md"

    lines = [
        "# Framework Shootout — Benchmark Report",
        "",
        f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}  ",
        f"**Frameworks:** {', '.join(FRAMEWORKS)}  ",
        f"**Scenarios:** {', '.join(SCENARIOS)}  ",
        f"**Python:** 3.11 (Docker, 2 CPU / 512MB per container)  ",
        "",
        "---",
        "",
    ]

    if not rows:
        lines.append("*No results found. Run `./bench/run_all.sh` first.*\n")
        report_path.write_text("\n".join(lines))
        print(f"  Report → {report_path} (empty)")
        return

    # ── Per-scenario tables ──────────────────────────────────────────────
    for scenario in SCENARIOS:
        scenario_rows = [r for r in rows if r["scenario"] == scenario]
        if not scenario_rows:
            continue

        scenario_rows.sort(key=lambda r: -r.get("req_s", 0))

        lines.append(f"## {scenario.upper()}")
        lines.append("")
        lines.append(
            "| # | Framework | Req/s | p50 (ms) | p95 (ms) | p99 (ms) | "
            "Errors | CPU % | Mem (MiB) | Runs |"
        )
        lines.append(
            "|---|-----------|------:|--------:|--------:|--------:|------:|------:|--------:|-----:|"
        )

        for i, r in enumerate(scenario_rows, 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, "")
            lines.append(
                f"| {medal}{i} | **{r['framework']}** "
                f"| {r.get('req_s', 0):,.0f} "
                f"| {r.get('p50_ms', 0):.2f} "
                f"| {r.get('p95_ms', 0):.2f} "
                f"| {r.get('p99_ms', 0):.2f} "
                f"| {r.get('errors', 0):.0f} "
                f"| {r.get('cpu_pct', 0):.1f} "
                f"| {r.get('mem_mib', 0):.0f} "
                f"| {r.get('runs', 0)} |"
            )

        lines.append("")

    # ── Executive summary ────────────────────────────────────────────────
    lines.append("---")
    lines.append("")
    lines.append("## Executive Summary")
    lines.append("")

    # Winner per scenario
    lines.append("### Winner per Scenario")
    lines.append("")
    lines.append("| Scenario | Winner | Req/s | Runner-up | Req/s |")
    lines.append("|----------|--------|------:|-----------|------:|")

    wins = defaultdict(int)
    for scenario in SCENARIOS:
        scenario_rows = sorted(
            [r for r in rows if r["scenario"] == scenario],
            key=lambda r: -r.get("req_s", 0),
        )
        if len(scenario_rows) >= 2:
            w = scenario_rows[0]
            r = scenario_rows[1]
            wins[w["framework"]] += 1
            lines.append(
                f"| {scenario} | **{w['framework']}** | {w['req_s']:,.0f} "
                f"| {r['framework']} | {r['req_s']:,.0f} |"
            )
        elif len(scenario_rows) == 1:
            w = scenario_rows[0]
            wins[w["framework"]] += 1
            lines.append(
                f"| {scenario} | **{w['framework']}** | {w['req_s']:,.0f} "
                f"| — | — |"
            )

    lines.append("")

    # Overall winner
    if wins:
        overall = max(wins, key=wins.get)
        lines.append(f"### Overall Winner: **{overall}** ({wins[overall]}/{len(SCENARIOS)} scenarios)")
    lines.append("")

    # ── Analysis notes ───────────────────────────────────────────────────
    lines.append("### Analysis Notes")
    lines.append("")
    lines.append("- **Ping/JSON** (tiny payload): Measures pure request-routing overhead.")
    lines.append("  Async frameworks (FastAPI, Aquilia, Sanic) typically dominate due to")
    lines.append("  event-loop efficiency vs. gunicorn process model.")
    lines.append("")
    lines.append("- **DB-read/write**: Async frameworks using `asyncpg` have an advantage")
    lines.append("  over sync frameworks using `psycopg2` with thread pools.")
    lines.append("")
    lines.append("- **Upload**: Tests I/O handling. Memory consumption matters here.")
    lines.append("")
    lines.append("- **Stream**: Tests chunked transfer. Async generators are natural fit.")
    lines.append("")
    lines.append("- **WebSocket**: Only async frameworks support this natively.")
    lines.append("  Flask and Django are excluded from this scenario.")
    lines.append("")

    # ── Methodology ──────────────────────────────────────────────────────
    lines.append("---")
    lines.append("")
    lines.append("## Methodology")
    lines.append("")
    lines.append("- **Isolation:** Each framework runs in its own Docker container (2 CPU, 512MB).")
    lines.append("- **DB:** PostgreSQL 16 with shared schema and 1000 seeded rows.")
    lines.append("- **Workers:** Sync (Flask/Django): gunicorn 4w×2t. Async: uvicorn/sanic 4 workers.")
    lines.append("- **Load:** `wrk` for GET, `hey` for POST. 50 concurrent, 3 min steady-state.")
    lines.append("- **Warmup:** 30s before each measurement.")
    lines.append("- **Repetitions:** 3 runs per scenario, median reported.")
    lines.append("- **Correctness:** Each endpoint validated before load test.")
    lines.append("")

    report_path.write_text("\n".join(lines))
    print(f"  Report → {report_path}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("Collecting results...")
    rows = collect_all_results()
    print(f"  Found {len(rows)} aggregated results.")

    generate_csv(rows)
    generate_markdown(rows)

    # Also dump JSON for programmatic access
    json_path = REPORT_DIR / "summary.json"
    with open(json_path, "w") as f:
        json.dump(rows, f, indent=2, default=str)
    print(f"  JSON → {json_path}")


if __name__ == "__main__":
    main()
