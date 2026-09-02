#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
WORKLOADS = ROOT / "benchmarks" / "v2" / "workloads"


def succeeds(command: list[str]) -> bool:
    return subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def main() -> int:
    total_memory = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True))
    disk = shutil.disk_usage(ROOT)
    checks = {
        "memory_gib": round(total_memory / 1024**3, 2),
        "disk_free_gib": round(disk.free / 1024**3, 2),
        "codex_authenticated": succeeds(["codex", "login", "status"]),
        "claude_authenticated": succeeds(["claude", "auth", "status"]),
        "docker_daemon": succeeds(["docker", "info"]),
        "commands": {},
        "workloads": {},
    }
    commands = sorted(
        {command for path in WORKLOADS.glob("*.json") for command in json.loads(path.read_text()).get("capability", [])}
    )
    checks["commands"] = {command: shutil.which(command) is not None for command in commands}
    for path in sorted(WORKLOADS.glob("*.json")):
        workload = json.loads(path.read_text())
        missing = [command for command in workload.get("capability", []) if not checks["commands"].get(command)]
        reason = "available"
        available = not missing
        if missing:
            reason = "missing: " + ", ".join(missing)
        elif workload.get("requires_docker_daemon") and not checks["docker_daemon"]:
            available = False
            reason = "Docker daemon unavailable"
        checks["workloads"][workload["id"]] = {"available": available, "reason": reason}
    print(json.dumps(checks, indent=2))
    # Optional agents and workloads must remain visible without blocking an
    # otherwise runnable suite. The selected runner performs its own agent and
    # capability checks before creating a case.
    required = (checks["codex_authenticated"] or checks["claude_authenticated"]) and checks["disk_free_gib"] >= 20
    return 0 if required else 1


if __name__ == "__main__":
    raise SystemExit(main())
