# Task-scoped RAM skills

These skills activate a RAM-aware execution budget for one task across the entire current project. Unlike files under `profiles/`, activating a skill does not write persistent project instructions.

| Agent | Skill | Project install | Personal install | Invoke |
|---|---|---|---|---|
| Codex | `codex-ram-profile` | `.agents/skills/codex-ram-profile/` | `~/.agents/skills/codex-ram-profile/` | `$codex-ram-profile` or `$codex-ram-profile 16` |
| Claude Code | `claude-ram-profile` | `.claude/skills/claude-ram-profile/` | `~/.claude/skills/claude-ram-profile/` | `/claude-ram-profile` or `/claude-ram-profile 16` |

Copy the complete skill directory so its detection script remains beside `SKILL.md`. When no RAM amount is supplied, the skill detects Mac unified memory with `sysctl`. Unlisted capacities use the next lower profile; values above 128 GB use the 128 GB ceiling.

The selected budget stays active for the current task and covers the full repository: agent fan-out, concurrent tool calls, browser tabs, heavy processes, background services, searches, builds, and tests.
