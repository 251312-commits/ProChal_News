"""Regression checks for the single-viewport Game 1 result and modal graph."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "games/game1/result_screen"


class ResultMobileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (SCREEN / "index.html").read_text(encoding="utf-8")
        cls.css = (SCREEN / "result.css").read_text(encoding="utf-8")
        cls.js = (SCREEN / "result.js").read_text(encoding="utf-8")
        cls.host = (ROOT / "games/game1/result_reveal.py").read_text(encoding="utf-8")

    def test_result_controls_stay_inside_one_screen(self):
        self.assertLess(self.html.index('class="actions"'), self.html.index("</main>"))
        self.assertEqual(self.html.count("</main>"), 1)
        layout = self.css.split("/* Fixed-size, single-viewport result.", 1)[1]
        layout = layout.split("/* Separate, accessible", 1)[0]
        self.assertIn("position:fixed; inset:0", layout)
        self.assertIn("height:100dvh", layout)
        self.assertIn("grid-template-rows:auto auto auto minmax(0,1fr) auto auto", layout)
        self.assertIn("overflow:hidden; overscroll-behavior:none", layout)
        self.assertIn("orientation:landscape", layout)

    def test_score_explanation_is_not_inline_and_is_accessible(self):
        self.assertGreater(self.html.index('id="analysis-dialog"'), self.html.index("</main>"))
        self.assertIn('role="dialog" aria-modal="true"', self.html)
        self.assertIn('aria-controls="analysis-dialog" aria-expanded="false"', self.html)
        self.assertIn('class="analysis-close"', self.html)
        self.assertIn("ui.analysis.hidden = false", self.js)
        self.assertIn('event.key === "Escape"', self.js)
        self.assertIn("ui.analysisClose.focus", self.js)
        self.assertNotIn("scrollIntoView", self.js)
        self.assertIn(".analysis-body {", self.css)
        self.assertIn("overflow-y:auto", self.css)

    def test_model_chart_and_digit_comparison_use_stored_result(self):
        self.assertIn('class="sigmoid-chart"', self.html)
        self.assertIn('class="analysis-meter-fill"', self.html)
        self.assertIn('class="analysis-guess-digit"', self.html)
        self.assertIn('class="analysis-answer-digit"', self.html)
        self.assertIn("function drawScoreChart(model)", self.js)
        self.assertIn('ui.chartCurve.setAttribute("d"', self.js)
        self.assertIn("model.logit == null ? NaN", self.js)
        self.assertIn("model.normalized == null ? NaN", self.js)
        self.assertIn("ui.chartUnavailable.hidden = valid", self.js)
        self.assertIn("ui.analysisScore.textContent = wholeScore", self.js)
        self.assertIn("const wholeScore = (Number(data.units) / 100).toFixed(2)", self.js)
        self.assertIn("Boolean(data.matches[i])", self.js)
        self.assertIn("ui.analysisTitle.textContent", self.js)
        self.assertIn("ui.summary.textContent", self.js)
        self.assertNotIn(".innerHTML", self.js)

    def test_earlier_result_audio_and_private_balance_behavior_remain(self):
        for marker in (
            "song.currentTime", "spec.drop1 - 0.12", "spec.drop2 - 0.12",
            "playFailSound()", "requestAnimationFrame(tick)",
            "ui.wallet.hidden = true", 'ui.outcome.hidden = true',
            "if (!revealFinished || locked) return;",
        ):
            self.assertIn(marker, self.js)
        self.assertIn("html:has(.st-key-game1-result-reveal-screen)", self.host)
        self.assertIn("height:100dvh !important", self.host)


if __name__ == "__main__":
    unittest.main()
