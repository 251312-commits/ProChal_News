"""Regression tests for the Game 1 casino-style prediction picker."""
from contextlib import nullcontext
from html import escape
from pathlib import Path
from runpy import run_module
import sys
import unittest
from unittest.mock import MagicMock, patch


class Session(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class RerunRequested(Exception):
    pass


class FakeStreamlit:
    def __init__(self, **state):
        self.session_state = Session(state)
        self.clicked = None
        self.markup = []
        self.rerun_scope = None

    @staticmethod
    def fragment(fn):
        return fn

    @staticmethod
    def container(*args, **kwargs):
        return nullcontext()

    def button(self, label, *, key, **kwargs):
        return key == self.clicked

    def html(self, value):
        self.markup.append(str(value))

    def rerun(self, scope=None):
        self.rerun_scope = scope
        raise RerunRequested()


class PredictionPickerTests(unittest.TestCase):
    def setUp(self):
        self.st = FakeStreamlit(current_user_data={"코인": 1250})
        self.ui = MagicMock()
        with patch.dict(sys.modules, {
            "streamlit": self.st, "modules.ui_components": self.ui,
        }):
            env = run_module("games.game1_prediction_ui")
        self.picker = env["render_game1_prediction_picker"]
        self.change_digit = env["_change_digit"]
        # Renderer works without disk access; physical image paths are tested separately.
        self.picker.__globals__["_asset"] = lambda name: "data:image/avif;base64,AAAA"

    def test_digits_wrap_and_do_not_commit_before_confirmation(self):
        self.st.session_state.game1_pred_tens = 9
        self.st.session_state.game1_pred_ones = 0
        self.change_digit("tens", 1)
        self.change_digit("ones", -1)
        self.assertEqual(self.st.session_state.game1_pred_tens, 0)
        self.assertEqual(self.st.session_state.game1_pred_ones, 9)
        self.assertNotIn("game_1_predicted_digits", self.st.session_state)

    def test_default_pair_and_news_title_are_safe_markup(self):
        title = '<img src=x onerror="alert(1)">'
        self.picker(title)
        page = "".join(self.st.markup)
        self.assertEqual((self.st.session_state.tens_val, self.st.session_state.ones_val), (0, 4))
        self.assertIn(escape(title, quote=True), page)
        self.assertNotIn(title, page)
        self.assertIn("1,250 C", page)
        self.assertNotIn("game_1_predicted_digits", self.st.session_state)

    def test_buttons_change_single_digit_using_fragment_rerun(self):
        self.st.clicked = "game1-pred-ones-down"
        with self.assertRaises(RerunRequested):
            self.picker("한 기사")
        self.assertEqual(self.st.session_state.game1_pred_ones, 3)
        self.assertEqual(self.st.rerun_scope, "fragment")
        self.assertNotIn("game_1_predicted_digits", self.st.session_state)

    def test_submit_commits_existing_score_protocol(self):
        self.st.session_state.game1_pred_tens = 8
        self.st.session_state.game1_pred_ones = 7
        self.st.session_state.game_1_bet = 1000
        self.st.clicked = "game1-pred-submit"
        with self.assertRaises(RerunRequested):
            self.picker("한 기사")
        self.assertEqual(self.st.session_state.game_1_predicted_digits, 87)
        self.assertEqual(self.st.session_state.game_1_bet, 1000)
        self.assertIsNone(self.st.rerun_scope)

    def test_bank_navigation_keeps_current_bet_and_digits(self):
        self.st.session_state.game_1_bet = 1000
        self.st.session_state.game1_pred_ones = 6
        self.st.clicked = "game1-pred-bank"
        self.picker("기사")
        self.ui.change_page.assert_called_once_with("bank")
        self.assertEqual(self.st.session_state.game_1_bet, 1000)
        self.assertEqual(self.st.session_state.game1_pred_ones, 6)
        self.assertNotIn("game_1_predicted_digits", self.st.session_state)

    def test_artwork_and_styles_are_checked_into_the_repository(self):
        root = Path(__file__).resolve().parents[1]
        for name in ("pred_header", "pred_tag", "pred_news", "pred_frame", "pred_reel"):
            with self.subTest(asset=name):
                self.assertGreater((root / "assets" / "game1_prediction" / f"{name}.avif").stat().st_size, 500)
        css = (root / "games" / "game1_prediction_ui.css").read_text(encoding="utf-8")
        self.assertIn("game1-prediction-reels", css)
        self.assertIn("orientation:landscape", css)


if __name__ == "__main__":
    unittest.main()
