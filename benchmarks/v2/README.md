# RAM-aware agent benchmark protocol v2

This suite tests whether project-level RAM profiles keep a Mac responsive without hiding failures or reducing task quality. Every measurement case starts from a new Git repository and a new agent session. Profile and control cases receive the same locked five-prompt workload.

## Workloads

| Workload | Stack | Split |
|---|---|---|
| `typescript-next` | TypeScript, Next.js, Vitest, Playwright | tuning |
| `python-data` | Python, FastAPI, streaming ETL, pytest | tuning |
| `rust-workspace` | Rust multi-crate workspace | tuning |
| `swift-macos` | Swift concurrency and macOS package | holdout |
| `browser-e2e` | React and browser-heavy Playwright suite | tuning |
| `large-refactor` | 2,000-module TypeScript repository | holdout |
| `plugin-docs` | Python and TypeScript document plugin | tuning |
| `docker-services` | Docker Compose multi-service system | tuning |

Holdout workloads must not influence profile edits. They are used only after a candidate profile is locked.

## Measurement contract

The runner samples the complete agent process tree and macOS once per second. It records average, P95, and peak RSS; system memory; free-memory pressure; swap growth; process counts; browser process counts; and a process-launch responsiveness probe. It also runs workload-owned verification commands after the agent finishes and records background processes whose command lines still reference the project.

The profile is a success only when resource improvements survive correctness gates. A run that skips required data sizes, fails verification, or leaks a task-created process is not counted as a memory win.

## Repetition policy

- Diagnostic stage: at least three profile/control pairs per available workload and agent.
- Ambiguous cells: expand to five and then seven pairs.
- Condition order alternates by repetition to reduce cache/order bias.
- Profile tuning uses only the tuning split.
- Final validation uses a locked candidate and at least five pairs, including both holdouts.

This machine can validate only its physical memory tier. Results for unavailable RAM tiers must be labeled unverified rather than extrapolated as measured facts.

## Usage

Run preflight first:

```sh
python3 benchmarks/v2/harness/preflight.py
```

Preflight returns success when at least one supported agent is authenticated and disk space is sufficient. Unavailable optional agents and workloads (for example Claude or Docker) remain listed in its JSON output and are skipped or selected explicitly by the runner.

Run one paired pilot:

```sh
python3 benchmarks/v2/harness/runner.py \
  --agent codex \
  --workload python-data \
  --repetitions 1
```

The default local result directory is ignored by Git because it contains full agent event logs and generated verification output. Curated summaries and privacy-reviewed samples can be published after analysis.

## Safety and isolation

The runner uses fresh temporary directories, isolated Codex configuration with only the existing authentication file linked, empty MCP configuration, no Claude Chrome integration, and sequential cases. It removes only temporary projects it created. Agent sandbox/permission bypass is limited to those disposable benchmark repositories; do not point the harness at an existing project.
