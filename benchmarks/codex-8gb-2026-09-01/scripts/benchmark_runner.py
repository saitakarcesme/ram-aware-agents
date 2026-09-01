#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

TOTAL_MEMORY = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
PAGE_SIZE = int(subprocess.check_output(["sysctl", "-n", "hw.pagesize"], text=True).strip())


def run_text(command: list[str]) -> str:
    return subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL)


def process_snapshot(root_pid: int) -> dict[str, float | int]:
    output = run_text(["ps", "-axo", "pid=,ppid=,rss=,%cpu=,command="])
    rows: list[tuple[int, int, int, float, str]] = []
    children: dict[int, list[int]] = {}
    by_pid: dict[int, tuple[int, int, int, float, str]] = {}
    for line in output.splitlines():
        parts = line.strip().split(None, 4)
        if len(parts) < 5:
            continue
        try:
            row = (int(parts[0]), int(parts[1]), int(parts[2]), float(parts[3]), parts[4])
        except ValueError:
            continue
        rows.append(row)
        by_pid[row[0]] = row
        children.setdefault(row[1], []).append(row[0])

    descendants: set[int] = set()
    pending = [root_pid]
    while pending:
        pid = pending.pop()
        if pid in descendants:
            continue
        descendants.add(pid)
        pending.extend(children.get(pid, []))

    selected = [by_pid[pid] for pid in descendants if pid in by_pid]
    return {
        "tree_rss_bytes": sum(row[2] for row in selected) * 1024,
        "tree_cpu_percent": sum(row[3] for row in selected),
        "tree_processes": len(selected),
        "tree_chromium_processes": sum(
            1 for row in selected if re.search(r"chrom(e|ium)|playwright", row[4], re.IGNORECASE)
        ),
        "tree_node_processes": sum(1 for row in selected if re.search(r"(^|/)node(\s|$)", row[4])),
    }


def system_snapshot() -> dict[str, float | int]:
    stats: dict[str, int] = {}
    for line in run_text(["vm_stat"]).splitlines():
        match = re.match(r"([^:]+):\s+([0-9]+)\.", line)
        if match:
            stats[match.group(1)] = int(match.group(2))

    free_pages = (
        stats.get("Pages free", 0)
        + stats.get("Pages inactive", 0)
        + stats.get("Pages speculative", 0)
    )
    compressed = stats.get("Pages occupied by compressor", 0) * PAGE_SIZE
    wired = stats.get("Pages wired down", 0) * PAGE_SIZE
    used = max(0, TOTAL_MEMORY - free_pages * PAGE_SIZE)

    pressure = run_text(["memory_pressure", "-Q"])
    pressure_match = re.search(r"free percentage:\s*([0-9]+)%", pressure)
    free_percent = int(pressure_match.group(1)) if pressure_match else -1

    swap = run_text(["sysctl", "vm.swapusage"])
    swap_match = re.search(r"used = ([0-9.]+)M", swap)
    swap_used = float(swap_match.group(1)) * 1024 * 1024 if swap_match else -1

    return {
        "system_used_bytes": used,
        "system_compressed_bytes": compressed,
        "system_wired_bytes": wired,
        "system_free_percent": free_percent,
        "swap_used_bytes": int(swap_used),
    }


def summarize(samples: list[dict[str, float | int]], elapsed: float, exit_code: int) -> dict[str, object]:
    def percentile(values: list[float], fraction: float) -> float:
        if not values:
            return 0.0
        ordered = sorted(values)
        index = min(len(ordered) - 1, round((len(ordered) - 1) * fraction))
        return ordered[index]

    rss = [float(sample["tree_rss_bytes"]) for sample in samples]
    system_used = [float(sample["system_used_bytes"]) for sample in samples]
    swap = [float(sample["swap_used_bytes"]) for sample in samples]
    return {
        "elapsed_seconds": elapsed,
        "exit_code": exit_code,
        "samples": len(samples),
        "tree_rss_average_bytes": sum(rss) / len(rss) if rss else 0,
        "tree_rss_p95_bytes": percentile(rss, 0.95),
        "tree_rss_peak_bytes": max(rss, default=0),
        "system_used_average_bytes": sum(system_used) / len(system_used) if system_used else 0,
        "system_used_peak_bytes": max(system_used, default=0),
        "swap_start_bytes": swap[0] if swap else 0,
        "swap_end_bytes": swap[-1] if swap else 0,
        "swap_peak_bytes": max(swap, default=0),
        "process_count_peak": max((int(s["tree_processes"]) for s in samples), default=0),
        "chromium_process_count_peak": max(
            (int(s["tree_chromium_processes"]) for s in samples), default=0
        ),
    }


