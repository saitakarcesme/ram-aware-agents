#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

GIB = 1024**3
ROOT = Path(__file__).resolve().parents[3]
V2 = ROOT / "benchmarks" / "v2"
WORKLOADS = V2 / "workloads"
PROTOCOL = json.loads((V2 / "protocol.json").read_text())
TOTAL_MEMORY = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
PAGE_SIZE = int(subprocess.check_output(["sysctl", "-n", "hw.pagesize"], text=True).strip())


def run_text(command: list[str]) -> str:
    return subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL)


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    fraction = position - low
    return ordered[low] * (1 - fraction) + ordered[high] * fraction


def process_table() -> tuple[dict[int, tuple[int, int, float, str]], dict[int, list[int]]]:
    output = run_text(["ps", "-axo", "pid=,ppid=,rss=,%cpu=,command="])
    rows: dict[int, tuple[int, int, float, str]] = {}
    children: dict[int, list[int]] = {}
    for line in output.splitlines():
        parts = line.strip().split(None, 4)
        if len(parts) != 5:
            continue
        try:
            pid, ppid, rss, cpu = int(parts[0]), int(parts[1]), int(parts[2]), float(parts[3])
        except ValueError:
            continue
        rows[pid] = (ppid, rss, cpu, parts[4])
        children.setdefault(ppid, []).append(pid)
    return rows, children


def process_snapshot(root_pid: int) -> dict[str, float | int]:
    rows, children = process_table()
    descendants: set[int] = set()
    pending = [root_pid]
    while pending:
        pid = pending.pop()
        if pid in descendants:
            continue
        descendants.add(pid)
        pending.extend(children.get(pid, []))
    selected = [rows[pid] for pid in descendants if pid in rows]
    commands = [row[3] for row in selected]
    return {
        "tree_rss_bytes": sum(row[1] for row in selected) * 1024,
        "tree_cpu_percent": sum(row[2] for row in selected),
        "tree_processes": len(selected),
        "tree_node_processes": sum(bool(re.search(r"(^|/)node(\s|$)", command)) for command in commands),
        "tree_browser_processes": sum(
            bool(re.search(r"chrom(e|ium)|playwright|webkit|firefox", command, re.IGNORECASE))
            for command in commands
        ),
    }


