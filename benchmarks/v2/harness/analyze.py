#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

GIB = 1024**3


def percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    fraction = position - low
    return ordered[low] * (1 - fraction) + ordered[high] * fraction


def sample_rows(case_dir: Path) -> list[dict[str, float]]:
    rows: list[dict[str, float]] = []
    for path in sorted(case_dir.glob("prompt-*-samples.csv")):
        with path.open() as handle:
            rows.extend({key: float(value) for key, value in row.items()} for row in csv.DictReader(handle))
    return rows


def case_metrics(case_dir: Path) -> dict[str, Any]:
    summary = json.loads((case_dir / "case-summary.json").read_text())
    if summary.get("status") != "complete":
        return summary
    samples = sample_rows(case_dir)
    rss = [row["tree_rss_bytes"] for row in samples]
    system = [row["system_used_bytes"] for row in samples]
    free = [row["system_free_percent"] for row in samples if row["system_free_percent"] >= 0]
    probe = [row["responsiveness_probe_ms"] for row in samples]
    swaps = [row["swap_used_bytes"] for row in samples if row["swap_used_bytes"] >= 0]
    summary["metrics"] = {
        "active_seconds": sum(float(item["elapsed_seconds"]) for item in summary["prompts"]),
        "tree_rss_average_gib": statistics.fmean(rss) / GIB if rss else 0,
        "tree_rss_p95_gib": percentile(rss, 0.95) / GIB,
        "tree_rss_peak_gib": max(rss, default=0) / GIB,
        "system_used_peak_gib": max(system, default=0) / GIB,
        "system_free_percent_min": min(free, default=-1),
        "memory_pressure_low_seconds": sum(value < 25 for value in free),
        "memory_pressure_critical_seconds": sum(value < 10 for value in free),
        "swap_growth_mib": (swaps[-1] - swaps[0]) / 1024**2 if swaps else -1,
        "responsiveness_probe_p95_ms": percentile(probe, 0.95),
        "process_count_peak": max((row["tree_processes"] for row in samples), default=0),
        "browser_process_count_peak": max((row["tree_browser_processes"] for row in samples), default=0),
    }
    return summary


def percent_delta(profile: float, control: float) -> float:
    return (profile / control - 1) * 100 if control else 0.0


def paired_rows(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for case in cases:
        if case.get("status") != "complete":
            continue
        grouped[(case["workload"], case["agent"], int(case["repetition"]))][case["condition"]] = case
    rows = []
    for (workload, agent, repetition), pair in sorted(grouped.items()):
        if set(pair) != {"profile", "control"}:
            continue
        profile, control = pair["profile"], pair["control"]
        pm, cm = profile["metrics"], control["metrics"]
        rows.append(
            {
                "workload": workload,
                "agent": agent,
                "repetition": repetition,
                "split": profile["split"],
                "profile_quality": profile["quality_passed"],
                "control_quality": control["quality_passed"],
                "time_delta_percent": percent_delta(pm["active_seconds"], cm["active_seconds"]),
                "average_rss_delta_percent": percent_delta(pm["tree_rss_average_gib"], cm["tree_rss_average_gib"]),
                "p95_rss_delta_percent": percent_delta(pm["tree_rss_p95_gib"], cm["tree_rss_p95_gib"]),
                "peak_rss_delta_percent": percent_delta(pm["tree_rss_peak_gib"], cm["tree_rss_peak_gib"]),
                "system_peak_delta_percent": percent_delta(pm["system_used_peak_gib"], cm["system_used_peak_gib"]),
                "profile_min_free_percent": pm["system_free_percent_min"],
                "control_min_free_percent": cm["system_free_percent_min"],
                "profile_low_pressure_seconds": pm["memory_pressure_low_seconds"],
                "control_low_pressure_seconds": cm["memory_pressure_low_seconds"],
                "profile_swap_growth_mib": pm["swap_growth_mib"],
                "control_swap_growth_mib": cm["swap_growth_mib"],
                "responsiveness_delta_percent": percent_delta(
                    pm["responsiveness_probe_p95_ms"], cm["responsiveness_probe_p95_ms"]
                ),
                "profile_process_peak": pm["process_count_peak"],
                "control_process_peak": cm["process_count_peak"],
                "profile_browser_peak": pm["browser_process_count_peak"],
                "control_browser_peak": cm["browser_process_count_peak"],
            }
        )
    return rows


def aggregate(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[(row["workload"], row["agent"])].append(row)
    output = []
    delta_fields = [
        "time_delta_percent", "average_rss_delta_percent", "p95_rss_delta_percent",
        "peak_rss_delta_percent", "system_peak_delta_percent", "responsiveness_delta_percent",
    ]
    for (workload, agent), items in sorted(groups.items()):
        item: dict[str, Any] = {
            "workload": workload,
            "agent": agent,
            "split": items[0]["split"],
            "pairs": len(items),
            "quality_pairs": sum(row["profile_quality"] and row["control_quality"] for row in items),
        }
        valid = [row for row in items if row["profile_quality"] and row["control_quality"]]
        for field in delta_fields:
            values = [float(row[field]) for row in valid]
            item[f"median_{field}"] = statistics.median(values) if values else None
            item[f"min_{field}"] = min(values) if values else None
            item[f"max_{field}"] = max(values) if values else None
        if len(valid) < 3:
            item["decision"] = "more-repetitions"
        elif item["median_peak_rss_delta_percent"] > 5:
            item["decision"] = "profile-regression"
        elif item["median_time_delta_percent"] > 35:
            item["decision"] = "time-regression"
        elif item["median_p95_rss_delta_percent"] <= -10:
            item["decision"] = "profile-benefit"
        else:
            item["decision"] = "ambiguous-expand-to-5-or-7"
        output.append(item)
    return output


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def chart(aggregates: list[dict[str, Any]], output: Path) -> None:
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return
    usable = [row for row in aggregates if row.get("median_p95_rss_delta_percent") is not None]
    if not usable:
        return
    labels = [f"{row['workload']}\n{row['agent']}" for row in usable]
    values = [row["median_p95_rss_delta_percent"] for row in usable]
    colors = ["white" if value <= 0 else "#555555" for value in values]
    fig, ax = plt.subplots(figsize=(max(8, len(labels) * 0.9), 4.8))
    x = np.arange(len(labels))
    bars = ax.bar(x, values, color=colors, edgecolor="black", hatch=["////" if value <= 0 else "" for value in values])
    ax.axhline(0, color="black", linewidth=1)
    ax.axhline(-10, color="#777777", linewidth=0.8, linestyle="--")
    ax.set_ylabel("Median profile delta in P95 RSS (%)")
    ax.set_xticks(x, labels, rotation=35, ha="right")
    ax.grid(axis="y", color="#d0d0d0", linewidth=0.6)
    ax.set_axisbelow(True)
    for bar, value in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:+.1f}%", ha="center", va="bottom" if value >= 0 else "top", fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "p95-rss-delta.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cases = [case_metrics(path.parent) for path in sorted(args.results.glob("*/case-summary.json"))]
    pairs = paired_rows(cases)
    aggregates = aggregate(pairs)
    write_csv(args.output / "paired-results.csv", pairs)
    write_csv(args.output / "aggregate-results.csv", aggregates)
    (args.output / "summary.json").write_text(json.dumps({"cases": cases, "pairs": pairs, "aggregate": aggregates}, indent=2) + "\n")
    chart(aggregates, args.output)
    print(json.dumps(aggregates, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
