"""Game 1 result automatically starts without a separate music tap."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "games/game1/result_screen"

class AutostartTests(unittest.TestCase):
    def test_result_starts_when_component_receives_data(self):
        js = (ROOT / "result.js").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('  screen.hidden = false;\n  start();', js)
        self.assertNotIn('class="start primary"', html)
        self.assertNotIn('ui.start', js)
        self.assertIn("if (roundId !== data.round_id) setup(data)", js)

    def test_autoplay_denial_uses_visual_timeline_not_instant_skip(self):
        js = (ROOT / "result.js").read_text(encoding="utf-8")
        self.assertIn("silentMode = true", js)
        self.assertIn("(performance.now() - silentStart) / 1000", js)
        self.assertIn("song.currentTime", js)
        self.assertIn("spec.drop1 - 0.12", js)
        self.assertIn("spec.drop2 - 0.12", js)
        self.assertIn("if (!silentMode) playFailSound()", js)
        self.assertIn("ui.wallet.hidden = true", js)
        self.assertIn("ui.outcome.hidden = true", js)

if __name__ == "__main__":
    unittest.main()
