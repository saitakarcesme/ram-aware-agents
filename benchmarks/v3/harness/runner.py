#!/usr/bin/env python3
"""Run the v3 control/AGENTS.md/hook benchmark using the hardened v2 engine."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
V3 = ROOT / "benchmarks" / "v3"
ENGINE_PATH = ROOT / "benchmarks" / "v2" / "harness" / "runner.py"
SPEC = importlib.util.spec_from_file_location("ram_benchmark_v2_runner", ENGINE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load benchmark engine: {ENGINE_PATH}")
ENGINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ENGINE)
ENGINE.V2 = V3
ENGINE.WORKLOADS = ROOT / "benchmarks" / "v2" / "workloads"
ENGINE.PROTOCOL = json.loads((V3 / "protocol.json").read_text())


if __name__ == "__main__":
    raise SystemExit(ENGINE.main())
