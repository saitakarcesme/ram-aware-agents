from __future__ import annotations

import base64
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
GUARD_PATH = ROOT / "hooks" / "codex-ram-guard" / "ram_guard.py"
SPEC = importlib.util.spec_from_file_location("ram_guard", GUARD_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Cannot load {GUARD_PATH}")
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)
PROFILE_SPEC = importlib.util.spec_from_file_location("generate_profiles", ROOT / "scripts" / "generate_profiles.py")
if PROFILE_SPEC is None or PROFILE_SPEC.loader is None:
    raise RuntimeError("Cannot load profile generator")
PROFILES = importlib.util.module_from_spec(PROFILE_SPEC)
PROFILE_SPEC.loader.exec_module(PROFILES)


class RamGuardTests(unittest.TestCase):
    def test_tier_selection_is_conservative(self) -> None:
        self.assertEqual(GUARD.select_tier(8), 8)
        self.assertEqual(GUARD.select_tier(15.9), 8)
        self.assertEqual(GUARD.select_tier(18), 18)
        self.assertEqual(GUARD.select_tier(256), 128)

    def test_heavy_classification_avoids_read_only_shell(self) -> None:
        self.assertTrue(GUARD.is_heavy("pnpm test"))
        self.assertTrue(GUARD.is_heavy("cargo build --release"))
        self.assertFalse(GUARD.is_heavy("rg --files src"))
        self.assertFalse(GUARD.is_heavy("git status --short"))

    def test_background_detection_does_not_confuse_and_operator(self) -> None:
        self.assertTrue(GUARD.contains_background_work("pnpm dev &"))
        self.assertTrue(GUARD.contains_background_work("nohup npm start"))
        self.assertFalse(GUARD.contains_background_work("pnpm install && pnpm test"))

    def test_pretool_rewrite_is_valid_hook_output(self) -> None:
        payload = {
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "cwd": "/tmp/ram-guard-test",
            "tool_input": {"command": "pnpm test", "timeout_ms": 120000},
        }
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {"RAM_GUARD_MEMORY_GB": "8", "RAM_GUARD_LOG": str(Path(directory) / "events.jsonl")},
            clear=False,
        ):
            completed = subprocess.run(
                ["python3", str(GUARD_PATH)],
                input=json.dumps(payload),
                text=True,
                stdout=subprocess.PIPE,
                check=True,
            )
        output = json.loads(completed.stdout)
        specific = output["hookSpecificOutput"]
        self.assertEqual(specific["hookEventName"], "PreToolUse")
        self.assertEqual(specific["permissionDecision"], "allow")
        rewritten = specific["updatedInput"]["command"]
        self.assertEqual(specific["updatedInput"]["timeout_ms"], 120000)
        self.assertIn("RAM_GUARD_WRAPPED=1", rewritten)
        encoded = rewritten.rsplit(" ", 1)[1]
        self.assertEqual(base64.urlsafe_b64decode(encoded).decode(), "pnpm test")

    def test_serialized_runner_applies_one_worker_environment(self) -> None:
        command = (
            "test \"$CARGO_BUILD_JOBS\" = 1 && test \"$RAYON_NUM_THREADS\" = 1 "
            "&& test \"$CI\" = 1"
        )
        encoded = base64.urlsafe_b64encode(command.encode()).decode()
        with tempfile.TemporaryDirectory() as directory, patch.dict(
            os.environ,
            {"RAM_GUARD_MEMORY_GB": "8", "RAM_GUARD_LOG": str(Path(directory) / "events.jsonl")},
            clear=False,
        ):
            self.assertEqual(GUARD.run_serialized(encoded), 0)

    def test_hook_config_has_one_synchronous_handler_per_event(self) -> None:
        config = json.loads((ROOT / "hooks" / "codex-ram-guard" / "hooks.json").read_text())
        self.assertEqual(set(config["hooks"]), {"SessionStart", "UserPromptSubmit", "SubagentStart", "PreToolUse"})
        for groups in config["hooks"].values():
            self.assertEqual(len(groups), 1)
            self.assertEqual(len(groups[0]["hooks"]), 1)
            self.assertNotIn("async", groups[0]["hooks"][0])
        self.assertEqual(config["hooks"]["SessionStart"][0]["matcher"], "compact")

    def test_hook_worker_tiers_match_generated_profiles(self) -> None:
        self.assertEqual(set(GUARD.TIERS), set(PROFILES.TIERS))
        for tier, expected in PROFILES.TIERS.items():
            actual = GUARD.TIERS[tier]
            self.assertEqual(actual["agent_workers"], expected["workers"])
            for key in ("light", "tabs", "heavy", "background", "jobs"):
                self.assertEqual(actual[key], expected[key])


if __name__ == "__main__":
    unittest.main()
