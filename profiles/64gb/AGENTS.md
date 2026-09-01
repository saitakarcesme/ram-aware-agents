# Performance Profile — 64 GB MacBook

Machine responsiveness has higher priority than finishing quickly. Treat the limits below as ceilings, not targets.

## Operating budget

- Keep one primary Codex task. Use at most two subagents for genuinely independent workstreams; total active workers must not exceed three.
- Allow at most three concurrent lightweight read-only operations. Writes and heavy operations remain sequential unless concurrency is essential for correctness.
- Keep at most 3 task-created browser tabs open and reuse existing tabs.
- Run one memory-heavy process at a time. Do not overlap full builds, full tests, containers, emulators, or browser automation. Heavy work includes builds, full test suites, dev servers, browser automation, containers, emulators, indexing, and local models.
- Keep at most two background services in total and stop each as soon as it is no longer needed.

## Working method

- Start sequentially. Add permitted concurrency only when operations are independent and the expected benefit is material.
- Inspect narrowly with `rg` or `rg --files` and scoped paths. Exclude dependencies, build outputs, caches, `.git`, and generated files.
- Read only what is needed for the next decision. Inspect large files in chunks; avoid loading many images, PDFs, logs, or datasets into one turn.
- Make small changes and run the smallest relevant check first. Run full tests or a production build once near completion, not after every edit.
- Do not combine package installation, indexing, full validation, browser automation, and a development server unless the operating budget explicitly permits it.
- Reuse existing terminals, servers, environments, and worktrees. Do not create duplicates for convenience.
- Prefer installed tools and existing dependencies. Do not enable extra plugins, MCP servers, containers, or local models unless required by the task.
- Clean up task-created background processes, temporary servers, and browser tabs before finishing.

## Memory-pressure fallback

If the UI stutters, swap rises, memory-pressure warnings appear, or a process is killed: stop optional/background work, return to fully sequential execution, close task-created tabs, reduce batch and worker counts, and retry only with a lighter command. Report the limitation instead of repeating the same resource-heavy action unchanged.
