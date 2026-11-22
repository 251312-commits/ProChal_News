import sys
import unittest
from pathlib import Path
from runpy import run_module
from unittest.mock import MagicMock, patch


class GameFiveTutorialTests(unittest.TestCase):
    def test_mobile_candidate_layout_and_confirmation_buttons_are_preserved(self):
        source = (Path(__file__).resolve().parents[1] / "games/game5.py").read_text(encoding="utf-8")

        self.assertIn("white-space: nowrap;", source)
        self.assertIn("gap: 16px;", source)
        self.assertIn(".st-key-game5-candidate-row-0", source)
        self.assertIn(".st-key-game5-candidate-row-1", source)
        self.assertIn("calc(50% - 4px)", source)
        self.assertIn("calc(33.333% - 6px)", source)
        self.assertIn("font-size: 9px !important;", source)
        self.assertIn("word-break: keep-all !important;", source)
        self.assertIn('"본문 읽기"', source)
        self.assertIn('"정답 결정"', source)
        self.assertIn(".st-key-game5-candidate-row-1 [data-testid=\"stVerticalBlockBorderWrapper\"]", source)
        self.assertIn("white-space: nowrap !important;", source)
        self.assertIn("@media (max-width: 480px)", source)
        self.assertNotIn(":has([data-testid=\"stVerticalBlockBorderWrapper\"])", source)

    def test_game5_closes_turn_with_interest_like_game1(self):
        game5 = (Path(__file__).resolve().parents[1] / "games/game5.py").read_text(encoding="utf-8")
        game1 = (Path(__file__).resolve().parents[1] / "games/game1/game1.py").read_text(encoding="utf-8")

        self.assertIn('settle_game_round("game_5"', game5)
        self.assertIn('apply_end_of_turn_interest("game_5")', game5)
        self.assertIn('apply_end_of_turn_interest("game_1")', game1)

    def test_mobile_betting_balance_uses_explicit_nav_grid(self):
        source = (Path(__file__).resolve().parents[1] / "games/shared/betting.py").read_text(encoding="utf-8")

        self.assertIn("grid-template-columns:44px minmax(0,1fr) 44px !important;", source)
        self.assertIn(".st-key-casino_betting_shell .cb-balance", source)
        self.assertIn("justify-content:flex-end !important;", source)
        self.assertIn('st.container(key="bet_nav_row")', source)

    def test_tutorial_starts_game_and_marks_it_as_seen(self):
        st, ui = MagicMock(), MagicMock()
        state = {}
        st.session_state = state
        st.button.side_effect = lambda label, **kwargs: label == "게임 시작"

        with patch.dict(sys.modules, {
            "streamlit": st, "modules.ui_components": ui,
            "modules.news_ai": MagicMock(), "modules.db_handler": MagicMock(),
            "views.ranking": MagicMock(),
            "games.shared.betting": MagicMock(),
            "games.shared.loading": MagicMock(),
        }):
            show_tutorial = run_module("games.game5")["show_game_5_tutorial"]
            show_tutorial()

        self.assertTrue(state["game_5_tutorial_seen"])
        ui.change_page.assert_called_once_with("game_5")

    def test_skip_also_starts_game_without_repeating_tutorial(self):
        st, ui = MagicMock(), MagicMock()
        state = {}
        st.session_state = state
        st.button.side_effect = lambda label, **kwargs: label == "건너뛰기"

        with patch.dict(sys.modules, {
            "streamlit": st, "modules.ui_components": ui,
            "modules.news_ai": MagicMock(), "modules.db_handler": MagicMock(),
            "views.ranking": MagicMock(),
            "games.shared.betting": MagicMock(),
            "games.shared.loading": MagicMock(),
        }):
            show_tutorial = run_module("games.game5")["show_game_5_tutorial"]
            show_tutorial()

        self.assertTrue(state["game_5_tutorial_seen"])
        ui.change_page.assert_called_once_with("game_5")
