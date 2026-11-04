import sys
import unittest
from runpy import run_module
from unittest.mock import MagicMock, patch


class GameOneEntryTests(unittest.TestCase):
    def test_guide_only_navigates_when_a_button_is_pressed(self):
        st, ui = MagicMock(), MagicMock()
        with patch.dict(sys.modules, {"streamlit": st, "modules.ui_components": ui}):
            show_guide = run_module("games.game1_tutorial")["show_game_1_tutorial"]
            for action, destination in (
                (None, None), ("메인으로", "main"), ("베팅하러 가기", "game_1"),
            ):
                with self.subTest(action=action):
                    st.button.side_effect = lambda label, **kwargs: label == action
                    ui.change_page.reset_mock()
                    show_guide()
                    if destination:
                        ui.change_page.assert_called_once_with(destination)
                    else:
                        ui.change_page.assert_not_called()

    def test_lobby_opens_guide_or_resumes_an_active_bet(self):
        st, ui, banners = MagicMock(), MagicMock(), MagicMock()
        banners.clickable_images.return_value = 2
        dependencies = {
            "streamlit": st, "streamlit_autorefresh": MagicMock(),
            "st_clickable_images": banners, "modules.ui_components": ui,
            "modules.db_handler": MagicMock(),
        }
        with patch.dict(sys.modules, dependencies):
            show_lobby = run_module("views.main")["show_main_page"]
            for round_state, expected in (
                ({}, "game_1_tutorial"),
                ({"game_1_bet": 1000, "game_1_predicted_digits": 4}, "game_1"),
            ):
                with self.subTest(expected=expected):
                    state = {"current_user_data": {"코인": 2000}, **round_state}
                    st.session_state = state.copy()
                    ui.change_page.reset_mock()
                    show_lobby()
                    ui.change_page.assert_called_once_with(expected)
                    self.assertEqual(st.session_state, state)
