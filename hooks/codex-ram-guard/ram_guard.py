#!/usr/bin/env python3
"""RAM-aware Codex hook and serialized heavy-command runner."""

from __future__ import annotations

import base64
import fcntl
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

TIERS = {
    8: {"agent_workers": 1, "light": 1, "tabs": 1, "heavy": 1, "background": 0, "jobs": 1},
    16: {"agent_workers": 1, "light": 1, "tabs": 1, "heavy": 1, "background": 1, "jobs": 1},
    18: {"agent_workers": 1, "light": 1, "tabs": 1, "heavy": 1, "background": 1, "jobs": 1},
    24: {"agent_workers": 2, "light": 2, "tabs": 2, "heavy": 1, "background": 1, "jobs": 2},
    32: {"agent_workers": 2, "light": 2, "tabs": 2, "heavy": 1, "background": 1, "jobs": 2},
    36: {"agent_workers": 2, "light": 2, "tabs": 2, "heavy": 1, "background": 1, "jobs": 2},
    48: {"agent_workers": 2, "light": 2, "tabs": 2, "heavy": 1, "background": 1, "jobs": 2},
    64: {"agent_workers": 3, "light": 3, "tabs": 3, "heavy": 1, "background": 2, "jobs": 2},
    96: {"agent_workers": 4, "light": 4, "tabs": 4, "heavy": 2, "background": 3, "jobs": 3},
    128: {"agent_workers": 5, "light": 4, "tabs": 5, "heavy": 2, "background": 4, "jobs": 4},
}

HEAVY_PATTERN = re.compile(
    r"(?:^|[;&|()\s])(?:"
    r"npm|pnpm|yarn|bun|node|npx|cargo|rustc|pytest|python(?:3)?|uv|pip|"
    r"playwright|vitest|jest|next|vite|webpack|tsc|swift|xcodebuild|make|cmake|"
    r"gradle|gradlew|go|docker|podman|ollama|java"
    r")(?:\s|$)",
    re.IGNORECASE,
)
BACKGROUND_PATTERN = re.compile(r"(?<!&)&(?!&)|\bnohup\b", re.IGNORECASE)


def physical_memory_gib() -> float:
    override = os.environ.get("RAM_GUARD_MEMORY_GB")
    if override:
        try:
            return float(override)
        except ValueError:
            pass
    if sys.platform == "darwin":
        raw = subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip()
        return int(raw) / 1024**3
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        match = re.search(r"^MemTotal:\s+(\d+)\s+kB", meminfo.read_text(), re.MULTILINE)
        if match:
            return int(match.group(1)) * 1024 / 1024**3
    return 8.0


def select_tier(memory_gib: float) -> int:
    eligible = [tier for tier in TIERS if tier <= memory_gib]
    return max(eligible, default=8)


def policy() -> tuple[int, dict[str, int]]:
    tier = select_tier(physical_memory_gib())
    return tier, TIERS[tier]


def context_text(tier: int, limits: dict[str, int]) -> str:
    workers = limits["agent_workers"]
    agent_rule = (
        "Keep exactly one active Codex task; do not create or delegate to subagents."
        if workers == 1
        else f"Keep at most {workers} total active Codex workers, including the primary task."
    )
    return (
        f"RAM Guard is active for the {tier} GB tier. Machine responsiveness outranks speed. "
        f"{agent_rule} Run heavy workflows sequentially and cap build/test/browser internals at "
        f"{limits['jobs']} worker(s). Reuse one browser with at most {limits['tabs']} task-created tab(s), "
        "one package manager, one dev server, and existing caches/environments. Run focused checks first "
        "and one full verification near completion; never skip correctness checks to save memory. Stop "
        "task-created services after use. Under memory pressure, reduce to one worker and retry only the "
        "smallest failed check. The hook serializes recognized heavy shell commands, but you must still "
        "avoid parallel tool calls and duplicate non-shell tools."
    )


def emit(event: str, **values: Any) -> None:
    payload = {"hookSpecificOutput": {"hookEventName": event, **values}}
    print(json.dumps(payload, separators=(",", ":")))


def log_event(cwd: str, event: dict[str, Any]) -> None:
    configured = os.environ.get("RAM_GUARD_LOG")
    if configured:
        path = Path(configured)
    else:
        digest = hashlib.sha256(cwd.encode()).hexdigest()[:16]
        path = Path(tempfile.gettempdir()) / "ram-aware-agents" / f"{digest}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {"timestamp": time.time(), "cwd": cwd, **event}
    with path.open("a") as handle:
        handle.write(json.dumps(event, separators=(",", ":")) + "\n")


