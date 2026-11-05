import sys
import unittest
from runpy import run_module
from unittest.mock import MagicMock, patch


class GameFiveTutorialTests(unittest.TestCase):
    def test_tutorial_starts_game_and_marks_it_as_seen(self):
        st, ui = MagicMock(), MagicMock()
        state = {}
        st.session_state = state
        st.button.side_effect = lambda label, **kwargs: label == "게임 시작"

        with patch.dict(sys.modules, {"streamlit": st, "modules.ui_components": ui}):
            show_tutorial = run_module("games.game5_tutorial")["show_game_5_tutorial"]
            show_tutorial()

        self.assertTrue(state["game_5_tutorial_seen"])
        ui.change_page.assert_called_once_with("game_5")

    def test_skip_also_starts_game_without_repeating_tutorial(self):
        st, ui = MagicMock(), MagicMock()
        state = {}
        st.session_state = state
        st.button.side_effect = lambda label, **kwargs: label == "건너뛰기"

        with patch.dict(sys.modules, {"streamlit": st, "modules.ui_components": ui}):
            show_tutorial = run_module("games.game5_tutorial")["show_game_5_tutorial"]
            show_tutorial()

        self.assertTrue(state["game_5_tutorial_seen"])
        ui.change_page.assert_called_once_with("game_5")
