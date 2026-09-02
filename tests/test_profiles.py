from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_INTERNAL_JOBS = {8: 1, 16: 1, 18: 1, 24: 2, 32: 2, 36: 2, 48: 2, 64: 2, 96: 3, 128: 4}


class ProfileTests(unittest.TestCase):
    def test_generated_profiles_are_current(self) -> None:
        subprocess.run(["python3", "scripts/generate_profiles.py", "--check"], cwd=ROOT, check=True)

    def test_every_profile_pair_exists_and_has_worker_guidance(self) -> None:
        for tier, jobs in EXPECTED_INTERNAL_JOBS.items():
            for filename in ("AGENTS.md", "CLAUDE.md"):
                content = (ROOT / "profiles" / f"{tier}gb" / filename).read_text()
                self.assertIn(f"Limit internal parallelism inside any one build, test, data, or browser command to {jobs} worker", content)
                self.assertIn("Required project dependencies may be installed", content)
                self.assertIn("never mix npm, pnpm, Yarn, or Bun artifacts", content)
                self.assertIn("Do not skip, deselect, or weaken required tests", content)

    def test_skill_detectors_match(self) -> None:
        codex = ROOT / "skills" / "codex-ram-profile" / "scripts" / "detect_profile.sh"
        claude = ROOT / "skills" / "claude-ram-profile" / "scripts" / "detect_profile.sh"
        self.assertEqual(codex.read_bytes(), claude.read_bytes())
        for tier, jobs in EXPECTED_INTERNAL_JOBS.items():
            output = subprocess.check_output([str(codex), str(tier)], cwd=ROOT, text=True)
            values = dict(line.split("=", 1) for line in output.splitlines())
            self.assertEqual(values["profile"], f"{tier}gb")
            self.assertEqual(int(values["max_internal_jobs"]), jobs)

    def test_browser_workloads_have_independent_quality_gates(self) -> None:
        for workload_name in ("browser-e2e", "typescript-next"):
            path = ROOT / "benchmarks" / "v2" / "workloads" / f"{workload_name}.json"
            workload = json.loads(path.read_text())
            commands = workload["verify"]
            self.assertIn("pnpm typecheck", commands)
            self.assertIn("pnpm test", commands)
            self.assertIn("pnpm test:e2e", commands)
            self.assertIn("pnpm build", commands)
            self.assertIn("playwright.config.ts", workload["required_files"])
            self.assertIn("pnpm-lock.yaml", workload["required_files"])

    def test_plugin_workload_uses_declared_root_scripts(self) -> None:
        path = ROOT / "benchmarks" / "v2" / "workloads" / "plugin-docs.json"
        workload = json.loads(path.read_text())
        self.assertIn("npm run test:node", workload["verify"])
        self.assertIn("npm run build", workload["verify"])
        self.assertNotIn("--runInBand", " ".join(workload["verify"]))
        self.assertIn("scripts/test-python.sh", workload["required_files"])
        lockfile_choices = workload["required_any_files"][0]
        self.assertIn("package-lock.json", lockfile_choices)
        self.assertIn("node/package-lock.json", lockfile_choices)


if __name__ == "__main__":
    unittest.main()
