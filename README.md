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

## What these profiles control

The profiles tell the coding agent to prefer machine responsiveness over wall-clock speed. They limit agent/subagent fan-out, parallel tool calls, browser tabs, background servers, watchers, broad filesystem scans, simultaneous builds, and oversized test runs. They also define a memory-pressure fallback.

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

The first controlled comparison is published under [`benchmarks/codex-8gb-2026-09-01/`](benchmarks/codex-8gb-2026-09-01/README.md). It uses two clean projects and the same four-prompt Codex workload. In this single run, the 8 GB profile reduced average Codex-tree RSS by 30.7% and P95 RSS by 18.0%, while taking 13.3% longer. It did not reduce the absolute peak Codex-tree RSS, which was 3.2% higher. See the report for the charts, raw one-second samples, method, and limitations.

## Sources

- [OpenAI: custom instructions with AGENTS.md](https://developers.openai.com/codex/guides/agents-md)
- [OpenAI: model guidance and lean tool orchestration](https://developers.openai.com/api/docs/guides/latest-model)
- [Anthropic: how Claude remembers your project](https://code.claude.com/docs/en/memory)
- [Anthropic: prompting guidance for parallel tool calls and subagents](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
- [OpenAI: build Codex skills](https://learn.chatgpt.com/docs/build-skills)
- [Anthropic: extend Claude Code with skills](https://code.claude.com/docs/en/slash-commands)

## Contributing

Keep profiles measurable and self-contained. Changes should preserve the performance-first goal and should not claim that Markdown instructions enforce hard OS limits.

## License

MIT
