# Copy-ready reply tweet

## Main reply — attach `03-hook-vs-agents-deltas.png`

Good question—I benchmarked it. On an 8 GB M1, the hook was 8.8% faster than AGENTS.md in Python and 13.1% faster in Rust. Peak RAM was mixed: −8.9% in Python, +16.7% in Rust. My take: AGENTS.md for planning, hooks for enforcement. Preliminary: n=1/stack.

## Optional follow-up — attach `04-hook-vs-agents-tradeoff.png`

Why not hook-only? Hooks enforce shell serialization and worker ceilings, while AGENTS.md shapes planning across tools. Hooks cannot cancel subagent starts. I excluded browser triples when any arm failed E2E.

Data: https://github.com/saitakarcesme/ram-aware-agents
