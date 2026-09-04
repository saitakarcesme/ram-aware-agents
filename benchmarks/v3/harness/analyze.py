#!/usr/bin/env python3
"""Analyze quality-valid v3 three-arm benchmark repetitions."""

from __future__ import annotations

import argparse
import csv
import html
import importlib.util
import json
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
V2_ANALYZE = ROOT / "benchmarks" / "v2" / "harness" / "analyze.py"
SPEC = importlib.util.spec_from_file_location("ram_benchmark_v2_analyze", V2_ANALYZE)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load benchmark analyzer: {V2_ANALYZE}")
ENGINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENGINE)

CONDITIONS = ("control", "profile", "hook")
METRICS = (
    "active_seconds",
    "tree_rss_average_gib",
    "tree_rss_p95_gib",
    "tree_rss_peak_gib",
    "system_used_peak_gib",
    "system_free_percent_min",
    "system_free_drop_points",
    "responsiveness_probe_p95_ms",
    "process_count_peak",
    "browser_process_count_peak",
)


def delta(value: float, baseline: float) -> float | None:
    return (value / baseline - 1) * 100 if baseline else None


def valid_triples(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for case in cases:
        if case.get("status") == "complete":
            grouped[(case["workload"], case["agent"], int(case["repetition"]))][case["condition"]] = case
    triples = []
    for (workload, agent, repetition), group in sorted(grouped.items()):
        if set(group) != set(CONDITIONS):
            continue
        quality = all(group[name].get("quality_passed") is True for name in CONDITIONS)
        row: dict[str, Any] = {
            "workload": workload,
            "agent": agent,
            "repetition": repetition,
            "split": group["control"]["split"],
            "quality_valid": quality,
        }
        for metric in METRICS:
            baseline = float(group["control"]["metrics"][metric])
            for condition in CONDITIONS:
                value = float(group[condition]["metrics"][metric])
                row[f"{condition}_{metric}"] = value
                if condition != "control":
                    row[f"{condition}_{metric}_delta_percent"] = delta(value, baseline)
            profile_value = float(group["profile"]["metrics"][metric])
            hook_value = float(group["hook"]["metrics"][metric])
            row[f"hook_vs_profile_{metric}_delta_percent"] = delta(hook_value, profile_value)
        triples.append(row)
    return triples


def aggregate(triples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in triples:
        groups[(row["workload"], row["agent"])].append(row)
    output = []
    for (workload, agent), rows in sorted(groups.items()):
        valid = [row for row in rows if row["quality_valid"]]
        item: dict[str, Any] = {
            "workload": workload,
            "agent": agent,
            "triples": len(rows),
            "quality_triples": len(valid),
            "decision": "more-repetitions" if len(valid) < 3 else "compare-medians",
        }
        for condition in ("profile", "hook"):
            for metric in ("active_seconds", "tree_rss_p95_gib", "tree_rss_peak_gib", "system_free_drop_points", "responsiveness_probe_p95_ms"):
                field = f"{condition}_{metric}_delta_percent"
                values = [float(row[field]) for row in valid if row[field] is not None]
                item[f"median_{field}"] = statistics.median(values) if values else None
        for metric in ("active_seconds", "tree_rss_p95_gib", "tree_rss_peak_gib", "system_free_drop_points", "responsiveness_probe_p95_ms"):
            field = f"hook_vs_profile_{metric}_delta_percent"
            values = [float(row[field]) for row in valid if row[field] is not None]
            item[f"median_{field}"] = statistics.median(values) if values else None
        output.append(item)
    return output


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def chart(triples: list[dict[str, Any]], output: Path) -> None:
    chart_svg(triples, output)
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        return
    valid = [row for row in triples if row["quality_valid"]]
    if not valid:
        return
    labels = [f"{row['workload']} r{row['repetition']}" for row in valid]
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    specs = (
        ("tree_rss_p95_gib", "P95 process-tree RSS", "GiB"),
        ("active_seconds", "Active completion time", "seconds"),
        ("system_free_drop_points", "Free-memory drop", "percentage points"),
    )
    x = np.arange(len(labels))
    width = 0.24
    styles = {
        "control": {"color": "white", "hatch": "", "edgecolor": "black"},
        "profile": {"color": "#bdbdbd", "hatch": "///", "edgecolor": "black"},
        "hook": {"color": "#303030", "hatch": "", "edgecolor": "black"},
    }
    for axis, (metric, title, unit) in zip(axes, specs):
        for index, condition in enumerate(CONDITIONS):
            values = [row[f"{condition}_{metric}"] for row in valid]
            axis.bar(x + (index - 1) * width, values, width, label=condition, **styles[condition])
        axis.set_title(title)
        axis.set_ylabel(unit)
        axis.set_xticks(x, labels, rotation=35, ha="right")
        axis.grid(axis="y", color="#d0d0d0", linewidth=0.6)
        axis.set_axisbelow(True)
    axes[0].legend(frameon=False)
    fig.tight_layout()
    fig.savefig(output / "agents-vs-hook.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


def chart_svg(triples: list[dict[str, Any]], output: Path) -> None:
    valid = [row for row in triples if row["quality_valid"]]
    if not valid:
        return
    conditions = ("control", "profile", "hook")
    fills = {"control": "#ffffff", "profile": "#a8a8a8", "hook": "#222222"}
    panels = (
        ("tree_rss_peak_gib", "Peak process-tree RSS", "GiB"),
        ("active_seconds", "Active completion time", "seconds"),
    )
    width, height = 1000, 520
    panel_width, left, top, plot_height = 460, 70, 75, 320
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;fill:#111} .title{font-size:18px;font-weight:600}.axis{font-size:11px}.value{font-size:10px}.frame{fill:none;stroke:#222;stroke-width:1}.grid{stroke:#ddd;stroke-width:1}</style>',
        '<text x="20" y="30" class="title">RAM-aware mechanism comparison — quality-valid v3 runs</text>',
    ]
    for panel_index, (metric, title, unit) in enumerate(panels):
        x0 = 20 + panel_index * 500
        values = [float(row[f"{condition}_{metric}"]) for row in valid for condition in conditions]
        maximum = max(values) * 1.12 if max(values) > 0 else 1
        parts.append(f'<text x="{x0 + panel_width / 2}" y="58" text-anchor="middle" class="title">{html.escape(title)}</text>')
        for tick in range(5):
            y = top + plot_height - tick * plot_height / 4
            tick_value = maximum * tick / 4
            parts.append(f'<line x1="{x0 + left}" y1="{y:.1f}" x2="{x0 + panel_width}" y2="{y:.1f}" class="grid"/>')
            parts.append(f'<text x="{x0 + left - 8}" y="{y + 4:.1f}" text-anchor="end" class="axis">{tick_value:.1f}</text>')
        parts.append(f'<rect x="{x0 + left}" y="{top}" width="{panel_width - left}" height="{plot_height}" class="frame"/>')
        group_width = (panel_width - left) / len(valid)
        bar_width = min(26, group_width / 4)
        for row_index, row in enumerate(valid):
            center = x0 + left + group_width * (row_index + 0.5)
            for condition_index, condition in enumerate(conditions):
                value = float(row[f"{condition}_{metric}"])
                bar_height = value / maximum * plot_height
                x = center + (condition_index - 1) * (bar_width + 3) - bar_width / 2
                y = top + plot_height - bar_height
                parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_height:.1f}" fill="{fills[condition]}" stroke="#111"/>')
                label = f"{value:.2f}" if value < 10 else f"{value:.0f}"
                parts.append(f'<text x="{x + bar_width / 2:.1f}" y="{max(top + 11, y - 4):.1f}" text-anchor="middle" class="value">{label}</text>')
            label = f"{row['workload']} r{row['repetition']}"
            parts.append(f'<text x="{center:.1f}" y="{top + plot_height + 20}" text-anchor="middle" class="axis">{html.escape(label)}</text>')
        parts.append(f'<text x="{x0 + 10}" y="{top + plot_height / 2}" transform="rotate(-90 {x0 + 10} {top + plot_height / 2})" text-anchor="middle" class="axis">{html.escape(unit)}</text>')
    legend_x = 285
    display_names = {"control": "control", "profile": "AGENTS.md", "hook": "hook"}
    for index, condition in enumerate(conditions):
        x = legend_x + index * 170
        parts.append(f'<rect x="{x}" y="475" width="18" height="18" fill="{fills[condition]}" stroke="#111"/>')
        parts.append(f'<text x="{x + 26}" y="489" class="axis">{html.escape(display_names[condition])}</text>')
    parts.append('</svg>')
    (output / "agents-vs-hook.svg").write_text("\n".join(parts) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    cases = [ENGINE.case_metrics(path.parent) for path in sorted(args.results.glob("*/case-summary.json"))]
    triples = valid_triples(cases)
    aggregates = aggregate(triples)
    write_csv(args.output / "three-arm-results.csv", triples)
    write_csv(args.output / "aggregate-results.csv", aggregates)
    (args.output / "summary.json").write_text(json.dumps({"cases": cases, "triples": triples, "aggregate": aggregates}, indent=2) + "\n")
    chart(triples, args.output)
    print(json.dumps(aggregates, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
