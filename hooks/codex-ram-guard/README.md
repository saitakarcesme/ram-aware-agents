# Codex RAM Guard hook

This project hook applies the repository's performance-first policy at runtime. It detects physical memory, selects the nearest conservative tier from 8 GB through 128 GB, injects a concise operating budget before each prompt and subagent start, restores the budget after context compaction, serializes recognized memory-heavy shell commands, sets common worker-limit environment variables, rejects background heavy commands, and records optional JSONL telemetry.

Install it from a clone of this repository:

```sh
python3 hooks/codex-ram-guard/install.py /path/to/project
```

Then open the target project in Codex, run `/hooks`, review the definition, and trust it. Project-local hooks do not run until both the project config layer and the current hook hash are trusted. Automation in a disposable, externally isolated repository may use `codex exec --dangerously-bypass-hook-trust` after independently vetting the hook source.

To test a lower tier on a larger machine, set `RAM_GUARD_MEMORY_GB`, for example:

```sh
RAM_GUARD_MEMORY_GB=8 codex
```

Set `RAM_GUARD_LOG=/absolute/path/events.jsonl` to retain hook decisions and serialized-command timings. Without it, telemetry is written under the system temporary directory and contains command text, so review it before sharing.

## Enforcement boundary

`PreToolUse` can rewrite or deny supported Bash calls, so recognized heavy commands receive real serialization and worker environment ceilings. Planning guidance and browser/subagent limits remain behavioral: Codex hooks can add context to a starting subagent, but cannot cancel that start. Tool-specific scripts may also ignore generic environment variables; keep explicit worker flags in project scripts when strict enforcement is required.

The hook never weakens validation, changes requested dataset sizes, or kills unrelated processes. A heavy command that tries to detach into the background is denied with a corrective message instead of being silently modified.

## When to use it

Use `AGENTS.md` as the broad default because it shapes planning across shell, browser, MCP, and subagent choices. Add RAM Guard when you also want recognized heavy Bash commands to be serialized at runtime. The preliminary [v3 benchmark](../../benchmarks/v3/evidence/8gb-m1-2026-09-04/README.md) shows strong peak control in Rust and comparable P95 RSS in Python, but it does not yet meet the minimum repetition count and does not justify replacing `AGENTS.md` universally.
