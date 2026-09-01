#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
CHARTS = ROOT / "charts"
REPORT = ROOT
GIB = 1024**3
CONDITIONS = ["with-profile", "without-profile"]
LABELS = {"with-profile": "8 GB profile", "without-profile": "No profile"}


def load_condition(condition: str) -> dict:
    return json.loads((RAW / condition / "condition-summary.json").read_text())


def load_samples(condition: str) -> list[dict[str, float]]:
    combined: list[dict[str, float]] = []
    offset = 0.0
    for prompt in range(1, 5):
        with (RAW / condition / f"prompt-{prompt:02d}-samples.csv").open() as handle:
            rows = list(csv.DictReader(handle))
        for row in rows:
            sample = {key: float(value) for key, value in row.items()}
            sample["condition_elapsed_seconds"] = offset + sample["elapsed_seconds"]
            sample["prompt"] = float(prompt)
            combined.append(sample)
        if rows:
            offset += float(rows[-1]["elapsed_seconds"])
    return combined


def percentile(values: list[float], q: float) -> float:
    return float(np.percentile(np.asarray(values), q)) if values else 0.0


def failed_commands(condition: str) -> tuple[int, int]:
    failed = 0
    total = 0
    logs_found = False
    for prompt in range(1, 5):
        log_path = RAW / condition / f"prompt-{prompt:02d}.jsonl"
        if not log_path.exists():
            continue
        logs_found = True
        for line in log_path.read_text(errors="replace").splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            item = event.get("item", {})
            if event.get("type") == "item.completed" and item.get("type") == "command_execution":
                total += 1
                if item.get("status") == "failed" or item.get("exit_code") not in (0, None):
                    failed += 1
    if logs_found:
        return failed, total
    saved = json.loads((ROOT / "data" / "command-counts.json").read_text())
    return int(saved[condition]["failed"]), int(saved[condition]["total"])


def style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "black",
            "axes.labelcolor": "black",
            "axes.titleweight": "normal",
            "font.size": 10,
            "text.color": "black",
            "xtick.color": "black",
            "ytick.color": "black",
            "grid.color": "#d0d0d0",
            "grid.linewidth": 0.6,
            "legend.frameon": False,
        }
    )


def save_figure(fig: plt.Figure, name: str) -> None:
    fig.tight_layout()
    fig.savefig(CHARTS / f"{name}.png", dpi=220, bbox_inches="tight")
    fig.savefig(CHARTS / f"{name}.svg", bbox_inches="tight")
    plt.close(fig)


def grouped_bars(
    values: dict[str, list[float]], title: str, ylabel: str, name: str, unit: str, decimals: int = 1
) -> None:
    x = np.arange(4)
    width = 0.34
    fig, ax = plt.subplots(figsize=(8, 4.4))
    bars_a = ax.bar(
        x - width / 2,
        values["with-profile"],
        width,
        label=LABELS["with-profile"],
        facecolor="white",
        edgecolor="black",
        hatch="////",
        linewidth=1,
    )
    bars_b = ax.bar(
        x + width / 2,
        values["without-profile"],
        width,
        label=LABELS["without-profile"],
        facecolor="#4a4a4a",
        edgecolor="black",
        linewidth=1,
    )
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel("Prompt")
    ax.set_xticks(x, ["1 · Core", "2 · Data", "3 · UI", "4 · Final"])
    ax.grid(axis="y")
    ax.set_axisbelow(True)
    ax.legend(ncols=2, loc="upper right")
    maximum = max(max(values["with-profile"]), max(values["without-profile"]))
    ax.set_ylim(0, maximum * 1.2)
    for bars in (bars_a, bars_b):
        for bar in bars:
            value = bar.get_height()
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                value + maximum * 0.025,
                f"{value:.{decimals}f}{unit}",
                ha="center",
                va="bottom",
                fontsize=8,
            )
    save_figure(fig, name)


