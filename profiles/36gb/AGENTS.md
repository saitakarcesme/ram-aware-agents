# Performance Profile — 36 GB MacBook

Machine responsiveness has higher priority than finishing quickly. These limits are ceilings, not targets. Hardware verification status is documented in the repository README.

## Operating budget

- Keep one primary Codex task and at most 1 bounded independent subagent; never exceed 2 total active workers.
- Related writes and every heavy command remain sequential. Concurrent lightweight reads must stay within the limit below.
- Allow at most 2 simultaneous lightweight read-only operations.
- Keep at most 2 task-created browser tabs; reuse existing tabs.
- Run at most 1 top-level memory-heavy workflow. Builds, full tests, browser automation, containers, emulators, indexing, and local models are heavy.
- Limit internal parallelism inside any one build, test, data, or browser command to 2 workers.
- Keep at most 1 task-created background service, and stop each immediately after use.

## Required dependencies and correctness

- Required project dependencies may be installed when missing. Install them once, sequentially, into the project-local environment; do not confuse required dependencies with optional convenience tools.
- Do not skip, deselect, or weaken required tests because a dependency is missing. Install the declared dependency, use the repository's documented environment, or report a genuine blocker.
- Preserve requested dataset sizes, validation scope, and correctness checks. Lower resource use is not a win when the task is incomplete.
- Reuse the same project-local environment and exact command family for development and final verification.

## Tool-specific worker limits

When the project supports the option, apply the 2-worker ceiling explicitly instead of relying on machine defaults:

- Rust: `CARGO_BUILD_JOBS=2` and `cargo ... -j 2`.
- pnpm workspaces: `--workspace-concurrency=2`; install dependencies only once.
- Vitest: `--maxWorkers=2 --minWorkers=1`; Jest: `--maxWorkers=2`.
- Playwright: `--workers=2` and one managed web server; never start a duplicate server manually.
- Python: no pytest-xdist; application multiprocessing/worker pools default to 2. Use a larger pool only briefly when correctness explicitly requires comparing worker counts, then shut it down.
- Swift/Xcode: `swift ... --jobs 2` and `xcodebuild -jobs 2`.
- Make/Go/Gradle: `-j2`, `go ... -p 2`, or `--max-workers=2`.

If a flag is unsupported, use the tool's equivalent configuration. Do not add a new dependency merely to enforce a worker limit.

## Working method

- Start sequentially. Add permitted lightweight concurrency only when operations are independent and materially useful.
- Inspect narrowly with scoped `rg` or `rg --files`; exclude dependencies, build outputs, caches, `.git`, and generated data.
- Read only what is needed for the next decision. Inspect large files in chunks and avoid loading many images, PDFs, logs, or datasets into one turn.
- Make small changes and run the smallest relevant check first. Run full tests or a production build once near completion, not after every edit.
- Never overlap package installation, indexing, a full build, a full test suite, browser automation, or an emulator unless the heavy-workflow budget explicitly allows it.
- Reuse terminals, servers, environments, caches, browsers, containers, and worktrees. Do not duplicate them for convenience.
- Track every task-created background PID or managed service and clean it up before finishing.

## Memory-pressure fallback

Before and after a heavy command, check `memory_pressure -Q` and `sysctl vm.swapusage` when available. If free percentage falls below 20%, swap grows materially, the UI stutters, or a process is killed:

1. Stop optional/background work and close task-created browser tabs.
2. Return to one active worker and one heavy workflow, even if this tier permits more.
3. Reduce the tool's internal worker count and batch size by half, with a minimum of one.
4. Retry only the failed or smallest relevant check; do not repeat the same heavy command unchanged.
5. Report the limitation if correctness cannot be completed within the reduced budget.
