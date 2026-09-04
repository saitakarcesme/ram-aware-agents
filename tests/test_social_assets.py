import csv
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "benchmarks" / "social" / "2026-09-04"


class SocialAssetTests(unittest.TestCase):
    def test_copy_ready_posts_fit_280_characters(self):
        content = (PACK / "tweet-thread.md").read_text(encoding="utf-8")
        sections = content.split("## ")[1:]
        self.assertGreaterEqual(len(sections), 5)
        for section in sections:
            title, body = section.split("\n", 1)
            self.assertLessEqual(len(body.strip()), 280, title)

    def test_claims_keep_preliminary_sample_counts(self):
        with (PACK / "claims.csv").open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        v2 = [row for row in rows if row["stage"] == "v2"]
        v3 = [row for row in rows if row["stage"] == "v3"]
        self.assertTrue(v2)
        self.assertTrue(v3)
        self.assertEqual({row["quality_valid_samples"] for row in v2}, {"2"})
        self.assertEqual({row["quality_valid_samples"] for row in v3}, {"1"})

    def test_shareable_png_and_editable_svg_pairs_exist(self):
        for stem in ("01-browser-profile", "02-agents-vs-hook"):
            for suffix in (".png", ".svg"):
                path = PACK / f"{stem}{suffix}"
                self.assertTrue(path.is_file(), path)
                self.assertGreater(path.stat().st_size, 1_000, path)


if __name__ == "__main__":
    unittest.main()