def main() -> None:
    CHARTS.mkdir(parents=True, exist_ok=True)
    REPORT.mkdir(parents=True, exist_ok=True)
    style()

    conditions = {name: load_condition(name) for name in CONDITIONS}
    samples = {name: load_samples(name) for name in CONDITIONS}

    prompt_rows: list[dict[str, float | int]] = []
    for prompt_index in range(4):
        with_item = conditions["with-profile"]["prompts"][prompt_index]
        without_item = conditions["without-profile"]["prompts"][prompt_index]
        prompt_rows.append(
            {
                "prompt": prompt_index + 1,
                "with_elapsed_seconds": with_item["elapsed_seconds"],
                "without_elapsed_seconds": without_item["elapsed_seconds"],
                "profile_time_delta_seconds": with_item["elapsed_seconds"] - without_item["elapsed_seconds"],
                "profile_time_delta_percent":
                    (with_item["elapsed_seconds"] / without_item["elapsed_seconds"] - 1) * 100,
                "with_peak_tree_rss_gib": with_item["tree_rss_peak_bytes"] / GIB,
                "without_peak_tree_rss_gib": without_item["tree_rss_peak_bytes"] / GIB,
                "profile_peak_rss_delta_percent":
                    (with_item["tree_rss_peak_bytes"] / without_item["tree_rss_peak_bytes"] - 1) * 100,
                "with_average_tree_rss_gib": with_item["tree_rss_average_bytes"] / GIB,
                "without_average_tree_rss_gib": without_item["tree_rss_average_bytes"] / GIB,
                "with_p95_tree_rss_gib": with_item["tree_rss_p95_bytes"] / GIB,
                "without_p95_tree_rss_gib": without_item["tree_rss_p95_bytes"] / GIB,
                "with_peak_processes": with_item["process_count_peak"],
                "without_peak_processes": without_item["process_count_peak"],
                "with_peak_chromium_processes": with_item["chromium_process_count_peak"],
                "without_peak_chromium_processes": without_item["chromium_process_count_peak"],
            }
        )

    comparison_path = ROOT / "data" / "comparison.csv"
    with comparison_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(prompt_rows[0].keys()))
        writer.writeheader()
        writer.writerows(prompt_rows)

    overall: dict[str, dict[str, float | int]] = {}
    for condition in CONDITIONS:
        elapsed = sum(float(item["elapsed_seconds"]) for item in conditions[condition]["prompts"])
        rss = [row["tree_rss_bytes"] for row in samples[condition]]
        system_used = [row["system_used_bytes"] for row in samples[condition]]
        free_percent = [row["system_free_percent"] for row in samples[condition] if row["system_free_percent"] >= 0]
        process_counts = [row["tree_processes"] for row in samples[condition]]
        failed, total_commands = failed_commands(condition)
        overall[condition] = {
            "elapsed_seconds": elapsed,
            "tree_rss_average_gib": sum(rss) / len(rss) / GIB,
            "tree_rss_p95_gib": percentile(rss, 95) / GIB,
            "tree_rss_peak_gib": max(rss) / GIB,
            "system_used_average_gib": sum(system_used) / len(system_used) / GIB,
            "system_used_peak_gib": max(system_used) / GIB,
            "system_free_percent_min": min(free_percent),
            "process_count_average": sum(process_counts) / len(process_counts),
            "process_count_peak": max(process_counts),
            "failed_commands": failed,
            "total_commands": total_commands,
        }

    delta = {
        "elapsed_percent":
            (overall["with-profile"]["elapsed_seconds"] / overall["without-profile"]["elapsed_seconds"] - 1)
            * 100,
        "tree_rss_average_percent":
            (overall["with-profile"]["tree_rss_average_gib"] / overall["without-profile"]["tree_rss_average_gib"] - 1)
            * 100,
        "tree_rss_p95_percent":
            (overall["with-profile"]["tree_rss_p95_gib"] / overall["without-profile"]["tree_rss_p95_gib"] - 1)
            * 100,
        "tree_rss_peak_percent":
            (overall["with-profile"]["tree_rss_peak_gib"] / overall["without-profile"]["tree_rss_peak_gib"] - 1)
            * 100,
        "system_used_peak_percent":
            (overall["with-profile"]["system_used_peak_gib"] / overall["without-profile"]["system_used_peak_gib"] - 1)
            * 100,
    }
    summary = {"overall": overall, "profile_minus_no_profile": delta, "prompts": prompt_rows}
    (ROOT / "data" / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

    grouped_bars(
        {
            condition: [item["elapsed_seconds"] for item in conditions[condition]["prompts"]]
            for condition in CONDITIONS
        },
        "Elapsed time by prompt",
        "Seconds",
        "elapsed-by-prompt",
        "s",
        0,
    )
    grouped_bars(
        {
            condition: [item["tree_rss_peak_bytes"] / GIB for item in conditions[condition]["prompts"]]
            for condition in CONDITIONS
        },
        "Peak Codex process-tree memory by prompt",
        "Peak RSS (GiB)",
        "peak-rss-by-prompt",
        "",
        2,
    )

    fig, axes = plt.subplots(2, 1, figsize=(9, 6.8), sharex=True)
    for condition, color, linestyle in [
        ("with-profile", "black", "-"),
        ("without-profile", "#666666", "--"),
    ]:
        x = [row["condition_elapsed_seconds"] / 60 for row in samples[condition]]
        tree = [row["tree_rss_bytes"] / GIB for row in samples[condition]]
        system = [row["system_used_bytes"] / GIB for row in samples[condition]]
        axes[0].plot(x, tree, color=color, linestyle=linestyle, linewidth=1.2, label=LABELS[condition])
        axes[1].plot(x, system, color=color, linestyle=linestyle, linewidth=1.2, label=LABELS[condition])
    axes[0].set_title("Memory over the four-prompt session")
    axes[0].set_ylabel("Codex tree RSS (GiB)")
    axes[1].set_ylabel("System used memory (GiB)")
    axes[1].set_xlabel("Cumulative active time (minutes)")
    for ax in axes:
        ax.grid(True)
        ax.set_axisbelow(True)
        ax.legend(ncols=2, loc="upper right")
        ax.set_ylim(bottom=0)
    save_figure(fig, "memory-timeline")

    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    names = [LABELS[c] for c in CONDITIONS]
    total_minutes = [overall[c]["elapsed_seconds"] / 60 for c in CONDITIONS]
    peak_rss = [overall[c]["tree_rss_peak_gib"] for c in CONDITIONS]
    for idx, condition in enumerate(CONDITIONS):
        marker = "o" if condition == "with-profile" else "s"
        face = "white" if condition == "with-profile" else "#4a4a4a"
        ax.scatter(total_minutes[idx], peak_rss[idx], s=90, marker=marker, facecolor=face, edgecolor="black")
        ax.annotate(
            names[idx],
            (total_minutes[idx], peak_rss[idx]),
            xytext=(8, 7 if idx == 0 else -14),
            textcoords="offset points",
        )
    ax.set_title("Total time versus peak Codex-tree memory")
    ax.set_xlabel("Total active time (minutes)")
    ax.set_ylabel("Peak RSS (GiB)")
    ax.grid(True)
    ax.set_axisbelow(True)
    ax.set_xlim(min(total_minutes) - 0.5, max(total_minutes) + 0.8)
    ax.set_ylim(min(peak_rss) - 0.08, max(peak_rss) + 0.08)
    save_figure(fig, "time-memory-tradeoff")

    def signed_percent(value: float) -> str:
        return f"{value:+.1f}%"

    report = f"""# Codex RAM profile benchmark — 8 GB MacBook

Date: 2026-09-01

Machine memory: 8 GiB unified memory

Codex CLI: 0.144.6

Model: `gpt-5.6-terra`, medium reasoning

Runs: one four-prompt session per condition

## Result

In this single run, the 8 GB profile did **not** reduce the measured peak Codex process-tree RAM. It finished {abs(delta['elapsed_percent']):.1f}% slower and its peak process-tree RSS was {abs(delta['tree_rss_peak_percent']):.1f}% higher. Its average process-tree RSS was {abs(delta['tree_rss_average_percent']):.1f}% {'lower' if delta['tree_rss_average_percent'] < 0 else 'higher'}, while peak system-wide used memory was {abs(delta['system_used_peak_percent']):.1f}% {'lower' if delta['system_used_peak_percent'] < 0 else 'higher'}.

| Metric | 8 GB profile | No profile | Profile difference |
|---|---:|---:|---:|
| Total active time | {overall['with-profile']['elapsed_seconds']/60:.2f} min | {overall['without-profile']['elapsed_seconds']/60:.2f} min | {signed_percent(delta['elapsed_percent'])} |
| Average Codex-tree RSS | {overall['with-profile']['tree_rss_average_gib']:.2f} GiB | {overall['without-profile']['tree_rss_average_gib']:.2f} GiB | {signed_percent(delta['tree_rss_average_percent'])} |
| P95 Codex-tree RSS | {overall['with-profile']['tree_rss_p95_gib']:.2f} GiB | {overall['without-profile']['tree_rss_p95_gib']:.2f} GiB | {signed_percent(delta['tree_rss_p95_percent'])} |
| Peak Codex-tree RSS | {overall['with-profile']['tree_rss_peak_gib']:.2f} GiB | {overall['without-profile']['tree_rss_peak_gib']:.2f} GiB | {signed_percent(delta['tree_rss_peak_percent'])} |
| Peak system used memory | {overall['with-profile']['system_used_peak_gib']:.2f} GiB | {overall['without-profile']['system_used_peak_gib']:.2f} GiB | {signed_percent(delta['system_used_peak_percent'])} |
| Minimum system free memory | {overall['with-profile']['system_free_percent_min']:.0f}% | {overall['without-profile']['system_free_percent_min']:.0f}% | — |
| Failed shell commands / total | {overall['with-profile']['failed_commands']} / {overall['with-profile']['total_commands']} | {overall['without-profile']['failed_commands']} / {overall['without-profile']['total_commands']} | — |

![Elapsed time by prompt](charts/elapsed-by-prompt.png)

![Peak RSS by prompt](charts/peak-rss-by-prompt.png)

![Memory timeline](charts/memory-timeline.png)

![Time-memory tradeoff](charts/time-memory-tradeoff.png)

## Prompt-level measurements

| Prompt | Profile time | No-profile time | Profile peak RSS | No-profile peak RSS |
|---|---:|---:|---:|---:|
"""
    for row in prompt_rows:
        report += (
            f"| {row['prompt']} | {row['with_elapsed_seconds']:.1f}s | {row['without_elapsed_seconds']:.1f}s | "
            f"{row['with_peak_tree_rss_gib']:.2f} GiB | {row['without_peak_tree_rss_gib']:.2f} GiB |\n"
        )

    report += f"""

## Behavioral observations

- Both conditions completed all four Codex turns with exit code 0 and produced 1,000,000-event, 16-shard workloads.
- The profiled implementation used two analytics workers in its final benchmark; the no-profile implementation used four. Their generated applications and data encodings diverged, so application-level throughput is not an apples-to-apples measure of the instruction file alone.
- During the no-profile dashboard turn, a manually started Next dev server remained running when Playwright tried to start another server. The duplicate-server attempt failed and was retried. The 8 GB profile explicitly asks the agent to reuse one server and clean it up.
- Despite that behavioral win, the profile did not lower overall peak Codex-tree RSS in this run. Prompt 1 implementation variance dominated both total time and the peak comparison.

## Method

Two clean local clones were created from the same seed commit. Dependencies and Playwright Chromium were installed before timing. Only the first clone received `profiles/8gb/AGENTS.md`. Both conditions used the same model, reasoning level, prompt files, package versions, browser cache, and one Codex session continued across four prompts.

The runner sampled once per second. Codex-tree RSS sums the Codex CLI process and all discoverable descendants. System memory comes from `vm_stat`; pressure comes from `memory_pressure -Q`; swap comes from `sysctl vm.swapusage`. Prompt duration begins when `codex exec` starts and ends when that turn exits.

The intended workload was a TypeScript telemetry monorepo with a Next.js dashboard, worker-thread analytics, 1,000,000 deterministic NDJSON events, Vitest integration tests, Playwright browser tests, and a production build. The exact prompts are preserved under `prompts/`.

## Limitations

- This is one run per condition, not a statistically powered benchmark.
- The required order was profile first, then no profile. Filesystem, compiler, browser, and server-side prompt caches may favor the second run.
- Coding-agent output is stochastic. The two agents produced different code, data sizes, worker counts, and intermediate failures. The result measures the complete agent workflow, not only scheduler policy.
- Process-tree sampling can miss a process that fully detaches and is re-parented before a sample.
- System-wide memory includes unrelated macOS and user processes. Starting free-memory baselines were close but not identical.
- A preliminary smoke run exposed harness sandbox and copied-`node_modules` issues. It was discarded, archived separately, and excluded from every reported number.
- The agents ran with approval/sandbox bypass inside dedicated benchmark directories so `tsx`, Next, and Playwright could execute consistently. Prompts constrained work to those repositories.

## Reproduction

Use `scripts/benchmark_runner.py` with the four locked prompt files. Install dependencies and Chromium before starting, use clean clones, and reverse the condition order in a second replication. A credible conclusion should use at least five alternating A/B and B/A repetitions.
"""
    (REPORT / "README.generated.md").write_text(report)


if __name__ == "__main__":
    main()
