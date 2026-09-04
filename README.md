# MacBook Agent Performance Profiles

Performance-first instruction files for running Codex and Claude Code on MacBooks without making the machine unpleasant to use.

Choose your unified-memory tier, then copy the matching file into your project:

| Memory | Codex | Claude Code | Operating style |
|---:|---|---|---|
| 8 GB | [`AGENTS.md`](profiles/8gb/AGENTS.md) | [`CLAUDE.md`](profiles/8gb/CLAUDE.md) | Strictly sequential, one heavy process |
| 16 GB | [`AGENTS.md`](profiles/16gb/AGENTS.md) | [`CLAUDE.md`](profiles/16gb/CLAUDE.md) | Sequential, targeted validation |
| 18 GB | [`AGENTS.md`](profiles/18gb/AGENTS.md) | [`CLAUDE.md`](profiles/18gb/CLAUDE.md) | Sequential, small batches |
| 24 GB | [`AGENTS.md`](profiles/24gb/AGENTS.md) | [`CLAUDE.md`](profiles/24gb/CLAUDE.md) | Mostly sequential, two light reads allowed |
| 32 GB | [`AGENTS.md`](profiles/32gb/AGENTS.md) | [`CLAUDE.md`](profiles/32gb/CLAUDE.md) | Limited concurrency |
| 36 GB | [`AGENTS.md`](profiles/36gb/AGENTS.md) | [`CLAUDE.md`](profiles/36gb/CLAUDE.md) | Limited concurrency |
| 48 GB | [`AGENTS.md`](profiles/48gb/AGENTS.md) | [`CLAUDE.md`](profiles/48gb/CLAUDE.md) | Two concurrent light operations |
| 64 GB | [`AGENTS.md`](profiles/64gb/AGENTS.md) | [`CLAUDE.md`](profiles/64gb/CLAUDE.md) | Conservative parallelism |
| 96 GB | [`AGENTS.md`](profiles/96gb/AGENTS.md) | [`CLAUDE.md`](profiles/96gb/CLAUDE.md) | Moderate, bounded parallelism |
| 128 GB | [`AGENTS.md`](profiles/128gb/AGENTS.md) | [`CLAUDE.md`](profiles/128gb/CLAUDE.md) | Bounded parallelism; usability still wins |

## Quick install

For Codex:

```sh
cp profiles/16gb/AGENTS.md /path/to/your-project/AGENTS.md
```

For Claude Code:

```sh
cp profiles/16gb/CLAUDE.md /path/to/your-project/CLAUDE.md
```

Replace `16gb` with your memory tier. If your exact capacity is not listed, choose the next lower tier. Commit the selected file if the whole team should use it; otherwise put it in your agent's user-level instruction location.

## Task-scoped skills

The repository also includes two reusable skills under [`skills/`](skills/README.md):

- [`codex-ram-profile`](skills/codex-ram-profile/SKILL.md) applies a temporary RAM budget to one Codex task across the entire project.
- [`claude-ram-profile`](skills/claude-ram-profile/SKILL.md) applies the same task-scoped approach in Claude Code.

Use `profiles/` when you want persistent project behavior. Use a skill when you want the selected budget only for the current task without changing the project's instruction files. Both skills detect Mac unified memory automatically or accept an explicit amount such as `16`.

Codex project installation:

```sh
cp -R skills/codex-ram-profile /path/to/project/.agents/skills/
```

Claude Code project installation:

```sh
cp -R skills/claude-ram-profile /path/to/project/.claude/skills/
```

## Runtime hook for Codex

[`hooks/codex-ram-guard/`](hooks/codex-ram-guard/README.md) is an experimental project hook that carries the same performance-first philosophy into the Codex lifecycle. Unlike an instruction file alone, it can rewrite recognized heavy Bash calls so they share a per-project lock, apply RAM-tier worker environment ceilings, and reject detached heavy commands. It injects a concise RAM budget before each prompt and for each starting subagent, then restores it after context compaction.

```sh
python3 hooks/codex-ram-guard/install.py /path/to/project
```

Review and trust the installed project hook with `/hooks`. Hook trust is intentionally hash-specific. The hook does not replace all planning guidance: current Codex hooks can advise a starting subagent but cannot cancel that start, and non-shell tools may remain outside hard enforcement. Based on the preliminary v3 evidence, `AGENTS.md` remains the default recommendation; add RAM Guard when runtime shell enforcement matters.

## What these profiles control

The profiles tell the coding agent to prefer machine responsiveness over wall-clock speed. They limit agent/subagent fan-out, parallel tool calls, browser tabs, background servers, watchers, broad filesystem scans, simultaneous builds, and oversized test runs. They also define a memory-pressure fallback.

