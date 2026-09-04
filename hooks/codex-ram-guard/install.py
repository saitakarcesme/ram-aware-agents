#!/usr/bin/env python3
"""Install RAM Guard into a Codex project."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the Codex RAM Guard project hook.")
    parser.add_argument("project", type=Path, help="Target project root")
    parser.add_argument("--force", action="store_true", help="Replace an existing .codex/hooks.json")
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    project = args.project.expanduser().resolve()
    if not project.is_dir():
        raise SystemExit(f"Project directory does not exist: {project}")
    codex = project / ".codex"
    hook_dir = codex / "hooks"
    config = codex / "hooks.json"
    if config.exists() and not args.force:
        raise SystemExit(f"Refusing to replace {config}; merge the hook definition or pass --force")
    hook_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / "ram_guard.py", hook_dir / "ram_guard.py")
    shutil.copy2(source / "hooks.json", config)
    print(f"Installed RAM Guard in {codex}")
    print("Review and trust the project hook with /hooks before relying on it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
