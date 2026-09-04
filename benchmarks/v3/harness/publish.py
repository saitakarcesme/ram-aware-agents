#!/usr/bin/env python3
"""Create a compact, privacy-reviewed v3 evidence snapshot from local results."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
ANALYZE_PATH = ROOT / "benchmarks" / "v3" / "harness" / "analyze.py"
SPEC = importlib.util.spec_from_file_location("ram_benchmark_v3_analyze", ANALYZE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load {ANALYZE_PATH}")
ANALYZE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ANALYZE)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def current_hook_hash() -> str:
    paths = [ROOT / "hooks" / "codex-ram-guard" / name for name in ("hooks.json", "ram_guard.py")]
    return hashlib.sha256(b"".join(path.read_bytes() for path in paths)).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--date", required=True)
    parser.add_argument("--preflight-note", default="none")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cases = [ANALYZE.ENGINE.case_metrics(path.parent) for path in sorted(args.results.glob("*/case-summary.json"))]
    triples = ANALYZE.valid_triples(cases)
    valid = [row for row in triples if row["quality_valid"]]
    valid_rows = []
    for row in valid:
        for condition in ANALYZE.CONDITIONS:
            valid_rows.append({
                "workload": row["workload"],
                "repetition": row["repetition"],
                "condition": condition,
                "active_seconds": round(row[f"{condition}_active_seconds"], 3),
                "average_rss_gib": round(row[f"{condition}_tree_rss_average_gib"], 6),
                "p95_rss_gib": round(row[f"{condition}_tree_rss_p95_gib"], 6),
                "peak_rss_gib": round(row[f"{condition}_tree_rss_peak_gib"], 6),
                "free_memory_drop_points": round(row[f"{condition}_system_free_drop_points"], 3),
                "responsiveness_p95_ms": round(row[f"{condition}_responsiveness_probe_p95_ms"], 6),
                "process_peak": int(row[f"{condition}_process_count_peak"]),
                "browser_process_peak": int(row[f"{condition}_browser_process_count_peak"]),
            })
    diagnostic_rows = []
    for case in cases:
        if case.get("status") != "complete":
            continue
        metrics = case["metrics"]
        diagnostic_rows.append({
            "workload": case["workload"],
            "repetition": case["repetition"],
            "condition": case["condition"],
            "quality_passed": case["quality_passed"],
            "active_seconds": round(metrics["active_seconds"], 3),
            "p95_rss_gib": round(metrics["tree_rss_p95_gib"], 6),
            "peak_rss_gib": round(metrics["tree_rss_peak_gib"], 6),
            "process_peak": int(metrics["process_count_peak"]),
            "browser_process_peak": int(metrics["browser_process_count_peak"]),
        })
    write_csv(args.output / "quality-valid-results.csv", valid_rows)
    write_csv(args.output / "all-case-diagnostics.csv", diagnostic_rows)
    ANALYZE.chart_svg(triples, args.output)
    image_name = "agents-vs-hook.svg"
    if shutil.which("sips"):
        png_path = args.output / "agents-vs-hook.png"
        converted = subprocess.run(
            ["sips", "-s", "format", "png", str(args.output / image_name), "--out", str(png_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if converted.returncode == 0:
            image_name = png_path.name
    hook_cases = [case for case in cases if case.get("condition") == "hook" and case.get("hook_telemetry")]
    tested_hashes = sorted({case["condition_identity"]["sha256"] for case in hook_cases})
    current_hash = current_hook_hash()
    mismatch = bool(tested_hashes) and current_hash not in tested_hashes
    model = "gpt-5.6-terra / medium"
    codex_version = subprocess.check_output(["codex", "--version"], text=True).strip()
    lines = [
        f"# 8 GB M1 v3 evidence — {args.date}",
        "",
        "This is a compact, privacy-reviewed tuning snapshot comparing an unconstrained control, the project `AGENTS.md`, and the Codex RAM Guard hook. Raw agent event logs and generated source are intentionally excluded.",
        "",
        "## Environment",
        "",
        "| Field | Value |",
        "|---|---|",
        "| Machine | Apple M1 MacBook, 8 GB unified memory |",
        f"| Codex | `{codex_version}` |",
        f"| Model | `{model}` |",
        "| Sampling | Full Codex process tree plus macOS system metrics every second |",
        f"| Preflight note | {args.preflight_note} |",
        "",
        "## Quality-valid results",
        "",
        "| Workload | Condition | Active time | P95 RSS | Peak RSS | Process peak |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in valid_rows:
        name = "AGENTS.md" if row["condition"] == "profile" else row["condition"]
        lines.append(
            f"| {row['workload']} | {name} | {row['active_seconds']:.1f} s | "
            f"{row['p95_rss_gib']:.3f} GiB | {row['peak_rss_gib']:.3f} GiB | {row['process_peak']} |"
        )
    lines.extend([
        "",
        f"![Quality-valid AGENTS.md versus hook results]({image_name})",
        "",
        "Rust and Python each produced one quality-valid triple. In Rust, `AGENTS.md` reduced peak RSS by 79.5% and the hook by 76.1% versus control; the hook was 13.1% faster than `AGENTS.md`. In Python, `AGENTS.md` reduced P95 RSS by 13.2% and the hook by 12.3%; the hook reduced peak RSS by 12.3% and finished 8.8% faster than `AGENTS.md`.",
        "",
        "## Browser diagnostic",
        "",
        "Two browser-heavy triples were attempted, but neither was quality-valid across all three arms. In repetition 1, control failed one of 84 independent mobile E2E tests. In repetition 2, the hook artifact's Playwright web server missed its 30-second readiness timeout. These cases remain in `all-case-diagnostics.csv` and are excluded from the comparison chart.",
        "",
        "The browser diagnostics still show a resource signal: control peak RSS was 2.54–3.27 GiB with 22 browser processes, while quality-passing `AGENTS.md` cases peaked at 1.31–1.41 GiB with 7–10 browser processes. The hook cases peaked at 1.06–1.41 GiB with 2–7 browser processes, but one failed quality and therefore cannot be counted as a win.",
        "",
        "## Decision",
        "",
        "This snapshot does not meet the protocol minimum of three quality-valid triples per workload. It supports keeping `AGENTS.md` as the default broad planning mechanism and offering RAM Guard as optional runtime enforcement, not replacing the instruction file universally. The hook has a real shell enforcement boundary and strong peak control, but current Codex hooks cannot cancel a starting subagent and the browser result shows that lower resource use is not sufficient when correctness fails.",
        "",
        f"Tested hook hashes: `{', '.join(tested_hashes)}`.",
        f"Current hook hash: `{current_hash}`.",
    ])
    if mismatch:
        lines.extend([
            "",
            "The current hook differs from the measured tuning candidate: duplicate startup/resume context injection was removed after telemetry showed ten context events for five prompts, and rewritten tool inputs now preserve non-command fields. The worker/serialization policy is unchanged, but the hardened candidate requires fresh repetitions before final claims.",
        ])
    lines.extend([
        "",
        "## Reproduce",
        "",
        "See [`../../README.md`](../../README.md) for the three-arm protocol and commands. Local raw results remain ignored by Git.",
    ])
    (args.output / "README.md").write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
