"""Regression tests for the standalone Game 1 prediction screen."""
from contextlib import nullcontext
from pathlib import Path
from runpy import run_module
import sys
import types
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
        self.markup = []

    @staticmethod
    def fragment(fn):
        return fn

    @staticmethod
    def container(*args, **kwargs):
        return nullcontext()

    def html(self, value):
        self.markup.append(str(value))

    @staticmethod
    def rerun():
        raise RerunRequested()


class FakeComponents:
    def __init__(self):
        self.event = None
        self.calls = []
        self.declared = None

    def declare_component(self, name, *, path):
        self.declared = (name, path)

        def show_screen(**kwargs):
            self.calls.append(kwargs)
            return self.event

        return show_screen


class PredictionScreenTests(unittest.TestCase):
    def setUp(self):
        self.st = FakeStreamlit(current_user_data={"코인": 1250}, game_1_bet=1000)
        self.v1 = FakeComponents()
        self.parent = types.ModuleType("streamlit.components")
        self.parent.v1 = self.v1
        self.st.components = self.parent
        self.ui = MagicMock()
        self.ui.load_local_image_url.side_effect = (
            lambda path: "/app/static/assets/" + Path(path).name
        )
        with patch.dict(sys.modules, {
            "streamlit": self.st,
            "streamlit.components": self.parent,
            "streamlit.components.v1": self.v1,
            "modules.ui_components": self.ui,
            "modules.news_ai": MagicMock(),
            "modules.db_handler": MagicMock(),
            "games.common": MagicMock(),
            "games.result_reveal": MagicMock(),
            "views.ranking": MagicMock(),
        }):
            source = run_module("games.game1.game1")
        self.picker = source["render_game1_prediction_picker"]
        self.save_digits = source["_save_digits"]

    def test_default_screen_uses_joined_wallet_component(self):
        self.picker("AI, 일자리 지형을 다시 바꾸나")
        self.assertEqual(
            self.v1.declared[0], "game1_prediction_screen"
        )
        self.assertTrue(self.v1.declared[1].endswith("games/game1/prediction_screen"))
        call = self.v1.calls[-1]
        self.assertEqual(call["coins"], 1250)
        self.assertEqual(call["digits"], [0, 4])
        self.assertEqual(call["title"], "AI, 일자리 지형을 다시 바꾸나")
        self.assertTrue(call["round_id"])
        self.assertIn("bet_podium.png", [
            Path(path).name for path in self.ui.load_local_image_url.call_args_list
            for path in [path.args[0]]
        ])
        self.assertEqual(set(call["art"]), {
            "background", "header", "news", "tag", "frame", "reel", "podium"
        })
        self.assertTrue(all(
            value.startswith("/app/static/assets/") for value in call["art"].values()
        ))
        self.assertNotIn("game_1_predicted_digits", self.st.session_state)

    def test_change_updates_both_digit_keys_without_submitting(self):
        self.picker("기사")
        self.v1.event = {
            "round_id": self.st.session_state.game1_pred_round_id,
            "action": "change", "digits": [9, 3],
        }
        self.picker("기사")
        self.assertEqual(
            (self.st.session_state.game1_pred_tens, self.st.session_state.game1_pred_ones),
            (9, 3),
        )
        self.assertEqual((self.st.session_state.tens_val, self.st.session_state.ones_val), (9, 3))
        self.assertNotIn("game_1_predicted_digits", self.st.session_state)

    def test_confirm_stores_00_99_protocol_and_preserves_bet(self):
        self.picker("기사")
        self.v1.event = {
            "round_id": self.st.session_state.game1_pred_round_id,
            "action": "confirm", "digits": [8, 7],
        }
        with self.assertRaises(RerunRequested):
            self.picker("기사")
        self.assertEqual(self.st.session_state.game_1_predicted_digits, 87)
        self.assertEqual(self.st.session_state.game_1_bet, 1000)
        self.assertNotIn("game1_pred_round_id", self.st.session_state)

    def test_invalid_digits_or_stale_round_do_not_commit(self):
        self.picker("기사")
        current = self.st.session_state.game1_pred_round_id
        for event in [
            {"round_id": "stale", "action": "confirm", "digits": [0, 4]},
            {"round_id": current, "action": "confirm", "digits": [-1, 4]},
            {"round_id": current, "action": "confirm", "digits": [10, 4]},
            {"round_id": current, "action": "confirm", "digits": [True, 4]},
            {"round_id": current, "action": "confirm", "digits": ["0", "4"]},
            {"round_id": current, "action": "confirm", "digits": [4]},
        ]:
            with self.subTest(event=event):
                self.v1.event = event
                self.picker("기사")
                self.assertNotIn("game_1_predicted_digits", self.st.session_state)

    def test_back_and_bank_keep_uncommitted_digits(self):
        for action, page in [("back", "main"), ("bank", "bank")]:
            with self.subTest(action=action):
                self.v1.event = None
                self.ui.change_page.reset_mock()
                self.picker("기사")
                self.v1.event = {
                    "round_id": self.st.session_state.game1_pred_round_id,
                    "action": action, "digits": [4, 6],
                }
                self.picker("기사")
                self.ui.change_page.assert_called_once_with(page)
                self.assertEqual(self.st.session_state.game_1_bet, 1000)
                self.assertEqual(
                    (self.st.session_state.game1_pred_tens, self.st.session_state.game1_pred_ones),
                    (4, 6),
                )
                self.assertNotIn("game_1_predicted_digits", self.st.session_state)

    def test_title_is_data_not_unsafe_html(self):
        raw_title = '<img src=x onerror="alert(1)">'
        self.picker(raw_title)
        self.assertEqual(self.v1.calls[-1]["title"], raw_title)
        self.assertNotIn(raw_title, "".join(self.st.markup))
        frontend = (
            Path(__file__).resolve().parents[1] / "games/game1/prediction_screen/prediction.js"
        ).read_text(encoding="utf-8")
        self.assertIn("ui.title.textContent", frontend)
        self.assertNotIn(".innerHTML", frontend)

    def test_frontend_files_and_one_screen_layout(self):
        root = Path(__file__).resolve().parents[1]
        ui = root / "games/game1/prediction_screen"
        for name in ("index.html", "prediction.css", "prediction.js"):
            self.assertTrue((ui / name).is_file(), name)
        html = (ui / "index.html").read_text(encoding="utf-8")
        css = (ui / "prediction.css").read_text(encoding="utf-8")
        js = (ui / "prediction.js").read_text(encoding="utf-8")
        self.assertIn('class="balance"', html)
        self.assertIn('class="bank"', html)
        self.assertIn('class="bank"', html.split('class="balance"')[1].split("</div>")[0])
        self.assertIn("height:100dvh", css)
        self.assertIn("grid-template-rows:", css)
        self.assertIn("container-type:size", css)
        self.assertIn("aspect-ratio:520/340", css)
        self.assertIn("aspect-ratio:258/360", css)
        self.assertIn("aspect-ratio:1160/566", css)
        self.assertIn('sendValue("change")', js)
        self.assertIn('sendValue(action)', js)
        self.assertIn("streamlit:setComponentValue", js)
        self.assertIn("streamlit:componentReady", js)
        self.assertEqual(css.count("{"), css.count("}"))
        for path in (
            "bet_background.jpg", "bet_podium.png",
            "game1_prediction/pred_header.avif", "game1_prediction/pred_news.avif",
            "game1_prediction/pred_tag.avif", "game1_prediction/pred_frame.avif",
            "game1_prediction/pred_reel.avif",
        ):
            self.assertTrue((root / "assets" / path).is_file(), path)


    def test_long_news_titles_are_clipped_and_stage_positions_are_adjusted(self):
        root = Path(__file__).resolve().parents[1] / "games/game1/prediction_screen"
        html = (root / "index.html").read_text(encoding="utf-8")
        css = (root / "prediction.css").read_text(encoding="utf-8")

        self.assertIn('<div class="news-copy">', html)
        self.assertIn('<p class="news-title"></p>', html)
        clipping_area = css.split(".news-copy {", 1)[1].split("}", 1)[0]
        headline = css.split(".news-title {", 1)[1].split("}", 1)[0]
        podium = css.split(".podium {", 1)[1].split("}", 1)[0]

        self.assertIn("inset:34% 7% 12% 26%", clipping_area)
        self.assertIn("overflow:hidden", clipping_area)
        self.assertIn("max-height:100%", headline)
        self.assertIn("-webkit-line-clamp:2", headline)
        self.assertIn("overflow:hidden", headline)
        self.assertNotIn("예측하는 유사도 점수", html)
        self.assertIn('<span class="prefix" aria-hidden="true">?.</span>', html)
        self.assertIn("top:55.5%", podium)


if __name__ == "__main__":
    unittest.main()