def contains_background_work(command: str) -> bool:
    return bool(BACKGROUND_PATTERN.search(command))


def is_heavy(command: str) -> bool:
    return bool(HEAVY_PATTERN.search(command))


def wrapper_command(command: str) -> str:
    encoded = base64.urlsafe_b64encode(command.encode()).decode()
    script = shlex.quote(str(Path(__file__).resolve()))
    return f"RAM_GUARD_WRAPPED=1 /usr/bin/python3 {script} run {shlex.quote(encoded)}"


def hook_main(payload: dict[str, Any]) -> int:
    event = payload.get("hook_event_name", "")
    tier, limits = policy()
    cwd = str(payload.get("cwd") or os.getcwd())
    if event in {"UserPromptSubmit", "SessionStart", "SubagentStart"}:
        log_event(cwd, {"event": event, "tier": tier, "action": "context"})
        emit(event, additionalContext=context_text(tier, limits))
        return 0
    if event != "PreToolUse" or payload.get("tool_name") != "Bash":
        return 0
    tool_input = payload.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0
    command = str(tool_input.get("command") or "")
    if not command or os.environ.get("RAM_GUARD_WRAPPED") == "1" or not is_heavy(command):
        return 0
    if contains_background_work(command):
        log_event(cwd, {"event": event, "tier": tier, "action": "deny-background", "command": command})
        emit(
            event,
            permissionDecision="deny",
            permissionDecisionReason=(
                "RAM Guard blocked a background heavy command. Run it in the foreground, reuse an existing "
                "managed service, or let the test runner own and clean up its child server."
            ),
        )
        return 0
    rewritten = wrapper_command(command)
    log_event(cwd, {"event": event, "tier": tier, "action": "rewrite-heavy", "command": command})
    emit(
        event,
        permissionDecision="allow",
        updatedInput={**tool_input, "command": rewritten},
        additionalContext=f"RAM Guard serialized this heavy command at the {tier} GB tier.",
    )
    return 0


def free_percent() -> int | None:
    if sys.platform != "darwin":
        return None
    try:
        output = subprocess.check_output(["memory_pressure", "-Q"], text=True, stderr=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None
    match = re.search(r"free percentage:\s*(\d+)%", output)
    return int(match.group(1)) if match else None


def worker_environment(jobs: int) -> dict[str, str]:
    value = str(jobs)
    return {
        "CARGO_BUILD_JOBS": value,
        "CMAKE_BUILD_PARALLEL_LEVEL": value,
        "MAKEFLAGS": f"-j{jobs}",
        "RAYON_NUM_THREADS": value,
        "SWIFTPM_MAXIMUM_CONCURRENT_JOBS": value,
        "UV_THREADPOOL_SIZE": value,
        "OMP_NUM_THREADS": value,
        "OPENBLAS_NUM_THREADS": value,
        "MKL_NUM_THREADS": value,
        "NUMEXPR_NUM_THREADS": value,
        "CI": "1",
    }


def run_serialized(encoded: str) -> int:
    command = base64.urlsafe_b64decode(encoded.encode()).decode()
    tier, limits = policy()
    pressure = free_percent()
    jobs = 1 if pressure is not None and pressure < 20 else limits["jobs"]
    cwd = os.getcwd()
    digest = hashlib.sha256(cwd.encode()).hexdigest()[:16]
    lock_path = Path(tempfile.gettempdir()) / "ram-aware-agents" / f"{os.getuid()}-{digest}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.update(worker_environment(jobs))
    started = time.monotonic()
    with lock_path.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        waited = time.monotonic() - started
        log_event(cwd, {"event": "run", "tier": tier, "action": "start", "jobs": jobs, "waited_seconds": waited, "free_percent": pressure, "command": command})
        shell = "/bin/zsh" if Path("/bin/zsh").exists() else "/bin/sh"
        completed = subprocess.run([shell, "-lc", command], env=environment)
        log_event(cwd, {"event": "run", "tier": tier, "action": "finish", "jobs": jobs, "exit_code": completed.returncode, "elapsed_seconds": time.monotonic() - started, "command": command})
        return completed.returncode


def main() -> int:
    if len(sys.argv) == 3 and sys.argv[1] == "run":
        return run_serialized(sys.argv[2])
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError) as error:
        print(f"RAM Guard received invalid hook input: {error}", file=sys.stderr)
        return 1
    return hook_main(payload)


if __name__ == "__main__":
    raise SystemExit(main())
