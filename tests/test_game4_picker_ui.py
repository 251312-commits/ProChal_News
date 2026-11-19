"""Game 4's independent mobile picker and round-bound events."""

import sys
import unittest
from pathlib import Path
from runpy import run_module
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]


class GameFourPickerTests(unittest.TestCase):
    def setUp(self):
        st = self.st = MagicMock()
        st.session_state = {}
        self.ui = MagicMock()
        self.ui.load_local_image_url.return_value = "https://example.org/art.png"
        deps = {
            "streamlit": st,
            "streamlit.components": st.components,
            "streamlit.components.v1": st.components.v1,
            "games.shared.betting": MagicMock(),
            "games.shared.news_flow": MagicMock(),
            "games.shared.loading": MagicMock(),
            "games.shared.interest": MagicMock(),
            "modules.transactions": MagicMock(),
            "modules.news_ai": MagicMock(),
            "modules.ui_components": self.ui,
            "views.ranking": MagicMock(),
        }
        with patch.dict(sys.modules, deps):
            self.picker = run_module("games.game4")["_render_game_4_range_picker"]
        self.component = st.components.v1.declare_component.return_value
        self.ranges = ["70.00~71.99%", "72.00~73.99%", "74.00~75.99%"]

    def test_component_is_full_screen_and_assets_are_reused(self):
        self.st.session_state["game4_picker_round"] = "round-a"
        self.component.return_value = None
        result = self.picker(self.ranges, 1250)
        self.assertIsNone(result)
        _, kwargs = self.component.call_args
        self.assertEqual(kwargs["round_id"], "round-a")
        self.assertEqual(kwargs["key"], "game4-picker-round-a")
        self.assertEqual(kwargs["coins"], 1250)
        self.assertEqual(kwargs["ranges"], self.ranges)
        self.assertIsNone(kwargs["reveal"])
        self.assertEqual(set(kwargs["art"]), {
            "background", "logo", "laurel_left", "laurel_right"
        })
        self.st.container.assert_called_once_with(key="game4-picker-stage")
        self.assertEqual(self.ui.load_local_image_url.call_count, 4)
        self.assertIn("position: fixed", self.st.html.call_args.args[0])
        self.assertIn("height: 100dvh", self.st.html.call_args.args[0])

    def test_confirmed_index_is_preserved_and_unconfirmed_choice_ignored(self):
        for index in [0, 1, 2]:
            with self.subTest(index=index):
                self.st.session_state["game4_picker_round"] = "round-a"
                self.component.return_value = {
                    "round_id": "round-a", "action": "choose", "index": index
                }
                self.assertEqual(self.picker(self.ranges, 1250), index)
                self.assertEqual(self.st.session_state["game4_picker_round"], "round-a")
        self.st.session_state["game4_picker_round"] = "round-a"
        self.component.return_value = {
            "round_id": "stale", "action": "choose", "index": 2
        }
        self.assertIsNone(self.picker(self.ranges, 1250))
        self.component.return_value = {
            "round_id": "round-a", "action": "choose", "index": True
        }
        self.assertIsNone(self.picker(self.ranges, 1250))
        self.component.return_value = {
            "round_id": "round-a", "action": "choose", "index": 3
        }
        self.assertIsNone(self.picker(self.ranges, 1250))

    def test_score_reveal_is_bound_to_the_same_round(self):
        self.st.session_state["game4_picker_round"] = "round-a"
        self.component.return_value = {
            "round_id": "round-a", "action": "reveal_complete"
        }
        completed = self.picker(
            self.ranges, 1550,
            selected_index=0, actual_score=74.25, answer_index=2,
        )
        self.assertEqual(completed, "reveal_complete")
        self.assertEqual(self.st.session_state["game4_picker_round"], "round-a")
        self.assertEqual(self.component.call_args.kwargs["reveal"], {
            "score": "74.25", "answer_index": 2, "selected_index": 0,
        })
        self.component.return_value = {
            "round_id": "round-a", "action": "choose", "index": 0,
        }
        self.assertIsNone(self.picker(
            self.ranges, 1550,
            selected_index=0, actual_score=74.25, answer_index=2,
        ))
        self.component.return_value = {
            "round_id": "old-round", "action": "reveal_complete"
        }
        self.assertIsNone(self.picker(
            self.ranges, 1550,
            selected_index=0, actual_score=74.25, answer_index=2,
        ))

    def test_reveal_completion_is_invalid_during_player_selection(self):
        self.st.session_state["game4_picker_round"] = "round-a"
        self.component.return_value = {
            "round_id": "round-a", "action": "reveal_complete"
        }
        self.assertIsNone(self.picker(self.ranges, 1000))

    def test_back_and_bank_navigation(self):
        for action, destination in [("back", "main"), ("bank", "bank")]:
            with self.subTest(action=action):
                self.st.session_state["game4_picker_round"] = "round-a"
                self.component.return_value = {
                    "round_id": "round-a", "action": action
                }
                self.ui.change_page.reset_mock()
                self.assertIsNone(self.picker(self.ranges, 1250))
                self.ui.change_page.assert_called_once_with(destination)
                self.assertNotIn("game4_picker_round", self.st.session_state)

    def test_frontend_grid_has_no_streamlit_columns_or_radio(self):
        html = (ROOT / "games/game4_ui/picker/index.html").read_text(encoding="utf-8")
        self.assertIn('grid-template-columns: minmax(0, 40fr) minmax(0, 60fr)', html)
        self.assertIn('grid-template-rows: repeat(3, minmax(0, 1fr))', html)
        self.assertIn('grid-template-columns: clamp(35px, 10vw, 49px) minmax(0, 1fr)', html)
        self.assertIn('min-height: 100dvh', html)
        self.assertIn('height: 100dvh', html)
        self.assertIn('viewport-fit=cover', html)
        self.assertIn('env(safe-area-inset-top)', html)
        self.assertIn('@media (max-width: 359px)', html)
        self.assertIn('@media (max-height: 620px)', html)
        self.assertIn('aria-pressed="true"', html)
        js = (ROOT / "games/game4_ui/picker/picker.js").read_text(encoding="utf-8")
        self.assertIn('if (action === "choose") value.index = selected', js)
        self.assertIn('finish("reveal_complete")', js)
        self.assertIn('payload.answer_index', js)
        self.assertIn('target.top + target.height / 2 - source.top', js)
        self.assertIn('args.reveal && !revealing', js)
        self.assertIn('class="mystery"', html)
        self.assertIn('var(--landing-offset, 0px)', html)
        self.assertIn('.segment.correct', html)
        self.assertIn('event.origin === "null" ? "*" : event.origin', js)
        self.assertIn('<script defer src="./picker.js"></script>', html)
        self.assertNotIn("st.radio", html)
        self.assertNotIn("st.columns", html)


if __name__ == "__main__":
    unittest.main()
