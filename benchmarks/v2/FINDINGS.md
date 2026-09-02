# Benchmark findings and profile decisions

This log separates measured evidence from profile hypotheses. A result is counted only when both profile and control projects pass the independent quality gate.

## Baseline profile

- Profile commit: `0ff1af2`
- 8 GB Codex profile SHA-256: `122f19bf00f42382a2b99354b30f23f3a7b1977c3a00c5cfa3ec860c527c0d98`
- Machine: MacBook Air M1, 8 GB unified memory
- Codex: 0.144.6, `gpt-5.6-terra`, medium effort

### Python data workload

Five pairs ran. The first pair is excluded because the original verifier used system Python for a control project whose dependencies were correctly installed in `.venv`. The verifier was corrected and now rejects skipped/deselected tests.

Across four valid pairs, the baseline profile was inconsistent:

| Metric | Median profile delta | Observed range |
|---|---:|---:|
| Active time | +2.2% | -17.7% to +16.7% |
| Average agent-tree RSS | +2.2% | -1.3% to +6.4% |
| P95 agent-tree RSS | +0.5% | -8.5% to +13.6% |
| Peak agent-tree RSS | +2.2% | -26.1% to +22.0% |
| Peak system used memory | -0.3% | -5.1% to +1.3% |
| Responsiveness probe P95 | +0.6% | -7.9% to +5.5% |

The first profile project also interpreted “do not install optional tools” as prohibiting a required FastAPI dependency and skipped the API test. The locked workload now requires a project-local environment and rejects skips. The profile must explicitly distinguish required dependencies from optional convenience tools.

### Rust workspace workload

Two valid pairs ran in opposite orders.

| Metric | Median profile delta | Observed range |
|---|---:|---:|
| Active time | +3.7% | -7.8% to +15.2% |
| Average agent-tree RSS | -9.4% | -12.3% to -6.4% |
| P95 agent-tree RSS | -7.4% | -10.9% to -3.9% |
| Peak agent-tree RSS | +19.5% | -16.1% to +55.2% |
| Peak system used memory | +14.2% | +11.3% to +17.0% |

When the profile condition ran first, its process tree peaked at 23 processes versus 9 for control. Reversing the order produced 9 for both. The general “one heavy process” rule does not constrain a compiler's internal jobs and is sensitive to cache/order effects.

### Claude status

The harness reached Claude Code 2.1.220, but the first real API request failed because the stored OAuth session had expired. Reauthentication reached Google phone verification and was stopped for user action. No Claude performance result is reported.

## Candidate v2 changes

The candidate profile adds:

- explicit permission to install required declared dependencies once in a project-local environment;
- a prohibition on treating skipped validation as successful completion;
- a tier-specific `max_internal_jobs` budget;
- concrete worker flags for Cargo, pnpm, Vitest, Jest, Playwright, Python pools, Swift/Xcode, Make, Go, and Gradle;
- one managed Playwright server and no manually duplicated server;
- before/after heavy-command memory-pressure checks and a deterministic fallback sequence;
- generated Codex/Claude profile pairs to prevent content drift.

## Candidate v2 tuning results

### Browser-heavy React and Playwright

Three paired repetitions ran after the browser quality gate was expanded to independently execute typecheck, component tests, the complete E2E script, and the production build. Two pairs were quality-valid. Each valid project passed 80 Playwright cases across desktop and mobile.

| Metric | Median profile delta | Observed range |
|---|---:|---:|
| Active time | +5.0% | -21.5% to +31.5% |
| Average agent-tree RSS | -40.6% | -67.2% to -13.9% |
| P95 agent-tree RSS | -57.0% | -65.3% to -48.7% |
| Peak agent-tree RSS | -58.9% | -64.2% to -53.7% |
| Peak system used memory | -9.7% | -13.3% to -6.1% |
| Responsiveness probe P95 | -61.5% | -63.9% to -59.1% |

Profile projects peaked at 13–15 processes and 7 browser processes; controls peaked at 26–30 and 22–24. Minimum free memory was 55–60% with the profile and 32–49% without it.

The excluded pair mixed npm-installed modules with pnpm verification. That exposed an instruction gap rather than a memory regression. Every generated profile and both task skills now require package-manager and lockfile consistency; the browser workload is explicitly pnpm-only.

### Rust and Python candidate snapshot

Two quality-valid Rust candidate pairs reduced peak agent-tree RSS by a median 28.7% and reduced process peaks from 7/10 to 6/6. P95 RSS was nearly flat at +2.8%, so more repetitions are required.

One quality-valid Python candidate pair reduced peak RSS by 20.3% but increased active time by 17.9% and average RSS by 7.1%. It is inconclusive and is not a basis for a broad benefit claim.

### Harness defects found by adversarial validation

- Browser verification originally omitted the E2E command. It now runs `typecheck`, component tests, E2E, and build independently and requires the lockfile and Playwright configuration.
- Plugin-docs verification appended a Jest-only flag to a Vitest project and assumed a root `test` script that the workload did not require. The workload now declares portable `test:node` and `build` root contracts.
- Preflight originally failed when either optional agent was logged out. It now succeeds when at least one supported agent is authenticated and reports unavailable agents/workloads without blocking unrelated runs.

The privacy-reviewed evidence snapshot and minimal chart are in [`evidence/8gb-m1-2026-09-02/`](evidence/8gb-m1-2026-09-02/README.md).

## Current validation boundary

- Direct performance evidence exists only for Codex on the physical 8 GB M1 machine.
- Claude remains blocked on user reauthentication; no Claude performance claim is made.
- Docker remains unavailable because the daemon is stopped.
- The browser result is a strong signal but has only two independently quality-valid pairs; the protocol requires a third before the `profile-benefit` label.
- Holdout workloads remain unreported until the updated candidate completes the tuning repetition requirement.
