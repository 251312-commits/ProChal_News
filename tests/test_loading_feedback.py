"""Regression checks for app-wide loading feedback."""
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from modules import loading_feedback


ROOT = Path(__file__).resolve().parents[1]


class LoadingFeedbackTests(TestCase):
    def test_render_has_unique_completion_token(self):
        with patch.object(loading_feedback.components, "html") as html:
            loading_feedback.render_loading_feedback()
            loading_feedback.render_loading_feedback()
        self.assertEqual(html.call_count, 2)
        first = html.call_args_list[0].args[0]
        second = html.call_args_list[1].args[0]
        self.assertNotEqual(first, second)
        self.assertIn("pcRunToken", first)
        self.assertIn("stFormSubmitButton", first)
        self.assertIn("pc:loading:start", first)
        self.assertEqual(html.call_args.kwargs["height"], 0)

    def test_app_footer_clears_after_page_router(self):
        app = (ROOT / "news.py").read_text(encoding="utf-8")
        self.assertGreater(app.rfind("render_loading_feedback()"),
                           app.rfind("show_game_5_tutorial()"))

    def test_dialog_fragment_renders_completion_hook(self):
        dialog = (ROOT / "views" / "badges.py").read_text(encoding="utf-8")
        self.assertIn("render_loading_feedback()", dialog)
        self.assertLess(dialog.index("render_loading_feedback()"),
                        dialog.index("def open_badge_gallery"))

    def test_custom_game_actions_report_start(self):
        for name in [
            "games/shared/news_slot/slot.js",
            "games/shared/article_reader/reader.js",
            "games/game1/prediction_screen/prediction.js",
            "games/game1/result_screen/result.js",
        ]:
            with self.subTest(name=name):
                self.assertIn('type: "pc:loading:start"',
                              (ROOT / name).read_text(encoding="utf-8"))
