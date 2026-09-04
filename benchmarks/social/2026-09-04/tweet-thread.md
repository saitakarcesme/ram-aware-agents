# Copy-ready X/Twitter thread

## Post 1 — attach `01-browser-profile.png`

I tested whether RAM-aware instructions actually keep coding agents usable on an 8 GB M1 MacBook.

In 2 quality-valid browser pairs, AGENTS.md cut median P95 RSS by 57% and peak RSS by 59%, with a 5% median time cost.

Preliminary, but promising. 🧵

## Post 2

The first pilot was mixed: average RSS fell 31%, but peak RSS rose 3% and completion time rose 13%.

That failure forced a better protocol: fresh projects, alternating order, 1-second process-tree sampling, and independent correctness gates.

## Post 3 — attach `02-agents-vs-hook.png`

I then compared AGENTS.md with runtime enforcement.

In one quality-valid Rust triple, peak RSS fell 79.5% with AGENTS.md and 76.1% with the hook. The hook was 13.1% faster than AGENTS.md. Python gains were smaller, but the hook was again faster.

## Post 4

Conclusion: hooks do not replace AGENTS.md.

Use AGENTS.md for planning; add the hook for serialization and worker ceilings. Runs with an E2E failure were excluded—even when they used less RAM.

Data, profiles, skills + hook:
https://github.com/saitakarcesme/ram-aware-agents

## Standalone alternative — attach both graphics

Benchmarked RAM-aware coding-agent policies on an 8 GB M1. In 2 quality-valid browser pairs, AGENTS.md cut median P95 RSS 57% and peak RSS 59% at a 5% time cost. A hook kept Rust peak control with less overhead. Preliminary: https://github.com/saitakarcesme/ram-aware-agents