def find_thread_id(log_path: Path) -> str | None:
    for line in log_path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "thread.started":
            return event.get("thread_id")
        if isinstance(event.get("thread"), dict) and event["thread"].get("id"):
            return event["thread"]["id"]
    return None


def execute_prompt(
    project: Path,
    condition: str,
    prompt_index: int,
    prompt: str,
    output_dir: Path,
    codex_home: Path,
    thread_id: str | None,
    timeout_seconds: int,
) -> tuple[dict[str, object], str | None]:
    log_path = output_dir / f"prompt-{prompt_index:02d}.jsonl"
    csv_path = output_dir / f"prompt-{prompt_index:02d}-samples.csv"
    summary_path = output_dir / f"prompt-{prompt_index:02d}-summary.json"

    common = [
        "--json",
        "--ignore-user-config",
        "--ignore-rules",
        "--dangerously-bypass-approvals-and-sandbox",
        "-m",
        "gpt-5.6-terra",
        "-c",
        'model_reasoning_effort="medium"',
    ]
    if thread_id is None:
        command = ["codex", "exec", *common, prompt]
    else:
        command = ["codex", "exec", "resume", *common, thread_id, prompt]

    environment = os.environ.copy()
    environment["CODEX_HOME"] = str(codex_home)
    environment["NO_COLOR"] = "1"
    environment["PNPM_CONFIG_CONFIRM_MODULES_PURGE"] = "false"

    started = time.monotonic()
    samples: list[dict[str, float | int]] = []
    with log_path.open("w") as log_file:
        process = subprocess.Popen(
            command,
            cwd=project,
            env=environment,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        timed_out = False
        while process.poll() is None:
            now = time.monotonic()
            sample: dict[str, float | int] = {
                "timestamp_epoch": time.time(),
                "elapsed_seconds": now - started,
            }
            try:
                sample.update(process_snapshot(process.pid))
                sample.update(system_snapshot())
                samples.append(sample)
            except (OSError, subprocess.SubprocessError):
                pass
            if now - started > timeout_seconds:
                timed_out = True
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                break
            time.sleep(1)
        exit_code = process.wait()

    elapsed = time.monotonic() - started
    fieldnames = list(samples[0].keys()) if samples else []
    with csv_path.open("w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
            writer.writerows(samples)

    summary = summarize(samples, elapsed, exit_code)
    summary.update(
        {
            "condition": condition,
            "prompt_index": prompt_index,
            "timed_out": timed_out,
            "model": "gpt-5.6-terra",
            "reasoning_effort": "medium",
            "project": str(project),
        }
    )
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    return summary, thread_id or find_thread_id(log_path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--condition", required=True)
    parser.add_argument("--prompts", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--codex-home", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    args = parser.parse_args()

    output_dir = args.results / args.condition
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_paths = sorted(args.prompts.glob("[0-9][0-9]-*.md"))
    if len(prompt_paths) != 4:
        raise SystemExit(f"Expected 4 prompts, found {len(prompt_paths)}")

    thread_id: str | None = None
    all_summaries: list[dict[str, object]] = []
    for index, prompt_path in enumerate(prompt_paths, start=1):
        prompt = prompt_path.read_text().strip()
        print(f"[{args.condition}] prompt {index}/4: {prompt_path.name}", flush=True)
        summary, thread_id = execute_prompt(
            args.project,
            args.condition,
            index,
            prompt,
            output_dir,
            args.codex_home,
            thread_id,
            args.timeout_seconds,
        )
        all_summaries.append(summary)
        print(
            f"[{args.condition}] prompt {index} finished: "
            f"exit={summary['exit_code']} elapsed={summary['elapsed_seconds']:.1f}s "
            f"peak_rss={float(summary['tree_rss_peak_bytes']) / 1024**3:.2f}GiB",
            flush=True,
        )
        if thread_id is None:
            print("Unable to determine Codex thread id; stopping condition.", file=sys.stderr)
            return 2
        time.sleep(10)

    (output_dir / "condition-summary.json").write_text(
        json.dumps({"condition": args.condition, "thread_id": thread_id, "prompts": all_summaries}, indent=2)
        + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
