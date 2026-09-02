#!/usr/bin/env python3
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent


def main() -> None:
    with (ROOT / "browser-valid-pairs.csv").open() as handle:
        rows = list(csv.DictReader(handle))

    labels = [f"R{row['repetition']} {row['condition']}" for row in rows]
    x = np.arange(len(rows))
    colors = ["white" if row["condition"] == "profile" else "#777777" for row in rows]
    hatches = ["////" if row["condition"] == "profile" else "" for row in rows]

    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
    series = [
        ("p95_tree_rss_gib", "P95 agent-tree RSS", "GiB"),
        ("browser_process_peak", "Peak browser processes", "processes"),
        ("min_free_percent", "Minimum free memory", "%"),
    ]
    for ax, (field, title, unit) in zip(axes, series):
        values = [float(row[field]) for row in rows]
        bars = ax.bar(x, values, color=colors, edgecolor="black", linewidth=1)
        for bar, hatch, value in zip(bars, hatches, values):
            bar.set_hatch(hatch)
            ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:g}", ha="center", va="bottom", fontsize=8)
        ax.set_title(title)
        ax.set_ylabel(unit)
        ax.set_xticks(x, labels, rotation=32, ha="right")
        ax.grid(axis="y", color="#d0d0d0", linewidth=0.6)
        ax.set_axisbelow(True)

    fig.suptitle("8 GB M1 · browser-e2e · quality-valid pairs", fontsize=12)
    fig.tight_layout()
    fig.savefig(ROOT / "browser-evidence.png", dpi=220, bbox_inches="tight", facecolor="white")


if __name__ == "__main__":
    main()