def system_snapshot() -> dict[str, float | int]:
    stats: dict[str, int] = {}
    for line in run_text(["vm_stat"]).splitlines():
        match = re.match(r"([^:]+):\s+([0-9]+)\.", line)
        if match:
            stats[match.group(1)] = int(match.group(2))
    free_pages = sum(
        stats.get(key, 0) for key in ("Pages free", "Pages inactive", "Pages speculative")
    )
    pressure = run_text(["memory_pressure", "-Q"])
    pressure_match = re.search(r"free percentage:\s*([0-9]+)%", pressure)
    swap = run_text(["sysctl", "vm.swapusage"])
    swap_match = re.search(r"used = ([0-9.]+)M", swap)
    probe_started = time.monotonic_ns()
    subprocess.run(["/usr/bin/true"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    probe_ms = (time.monotonic_ns() - probe_started) / 1_000_000
    return {
        "system_used_bytes": max(0, TOTAL_MEMORY - free_pages * PAGE_SIZE),
        "system_compressed_bytes": stats.get("Pages occupied by compressor", 0) * PAGE_SIZE,
        "system_wired_bytes": stats.get("Pages wired down", 0) * PAGE_SIZE,
        "system_free_percent": int(pressure_match.group(1)) if pressure_match else -1,
        "swap_used_bytes": int(float(swap_match.group(1)) * 1024 * 1024) if swap_match else -1,
        "responsiveness_probe_ms": probe_ms,
    }


def current_leaks(project: Path) -> list[dict[str, Any]]:
    rows, _ = process_table()
    marker = str(project)
    leaks = []
    for pid, (ppid, rss, cpu, command) in rows.items():
        if marker in command:
            leaks.append({"pid": pid, "ppid": ppid, "rss_bytes": rss * 1024, "cpu_percent": cpu, "command": command})
    return leaks


def stop_leaks(leaks: list[dict[str, Any]]) -> None:
    own_pid = os.getpid()
    pids = [int(item["pid"]) for item in leaks if int(item["pid"]) != own_pid]
    for pid in pids:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    if pids:
        time.sleep(2)
    for pid in pids:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            continue
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


def summarize(samples: list[dict[str, float | int]], elapsed: float, exit_code: int) -> dict[str, Any]:
    rss = [float(row["tree_rss_bytes"]) for row in samples]
    system = [float(row["system_used_bytes"]) for row in samples]
    free = [float(row["system_free_percent"]) for row in samples if float(row["system_free_percent"]) >= 0]
    swap = [float(row["swap_used_bytes"]) for row in samples if float(row["swap_used_bytes"]) >= 0]
    probe = [float(row["responsiveness_probe_ms"]) for row in samples]
    sample_interval = float(PROTOCOL["sample_interval_seconds"])
    return {
        "elapsed_seconds": elapsed,
        "exit_code": exit_code,
        "sample_count": len(samples),
        "tree_rss_average_bytes": statistics.fmean(rss) if rss else 0,
        "tree_rss_p95_bytes": percentile(rss, 0.95),
        "tree_rss_peak_bytes": max(rss, default=0),
        "system_used_average_bytes": statistics.fmean(system) if system else 0,
        "system_used_peak_bytes": max(system, default=0),
        "system_free_percent_min": min(free, default=-1),
        "memory_pressure_low_seconds": sum(value < 25 for value in free) * sample_interval,
        "memory_pressure_critical_seconds": sum(value < 10 for value in free) * sample_interval,
        "swap_start_bytes": swap[0] if swap else -1,
        "swap_end_bytes": swap[-1] if swap else -1,
        "swap_growth_bytes": (swap[-1] - swap[0]) if swap else -1,
        "responsiveness_probe_p95_ms": percentile(probe, 0.95),
        "process_count_peak": max((int(row["tree_processes"]) for row in samples), default=0),
        "browser_process_count_peak": max((int(row["tree_browser_processes"]) for row in samples), default=0),
    }


def codex_command(prompt: str, session_id: str | None) -> list[str]:
    common = [
        "--json",
        "--ignore-user-config",
        "--ignore-rules",
        "--dangerously-bypass-approvals-and-sandbox",
        "-m",
        PROTOCOL["agents"]["codex"]["model"],
        "-c",
        f'model_reasoning_effort="{PROTOCOL["agents"]["codex"]["effort"]}"',
    ]
    if session_id:
        return ["codex", "exec", "resume", *common, session_id, prompt]
    return ["codex", "exec", *common, prompt]


def claude_command(prompt: str, session_id: str, first: bool) -> list[str]:
    common = [
        "-p",
        "--output-format",
        "stream-json",
        "--verbose",
        "--model",
        PROTOCOL["agents"]["claude"]["model"],
        "--effort",
        PROTOCOL["agents"]["claude"]["effort"],
        "--permission-mode",
        "bypassPermissions",
        "--no-chrome",
        "--strict-mcp-config",
        "--mcp-config",
        '{"mcpServers":{}}',
        "--setting-sources",
        "project",
    ]
    session = ["--session-id", session_id] if first else ["--resume", session_id]
    return ["claude", *common, *session, prompt]


def codex_session_id(log_path: Path) -> str | None:
    for line in log_path.read_text(errors="replace").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "thread.started":
            return event.get("thread_id")
    return None


def execute_prompt(
    *, agent: str, project: Path, prompt: str, prompt_index: int, output: Path,
    session_id: str | None, codex_home: Path,
) -> tuple[dict[str, Any], str | None]:
    log_path = output / f"prompt-{prompt_index:02d}.jsonl"
    csv_path = output / f"prompt-{prompt_index:02d}-samples.csv"
    if agent == "codex":
        command = codex_command(prompt, session_id)
    else:
        session_id = session_id or str(uuid.uuid4())
        command = claude_command(prompt, session_id, first=prompt_index == 1)
    environment = os.environ.copy()
    environment.update({"NO_COLOR": "1", "CI": "1", "PNPM_CONFIG_CONFIRM_MODULES_PURGE": "false"})
    if agent == "codex":
        environment["CODEX_HOME"] = str(codex_home)
    started = time.monotonic()
    samples: list[dict[str, float | int]] = []
    timed_out = False
    with log_path.open("w") as log_file:
        process = subprocess.Popen(
            command, cwd=project, env=environment, stdout=log_file, stderr=subprocess.STDOUT,
            text=True, start_new_session=True,
        )
        while process.poll() is None:
            loop_started = time.monotonic()
            sample: dict[str, float | int] = {
                "timestamp_epoch": time.time(),
                "elapsed_seconds": loop_started - started,
            }
            try:
                sample.update(process_snapshot(process.pid))
                sample.update(system_snapshot())
                sample["sampler_lag_ms"] = max(
                    0.0, (time.monotonic() - loop_started - float(PROTOCOL["sample_interval_seconds"])) * 1000
                )
                samples.append(sample)
            except (OSError, subprocess.SubprocessError):
                pass
            if time.monotonic() - started > int(PROTOCOL["prompt_timeout_seconds"]):
                timed_out = True
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                break
            remaining = float(PROTOCOL["sample_interval_seconds"]) - (time.monotonic() - loop_started)
            if remaining > 0:
                time.sleep(remaining)
        exit_code = process.wait()
    elapsed = time.monotonic() - started
    if samples:
        with csv_path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(samples[0]))
            writer.writeheader()
            writer.writerows(samples)
    summary = summarize(samples, elapsed, exit_code)
    summary.update({"prompt_index": prompt_index, "timed_out": timed_out})
    (output / f"prompt-{prompt_index:02d}-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    if agent == "codex" and not session_id:
        session_id = codex_session_id(log_path)
    return summary, session_id


def capability_status(workload: dict[str, Any]) -> tuple[bool, str]:
    missing = [name for name in workload.get("capability", []) if shutil.which(name) is None]
    if missing:
        return False, f"missing commands: {', '.join(missing)}"
    if workload.get("requires_docker_daemon"):
        result = subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode:
            return False, "Docker daemon unavailable"
    return True, "available"


def prepare_project(base: Path, workload: dict[str, Any], agent: str, condition: str) -> Path:
    project = base / "project"
    project.mkdir(parents=True)
    (project / "BENCHMARK_SPEC.md").write_text(f"# {workload['title']}\n\n{workload['spec']}\n")
    (project / "README.md").write_text(f"# {workload['title']}\n\nGenerated from a locked benchmark specification.\n")
    if condition == "profile":
        source = ROOT / "profiles" / "8gb" / ("AGENTS.md" if agent == "codex" else "CLAUDE.md")
        shutil.copy2(source, project / source.name)
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.name", "RAM Benchmark"], cwd=project, check=True)
    subprocess.run(["git", "config", "user.email", "benchmark@example.invalid"], cwd=project, check=True)
    subprocess.run(["git", "add", "."], cwd=project, check=True)
    subprocess.run(["git", "commit", "-qm", "benchmark seed"], cwd=project, check=True)
    return project


def profile_identity(agent: str) -> dict[str, str]:
    path = ROOT / "profiles" / "8gb" / ("AGENTS.md" if agent == "codex" else "CLAUDE.md")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    return {"path": str(path.relative_to(ROOT)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "commit": commit}


def verify(project: Path, workload: dict[str, Any], output: Path) -> dict[str, Any]:
    results = []
    forbidden = [re.compile(pattern, re.IGNORECASE) for pattern in workload.get("forbid_verify_patterns", [])]
    for command in workload["verify"]:
        started = time.monotonic()
        completed = subprocess.run(
            command, cwd=project, shell=True, text=True, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, timeout=1800,
        )
        log_name = f"verify-{len(results) + 1:02d}.log"
        (output / log_name).write_text(completed.stdout)
        matches = [pattern.pattern for pattern in forbidden if pattern.search(completed.stdout)]
        results.append({
            "command": command,
            "exit_code": completed.returncode,
            "elapsed_seconds": time.monotonic() - started,
            "forbidden_output_matches": matches,
        })
    required = [
        {"path": path, "exists": (project / path).exists()}
        for path in workload.get("required_files", ["BENCHMARK_RESULTS.md"])
    ]
    required_any = [
        {
            "paths": paths,
            "matched": [path for path in paths if (project / path).exists()],
        }
        for paths in workload.get("required_any_files", [])
    ]
    passed = all(item["exit_code"] == 0 and not item["forbidden_output_matches"] for item in results)
    passed = passed and all(item["exists"] for item in required)
    passed = passed and all(item["matched"] for item in required_any)
    return {
        "passed": passed,
        "commands": results,
        "required_files": required,
        "required_any_files": required_any,
    }


def run_case(args: argparse.Namespace, workload: dict[str, Any], repetition: int, condition: str) -> dict[str, Any]:
    case_id = f"{workload['id']}__{args.agent}__{condition}__r{repetition:02d}"
    output = args.results / case_id
    output.mkdir(parents=True, exist_ok=False)
    available, reason = capability_status(workload)
    if not available:
        result = {"case_id": case_id, "status": "unavailable", "reason": reason}
        (output / "case-summary.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    temp_parent = Path(tempfile.mkdtemp(prefix=f"ram-bench-{workload['id']}-", dir=args.workspace))
    project = prepare_project(temp_parent, workload, args.agent, condition)
    codex_home = temp_parent / "codex-home"
    codex_home.mkdir()
    auth_source = Path.home() / ".codex" / "auth.json"
    if args.agent == "codex" and auth_source.exists():
        (codex_home / "auth.json").symlink_to(auth_source)
    session_id: str | None = None
    prompt_summaries = []
    baseline = system_snapshot()
    case_started = time.monotonic()
    try:
        for index, task in enumerate(workload["prompts"], start=1):
            prompt = (
                "Read BENCHMARK_SPEC.md and continue the same benchmark project. "
                + task
                + " Work only inside this repository. Do not reduce required dataset sizes or skip requested validation."
            )
            print(f"[{case_id}] prompt {index}/{len(workload['prompts'])}", flush=True)
            summary, session_id = execute_prompt(
                agent=args.agent, project=project, prompt=prompt, prompt_index=index,
                output=output, session_id=session_id, codex_home=codex_home,
            )
            prompt_summaries.append(summary)
            if summary["exit_code"] != 0 or summary["timed_out"] or session_id is None:
                break
            time.sleep(int(PROTOCOL["cooldown_seconds"]))
        verification = verify(project, workload, output) if len(prompt_summaries) == len(workload["prompts"]) else {"passed": False, "commands": [], "required_files": []}
        leaks = current_leaks(project)
        stop_leaks(leaks)
        result = {
            "case_id": case_id,
            "status": "complete" if len(prompt_summaries) == len(workload["prompts"]) else "incomplete",
            "workload": workload["id"],
            "split": workload["profile_split"],
            "agent": args.agent,
            "condition": condition,
            "profile_identity": profile_identity(args.agent),
            "repetition": repetition,
            "elapsed_seconds": time.monotonic() - case_started,
            "baseline": baseline,
            "prompts": prompt_summaries,
            "verification": verification,
            "leaked_processes": leaks,
            "quality_passed": verification["passed"] and not leaks,
        }
        (output / "case-summary.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    finally:
        if not args.keep_projects:
            shutil.rmtree(temp_parent, ignore_errors=True)


def load_workloads(selected: list[str]) -> list[dict[str, Any]]:
    items = []
    for path in sorted(WORKLOADS.glob("*.json")):
        item = json.loads(path.read_text())
        if not selected or item["id"] in selected:
            items.append(item)
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description="Run clean, paired RAM-profile benchmark projects.")
    parser.add_argument("--agent", choices=["codex", "claude"], required=True)
    parser.add_argument("--workload", action="append", default=[])
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--results", type=Path, default=V2 / "results" / "local")
    parser.add_argument("--workspace", type=Path, default=Path(tempfile.gettempdir()))
    parser.add_argument("--keep-projects", action="store_true")
    parser.add_argument("--only-condition", choices=["profile", "control"])
    args = parser.parse_args()
    args.results.mkdir(parents=True, exist_ok=True)
    args.workspace.mkdir(parents=True, exist_ok=True)
    workloads = load_workloads(args.workload)
    if not workloads:
        raise SystemExit("No matching workloads")
    manifest = []
    for workload in workloads:
        for repetition in range(1, args.repetitions + 1):
            order = ["profile", "control"] if repetition % 2 else ["control", "profile"]
            if args.only_condition:
                order = [args.only_condition]
            for condition in order:
                case_dir = args.results / f"{workload['id']}__{args.agent}__{condition}__r{repetition:02d}"
                if case_dir.exists():
                    print(f"Skipping existing {case_dir.name}", flush=True)
                    continue
                manifest.append(run_case(args, workload, repetition, condition))
                time.sleep(int(PROTOCOL["cooldown_seconds"]))
    (args.results / f"manifest-{args.agent}.json").write_text(json.dumps(manifest, indent=2) + "\n")
    successful = all(
        item.get("status") == "unavailable"
        or (item.get("status") == "complete" and item.get("quality_passed") is True)
        for item in manifest
    )
    return 0 if successful else 1


if __name__ == "__main__":
    raise SystemExit(main())
