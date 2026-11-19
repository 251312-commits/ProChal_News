"""Game 4 mobile selector preserves range indices and uses existing assets."""

from pathlib import Path
from runpy import run_module
import sys
import unittest
from unittest.mock import MagicMock, patch


class GameFourPickerTests(unittest.TestCase):
    def setUp(self):
        self.st = MagicMock()
        self.ui = MagicMock()
        self.ui.load_local_image_url.return_value = "https://cdn.example.org/art.png"
        self.st.columns.side_effect = (
            lambda widths, **_kwargs: [MagicMock() for _ in widths]
        )
        modules = {
            "streamlit": self.st,
            "games.shared.betting": MagicMock(),
            "games.shared.news_flow": MagicMock(),
            "games.shared.loading": MagicMock(),
            "games.shared.interest": MagicMock(),
            "modules.transactions": MagicMock(),
            "modules.news_ai": MagicMock(),
            "modules.ui_components": self.ui,
            "views.ranking": MagicMock(),
        }
        with patch.dict(sys.modules, modules):
            self.picker = run_module("games.game4")["_render_game_4_range_picker"]

    def test_descending_display_preserves_scoring_index(self):
        ranges = ["70.00~71.99%", "72.00~73.99%", "74.00~75.99%"]
        self.st.radio.return_value = 0
        self.st.button.side_effect = lambda text, **_kwargs: "선택하기" in text

        chosen = self.picker(ranges, balance=1250)
        self.assertEqual(chosen, 0)

        args, kwargs = self.st.radio.call_args
        self.assertEqual(kwargs["options"], [2, 1, 0])
        self.assertEqual(kwargs["index"], 1)
        self.assertEqual(kwargs["key"], "game_4_range_picker")
        self.assertEqual(
            [kwargs["format_func"](index) for index in kwargs["options"]],
            [
                "**상위 구간**  \n(74.00~75.99%)",
                "**중간 구간**  \n(72.00~73.99%)",
                "**하위 구간**  \n(70.00~71.99%)",
            ],
        )

        markup = " ".join(
            call.args[0] for call in self.st.html.call_args_list
            if isinstance(call.args[0], str)
        )
        self.assertIn("1,250", markup)
        self.assertIn("cb-balance", markup)
        self.assertIn("cb-coin-symbol", markup)
        self.assertIn("cb-game-title", markup)
        self.assertIn("BET 로고", markup)
        self.assertIn("75.99%", markup)
        self.assertIn("70.00%", markup)
        self.assertIn("숨겨진 일치율", markup)
        self.assertNotIn("74.25%", markup)
        # Background/crown/coin/laurel assets are loaded, not duplicated.
        paths = [call.args[0] for call in self.ui.load_local_image_url.call_args_list]
        self.assertTrue(any(path.endswith("bet_background.jpg") for path in paths))
        self.assertTrue(any(path.endswith("bet_crown.png") for path in paths))
        self.assertEqual(len(paths), 4)

    def test_cancel_without_confirmation_does_not_select(self):
        self.st.button.return_value = False
        self.st.radio.return_value = 1
        chosen = self.picker(
            ["70.00~71.99%", "72.00~73.99%", "74.00~75.99%"], 2000
        )
        self.assertIsNone(chosen)

    def test_back_navigation_avoids_submitting_a_selection(self):
        self.st.button.side_effect = lambda _label, **kwargs: (
            kwargs.get("key") == "game4_picker_back"
        )
        chosen = self.picker(
            ["70.00~71.99%", "72.00~73.99%", "74.00~75.99%"], 2000
        )
        self.assertIsNone(chosen)
        self.ui.change_page.assert_called_once_with("main")
        self.st.radio.assert_not_called()

    def test_bank_navigation_leaves_selection_unset(self):
        self.st.button.side_effect = lambda _label, **kwargs: (
            kwargs.get("key") == "game4_picker_bank"
        )
        chosen = self.picker(
            ["70.00~71.99%", "72.00~73.99%", "74.00~75.99%"], 2000
        )
        self.assertIsNone(chosen)
        self.ui.change_page.assert_called_once_with("bank")
        self.st.radio.assert_not_called()

    def test_style_has_mobile_and_focus_rules(self):
        css = Path(__file__).resolve().parents[1] / "games" / "game4_picker.css"
        sheet = css.read_text(encoding="utf-8")
        self.assertIn("@media (max-width: 355px)", sheet)
        self.assertIn("label:focus-within", sheet)
        self.assertIn("label:has(input:checked)", sheet)
        self.assertIn("grid-template-columns: minmax(0,42%) minmax(0,1fr)", sheet)
        self.assertIn("padding: 24px 1px 24px 53px", sheet)
        self.assertIn("g4-reel-rotate", sheet)
        self.assertIn("prefers-reduced-motion: reduce", sheet)


if __name__ == "__main__":
    unittest.main()
