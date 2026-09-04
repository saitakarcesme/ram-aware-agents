# AGENTS.md versus hook benchmark protocol v3

This suite compares three ways of running the same five-prompt project on the same machine:

1. `control`: no RAM-aware project policy.
2. `profile`: the existing 8 GB `AGENTS.md` profile.
3. `hook`: no `AGENTS.md`; the Codex RAM Guard project hook injects the budget and enforces serialized heavy Bash commands.

Every arm starts from a fresh Git repository and a fresh Codex session. The locked v2 workloads, independent verification commands, one-second process-tree/system sampling, process-leak checks, and dataset-size requirements remain unchanged. Condition order rotates across repetitions to reduce first-run and cache bias. A comparison counts only when all three arms pass the same quality gates.

## Run

Preflight uses the existing workload checks:

```sh
python3 benchmarks/v2/harness/preflight.py
```

Run a one-repetition smoke benchmark first:

```sh
python3 benchmarks/v3/harness/runner.py \
  --agent codex \
  --workload browser-e2e \
  --repetitions 1 \
  --results benchmarks/v3/results/pilot
```

Run the minimum diagnostic set:

```sh
python3 benchmarks/v3/harness/runner.py \
  --agent codex \
  --workload browser-e2e \
  --workload python-data \
  --workload rust-workspace \
  --repetitions 3 \
  --results benchmarks/v3/results/diagnostic
```

Analyze quality-valid triples and render the black-and-white comparison chart:

```sh
python3 benchmarks/v3/harness/analyze.py \
  --results benchmarks/v3/results/diagnostic \
  --output benchmarks/v3/results/diagnostic-analysis
```

Local results are ignored because raw agent logs can contain generated source and command text. Publish only privacy-reviewed evidence snapshots.

Create a compact evidence snapshot without copying raw logs:

```sh
python3 benchmarks/v3/harness/publish.py \
  --results benchmarks/v3/results/diagnostic \
  --output benchmarks/v3/evidence/my-machine-date \
  --date YYYY-MM-DD
```

The current published tuning snapshot is [`evidence/8gb-m1-2026-09-04/`](evidence/8gb-m1-2026-09-04/README.md). It contains one quality-valid Rust triple, one quality-valid Python triple, two excluded browser diagnostics, CSV data, and a dependency-free SVG chart. It is preliminary because no workload yet reaches the required three quality-valid triples.

## Interpretation

The hook has a stronger enforcement boundary for recognized Bash commands, but it cannot guarantee browser-tab limits, cancel a subagent at `SubagentStart`, or constrain tools that ignore generic worker environment variables. `AGENTS.md` can shape planning earlier and across more tool types, but compliance is behavioral. The benchmark therefore reports quality, time, process-tree RSS, system memory pressure, responsiveness, process/browser counts, leaks, and hook telemetry together; memory alone does not decide the winner.

The current evidence supports `AGENTS.md` as the default broad mechanism and RAM Guard as optional shell enforcement. This is a provisional recommendation, not a universal conclusion.
