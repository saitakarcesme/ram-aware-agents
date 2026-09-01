# Performance Profile — 8 GB MacBook

Machine responsiveness has higher priority than finishing quickly.

## Hard operating budget

- Keep exactly one active Codex task. Do not create, fork, or delegate to subagents.
- Execute tool calls and shell commands sequentially. Never launch parallel calls.
- Keep at most one browser tab opened by the task and reuse it.
- Run only one memory-heavy process at a time: build, test runner, dev server, browser automation, container, emulator, or local model.
- Do not start watchers. Use one-shot commands. Stop task-created background processes immediately after use.

## Working method

- Inspect narrowly. Use `rg` or `rg --files` with a scoped path; exclude dependencies, build outputs, caches, `.git`, and generated files.
- Read only the files needed for the next decision. Read large files in chunks and avoid loading multiple images, PDFs, or datasets together.
- Make one small change, run the smallest relevant check, then continue. Run a full test/build once near completion only when required.
- Never run package installation, indexing, full tests, and a dev server at the same time.
- Reuse an existing terminal and server. Do not open duplicate tabs, windows, worktrees, containers, or IDE instances.
- Prefer existing tools and dependencies. Do not install optional tools or enable plugins merely for convenience.

## Memory-pressure fallback

If the UI stutters, swap rises, memory-pressure warnings appear, or a command is killed: stop optional/background work, close task-created browser tabs, reduce the batch size, and continue sequentially. Report the limitation instead of retrying the same heavy command unchanged.
