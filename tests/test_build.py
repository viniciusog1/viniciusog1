import re
import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build  # noqa: E402

DATA = {p[0]: {"pushed": "2026-07-10T19:20:11Z", "languages": {"Python": 90, "Shell": 10}, "ci": True}
        for p in build.PROJECTS}


def run(status, conclusion):
    return {"name": "CI", "status": status, "conclusion": conclusion}


class BuildTest(unittest.TestCase):
    def test_every_svg_is_valid_xml(self):
        for name, svg in build.build(DATA).items():
            with self.subTest(name):
                ET.fromstring(svg)

    def test_readme_uses_exactly_the_generated_assets(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        used = set(re.findall(r"assets/([\w-]+\.svg)", readme))
        self.assertEqual(used, set(build.build(DATA)))

    def test_ci_status_uses_latest_finished_run(self):
        self.assertTrue(build.ci_passing([run("in_progress", None), run("completed", "success")]))
        self.assertFalse(build.ci_passing([run("completed", "failure"), run("completed", "success")]))
        self.assertFalse(build.ci_passing([]))

    def test_failing_ci_shows_no_badge(self):
        card = build.card("X", "t", [], {**DATA["vox"], "ci": False}, build.THEMES["dark"])
        self.assertNotIn("CI passing", card)

    def test_empty_language_list(self):
        self.assertEqual(build.shares({}), [])


if __name__ == "__main__":
    unittest.main()
