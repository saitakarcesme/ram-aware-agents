---
name: claude-ram-profile
description: Apply a RAM-aware, performance-first execution budget to the current Claude Code task across the entire project. Use when the user asks to activate a Mac RAM profile, reduce Claude Code resource use, prevent parallel work from slowing the Mac, or explicitly invokes this skill with an optional RAM amount.
---

# Claude RAM Profile

Apply one temporary execution budget to the whole current project for the rest of this task. This skill changes task behavior only; do not create, replace, or edit `CLAUDE.md`, settings, or project files merely to activate it.

## Select the budget

1. If the user supplied a RAM amount with the invocation, run `${CLAUDE_SKILL_DIR}/scripts/detect_profile.sh <GB>`.
2. Otherwise run `${CLAUDE_SKILL_DIR}/scripts/detect_profile.sh`. It detects Mac unified memory with `sysctl`.
3. If detection fails, use the 8 GB budget and briefly disclose the fallback.
4. State the selected tier once in a short progress update. Do not repeatedly announce it.

Treat the script output as ceilings, not targets:

- `max_workers` includes the main agent, subagents, and agent-team members combined.
- `max_light_calls` includes concurrent read-only searches, file reads, and other low-memory tools across all workers.
- `max_heavy_processes` covers builds, full test suites, dev servers, browser automation, containers, emulators, indexing, and local models across the whole project.
- `max_background_services` covers watchers, servers, emulators, containers, and other task-created persistent processes.
- `max_browser_tabs` covers all tabs created for this task.

## Operate within the budget

- Start sequentially even when the tier permits concurrency. Add concurrency only for independent work with a material benefit.
- Do not use subagents or agent teams when `max_workers=1`. Otherwise keep one primary task and never exceed the aggregate worker ceiling.
- Run related writes sequentially. Do not run two full builds or two full test suites together at any tier.
- Search with scoped `rg` or `rg --files`; exclude dependencies, build outputs, caches, `.git`, and generated files.
- Read only what is needed for the next decision. Chunk large files and avoid loading many images, PDFs, logs, or datasets together.
- Run the smallest relevant check first. Reserve full validation for the end unless the task specifically requires it earlier.
- Reuse existing terminals, servers, browser tabs, environments, and worktrees. Do not duplicate them for convenience.
- Do not enable optional plugins, MCP servers, containers, or local models unless the task requires them.
- Clean up task-created background processes and browser tabs before finishing.

Existing system, user, and project instructions still apply. When another instruction is stricter, follow the stricter limit. This skill does not expand permissions or authorize unrelated changes.

## Memory-pressure fallback

If the UI stutters, swap rises, memory-pressure warnings appear, or a process is killed, stop optional work, return to sequential execution, and drop to the next lower tier for the rest of the task. Retry only with smaller batches or a lighter command; do not repeat the same heavy action unchanged.