Profiles also cap internal workers used by compilers, test runners, package managers, browser automation, and data-processing pools. They require one package manager and lockfile convention per project, unless the repository intentionally documents a mixed setup. Required project dependencies remain allowed and must not be replaced with skipped validation. All profile pairs are generated from [`scripts/generate_profiles.py`](scripts/generate_profiles.py) so Codex and Claude limits cannot drift silently.

These are behavioral instructions, not an operating-system resource limiter. An agent may fail to follow them, and a compiler, browser, container, local model, or plugin can still consume substantial memory. For hard limits, also use macOS Activity Monitor, container limits, tool-specific worker settings, and fewer enabled plugins/MCP servers.

## Design principles

- Keep one active coding-agent task by default.
- Prefer sequential work; use only the concurrency allowed by the chosen tier.
- Search narrowly with `rg`/`rg --files`; never scan the whole home directory by default.
- Run the smallest relevant test first and full validation once, near completion.
- Do not keep duplicate dev servers, watchers, browsers, or emulators alive.
- Inspect large files in chunks and avoid loading many images or documents at once.
- Stop optional work and reduce batch size when memory pressure or swap rises.
- Clean up background processes created for the task.

## Benchmark

The current three-arm evidence snapshot is under [`benchmarks/v3/evidence/8gb-m1-2026-09-04/`](benchmarks/v3/evidence/8gb-m1-2026-09-04/README.md). It compares unconstrained control, project `AGENTS.md`, and the Codex RAM Guard hook using fresh projects, five-prompt workloads, one-second sampling, rotating condition order, independent correctness gates, and hook telemetry.

One quality-valid Rust triple and one quality-valid Python triple show that both mechanisms reduced process-tree memory. Rust peak RSS fell from 1.607 GiB to 0.329 GiB with `AGENTS.md` and 0.383 GiB with the hook. Python P95 RSS fell from 0.288 GiB to 0.250 GiB and 0.253 GiB respectively. In both workloads the hook finished faster than `AGENTS.md`, but the sample size is below the protocol minimum and two browser-heavy triples were excluded because one arm failed independent E2E verification. The measured hook candidate also exposed duplicate context injection and tool-input preservation hardening, both fixed in the current unremeasured candidate.

The earlier profile/control evidence remains under [`benchmarks/v2/evidence/8gb-m1-2026-09-02/`](benchmarks/v2/evidence/8gb-m1-2026-09-02/README.md); its reproducible protocol and runner are documented in [`benchmarks/v2/`](benchmarks/v2/README.md).

In two quality-valid browser-heavy React/Playwright pairs, the 8 GB profile reduced median P95 Codex-tree RSS by 57.0%, median peak RSS by 58.9%, and browser process peaks from 22–24 to 7. Minimum free system memory improved from 32–49% to 55–60%. Median active-time delta was +5.0%, with large run-to-run variance. This is a strong signal, not a final universal claim: the protocol requires at least three valid pairs. In this evidence snapshot, Claude could not be measured because its local OAuth session required reauthentication; memory tiers above 8 GB have not been measured on physical hardware.

The earlier four-prompt pilot remains under [`benchmarks/codex-8gb-2026-09-01/`](benchmarks/codex-8gb-2026-09-01/README.md) for historical comparison. Benchmark defects discovered during the v2 runs led directly to stricter dependency, package-manager, worker-limit, E2E, and quality-gate rules.

The [`benchmarks/v3/`](benchmarks/v3/README.md) protocol, analyzer, evidence publisher, and minimal black-and-white SVG chart are reproducible. Local raw results stay ignored because they contain full generated source and agent event logs.

A consolidated analysis and copy-ready English social post pack are available under [`benchmarks/social/2026-09-04/`](benchmarks/social/2026-09-04/README.md). Its graphics use only quality-valid runs for headline comparisons and keep the pilot, excluded browser triples, sample-size limits, and unremeasured hook revision explicit.

## Sources

- [OpenAI: custom instructions with AGENTS.md](https://developers.openai.com/codex/guides/agents-md)
- [OpenAI: model guidance and lean tool orchestration](https://developers.openai.com/api/docs/guides/latest-model)
- [Anthropic: how Claude remembers your project](https://code.claude.com/docs/en/memory)
- [Anthropic: prompting guidance for parallel tool calls and subagents](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
- [OpenAI: build Codex skills](https://developers.openai.com/codex/skills)
- [OpenAI: Codex hooks](https://learn.chatgpt.com/docs/hooks)
- [Anthropic: extend Claude Code with skills](https://code.claude.com/docs/en/slash-commands)

## Contributing

Keep profiles measurable and self-contained. Changes should preserve the performance-first goal and should not claim that Markdown instructions enforce hard OS limits.

## License

MIT
