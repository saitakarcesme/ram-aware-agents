#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TIERS = {
    8:   {"workers": 1, "light": 1, "tabs": 1, "heavy": 1, "background": 0, "jobs": 1},
    16:  {"workers": 1, "light": 1, "tabs": 1, "heavy": 1, "background": 1, "jobs": 1},
    18:  {"workers": 1, "light": 1, "tabs": 1, "heavy": 1, "background": 1, "jobs": 1},
    24:  {"workers": 2, "light": 2, "tabs": 2, "heavy": 1, "background": 1, "jobs": 2},
    32:  {"workers": 2, "light": 2, "tabs": 2, "heavy": 1, "background": 1, "jobs": 2},
    36:  {"workers": 2, "light": 2, "tabs": 2, "heavy": 1, "background": 1, "jobs": 2},
    48:  {"workers": 2, "light": 2, "tabs": 2, "heavy": 1, "background": 1, "jobs": 2},
    64:  {"workers": 3, "light": 3, "tabs": 3, "heavy": 1, "background": 2, "jobs": 2},
    96:  {"workers": 4, "light": 4, "tabs": 4, "heavy": 2, "background": 3, "jobs": 3},
    128: {"workers": 5, "light": 4, "tabs": 5, "heavy": 2, "background": 4, "jobs": 4},
}


def agent_budget(agent: str, workers: int) -> str:
    if workers == 1:
        return (
            f"- Keep exactly one active {agent} task. Do not create, fork, delegate to, or run subagents/agent teams.\n"
            "- Execute tool calls, writes, and shell commands sequentially. Never launch parallel tool calls."
        )
    return (
        f"- Keep one primary {agent} task and at most {workers - 1} bounded independent subagent"
        f"{'s' if workers - 1 != 1 else ''}; never exceed {workers} total active workers.\n"
        "- Related writes and every heavy command remain sequential. Concurrent lightweight reads must stay within the limit below."
    )


def render(tier: int, values: dict[str, int], filename: str) -> str:
    agent = "Codex" if filename == "AGENTS.md" else "Claude Code"
    jobs = values["jobs"]
    jest = "`--runInBand`" if jobs == 1 else f"`--maxWorkers={jobs}`"
    background = (
        "Do not leave a watcher or server running. A test runner may own one child server only for the duration of that command."
        if values["background"] == 0
        else f"Keep at most {values['background']} task-created background service{'s' if values['background'] != 1 else ''}, and stop each immediately after use."
    )
    return f"""# Performance Profile — {tier} GB MacBook

Machine responsiveness has higher priority than finishing quickly. These limits are ceilings, not targets. Hardware verification status is documented in the repository README.

## Operating budget

{agent_budget(agent, values['workers'])}
- Allow at most {values['light']} simultaneous lightweight read-only operation{'s' if values['light'] != 1 else ''}.
- Keep at most {values['tabs']} task-created browser tab{'s' if values['tabs'] != 1 else ''}; reuse existing tabs.
- Run at most {values['heavy']} top-level memory-heavy workflow{'s' if values['heavy'] != 1 else ''}. Builds, full tests, browser automation, containers, emulators, indexing, and local models are heavy.
- Limit internal parallelism inside any one build, test, data, or browser command to {jobs} worker{'s' if jobs != 1 else ''}.
- {background}

## Required dependencies and correctness

- Required project dependencies may be installed when missing. Install them once, sequentially, into the project-local environment; do not confuse required dependencies with optional convenience tools.
- Respect the repository's existing package manager and lockfile. In a new project, choose one package manager before installing dependencies and use it exclusively; never mix npm, pnpm, Yarn, or Bun artifacts.
- Do not skip, deselect, or weaken required tests because a dependency is missing. Install the declared dependency, use the repository's documented environment, or report a genuine blocker.
- Preserve requested dataset sizes, validation scope, and correctness checks. Lower resource use is not a win when the task is incomplete.
- Reuse the same project-local environment and exact command family for development and final verification.

## Tool-specific worker limits

When the project supports the option, apply the {jobs}-worker ceiling explicitly instead of relying on machine defaults:

- Rust: `CARGO_BUILD_JOBS={jobs}` and `cargo ... -j {jobs}`.
- pnpm workspaces: `--workspace-concurrency={jobs}`; install dependencies only once.
- Vitest: `--maxWorkers={jobs} --minWorkers=1`; Jest: {jest}.
- Playwright: `--workers={jobs}` and one managed web server; never start a duplicate server manually.
- Python: no pytest-xdist; application multiprocessing/worker pools default to {jobs}. Use a larger pool only briefly when correctness explicitly requires comparing worker counts, then shut it down.
- Swift/Xcode: `swift ... --jobs {jobs}` and `xcodebuild -jobs {jobs}`.
- Make/Go/Gradle: `-j{jobs}`, `go ... -p {jobs}`, or `--max-workers={jobs}`.

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
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changed = []
    for tier, values in TIERS.items():
        directory = ROOT / "profiles" / f"{tier}gb"
        for filename in ("AGENTS.md", "CLAUDE.md"):
            path = directory / filename
            content = render(tier, values, filename)
            if not path.exists() or path.read_text() != content:
                changed.append(str(path.relative_to(ROOT)))
                if not args.check:
                    path.write_text(content)
    if args.check and changed:
        print("Profiles need regeneration:")
        print("\n".join(changed))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
