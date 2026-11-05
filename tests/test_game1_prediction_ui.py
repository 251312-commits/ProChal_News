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
        # Real Streamlit callbacks run before the next fragment rerender.
        if key == self.clicked:
            self.clicked = None
            callback = kwargs.get("on_click")
            if callback:
                callback(*kwargs.get("args", ()), **kwargs.get("kwargs", {}))
            return True
        return False

    @staticmethod
    def columns(spec, **kwargs):
        return tuple(nullcontext() for _ in spec)

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

    def test_arrow_callbacks_change_number_and_rerender_display(self):
        # Pressing any arrow runs its callback; Streamlit then reruns the fragment.
        for key, expected_tens, expected_ones in (
            ("game1-pred-tens-up", 1, 4),
            ("game1-pred-ones-down", 1, 3),
            ("game1-pred-tens-down", 0, 3),
            ("game1-pred-ones-up", 0, 4),
        ):
            with self.subTest(key=key):
                self.st.clicked = key
                self.picker("한 기사")
                self.assertEqual(
                    (self.st.session_state.game1_pred_tens,
                     self.st.session_state.game1_pred_ones),
                    (expected_tens, expected_ones),
                )
                self.st.markup.clear()
                self.picker("한 기사")  # Simulate Streamlit's automatic fragment rerun.
                page = "".join(self.st.markup)
                self.assertIn(f'aria-label="소수 첫째 자리 {expected_tens}"', page)
                self.assertIn(f'aria-label="소수 둘째 자리 {expected_ones}"', page)
                self.assertEqual(
                    (self.st.session_state.tens_val, self.st.session_state.ones_val),
                    (expected_tens, expected_ones),
                )
                self.assertNotIn("game_1_predicted_digits", self.st.session_state)
                self.assertIsNone(self.st.rerun_scope)

    def test_arrows_wrap_zero_and_nine(self):
        self.st.session_state.game1_pred_tens = 9
        self.st.session_state.game1_pred_ones = 0
        self.st.clicked = "game1-pred-tens-up"
        self.picker("기사")
        self.assertEqual(self.st.session_state.game1_pred_tens, 0)
        self.st.clicked = "game1-pred-ones-down"
        self.picker("기사")
        self.assertEqual(self.st.session_state.game1_pred_ones, 9)
        self.picker("기사")
        self.assertEqual((self.st.session_state.tens_val, self.st.session_state.ones_val), (0, 9))

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

    def test_mobile_grid_uses_native_columns_and_correct_assets(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "games" / "game1_prediction_ui.py").read_text(encoding="utf-8")
        css = (root / "games" / "game1_prediction_ui.css").read_text(encoding="utf-8")
        self.assertIn('st.container(key="game1-prediction-nav", gap=None)', source)
        self.assertIn('st.container(key="game1-prediction-reels", gap=None)', source)
        self.assertIn("st.columns([1, 5, 1]", source)
        self.assertIn("st.columns([0.7, 1, 1]", source)
        self.assertIn("on_click=_change_digit", source)
        self.assertNotIn('color:transparent !important', source)
        self.assertNotIn('bet_coin_stack.png', source)
        self.assertIn('bet_podium.png', source)
        self.assertTrue((root / "assets" / "bet_podium.png").exists())
        self.assertIn('.st-key-game1-prediction-reels [data-testid="stHorizontalBlock"]', css)
        self.assertIn('grid-template-columns:minmax(0,.67fr)', css)
        self.assertIn('.st-key-game1-prediction-nav [data-testid="stHorizontalBlock"]', css)
        self.assertIn('minmax(0,1fr)', css)
        self.assertIn('max-height:640px', css)
        self.assertIn('env(safe-area-inset-bottom)', css)
        self.assertEqual(css.count("{"), css.count("}"))

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
