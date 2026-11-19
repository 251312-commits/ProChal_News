"""Game 4 illustrated pre-game guide and main-menu routing."""

import sys
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from runpy import run_module
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]


class GameFourTutorialTests(unittest.TestCase):
    def setUp(self):
        st = self.st = MagicMock()
        self.ui = MagicMock()
        self.ui.load_local_image_url.return_value = "data:image/svg+xml;base64,example"
        deps = {
            "streamlit": st,
            "streamlit.components": st.components,
            "streamlit.components.v1": st.components.v1,
            "modules.ui_components": self.ui,
            "games.shared.betting": MagicMock(),
            "games.shared.news_flow": MagicMock(),
            "games.shared.loading": MagicMock(),
            "games.shared.interest": MagicMock(),
            "modules.transactions": MagicMock(),
            "modules.news_ai": MagicMock(),
            "views.ranking": MagicMock(),
        }
        with patch.dict(sys.modules, deps):
            self.show_tutorial = run_module("games.game4")["show_game_4_tutorial"]

    def test_guide_is_four_step_and_includes_generated_illustrations(self):
        self.st.button.return_value = False
        self.show_tutorial()
        markup = " ".join(
            str(call.args[0]) for call in self.st.html.call_args_list
        )
        self.assertIn("GAME 04", markup)
        self.assertIn("game4-guide-sheet", markup)
        self.assertIn("코인 베팅", markup)
        self.assertIn("기사 선택", markup)
        self.assertIn("구간 예측", markup)
        self.assertIn("결과 확인", markup)
        self.assertIn("3배 추가", markup)
        self.assertIn("1,000 C", markup)
        self.assertIn("30초", markup)
        self.assertIn("세 구간", markup)
        self.assertEqual(markup.count("<img "), 4)
        paths = [
            Path(call.args[0]) for call
            in self.ui.load_local_image_url.call_args_list
        ]
        self.assertEqual([p.name for p in paths],
                         ["bet.svg", "news.svg", "range.svg", "result.svg"])
        self.assertTrue(all(p.parent.name == "game4_guide" for p in paths))
        self.ui.change_page.assert_not_called()

    def test_start_skip_and_back_buttons_route_correctly(self):
        for clicked, page in (
            ("메인으로", "main"),
            ("건너뛰기", "game_4"),
            ("베팅하러 가기", "game_4"),
        ):
            with self.subTest(clicked=clicked):
                self.st.button.side_effect = lambda label, **kwargs: label == clicked
                self.ui.change_page.reset_mock()
                self.show_tutorial()
                self.ui.change_page.assert_called_once_with(page)

    def test_generated_svg_assets_are_valid_and_have_descriptions(self):
        art = ROOT / "assets" / "game4_guide"
        for file in ("bet.svg", "news.svg", "range.svg", "result.svg"):
            with self.subTest(file=file):
                root = ET.parse(art / file).getroot()
                self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
                self.assertEqual(root.attrib.get("viewBox"), "0 0 560 300")
                self.assertTrue(root.find("{http://www.w3.org/2000/svg}title") is not None)

    def test_tutorial_css_remains_responsive_and_isolated(self):
        style = (ROOT / "games" / "game4_tutorial.css").read_text(encoding="utf-8")
        self.assertIn(".st-key-game4-guide", style)
        self.assertIn(".game4-guide-sheet li img", style)
        self.assertIn("max-width: 380px", style)
        self.assertIn("orientation: landscape", style)


class GameFourMenuRouteTests(unittest.TestCase):
    def test_main_menu_opens_guide_or_resumes_current_round(self):
        st, ui, banners = MagicMock(), MagicMock(), MagicMock()
        banners.clickable_images.return_value = 5
        st.button.return_value = False
        deps = {
            "streamlit": st, "streamlit_autorefresh": MagicMock(),
            "st_clickable_images": banners,
            "modules.ui_components": ui, "modules.db_handler": MagicMock(),
        }
        with patch.dict(sys.modules, deps):
            show_main = run_module("views.main")["show_main_page"]
            for state, expected in (
                ({}, "game_4_tutorial"),
                ({"game_4_bet": 1000}, "game_4"),
                ({"game_4_bet": 1000, "game_4_range": 2}, "game_4"),
            ):
                with self.subTest(state=state):
                    st.session_state = {
                        "current_user_data": {"코인": 3000},
                        **state,
                    }
                    ui.change_page.reset_mock()
                    show_main()
                    ui.change_page.assert_called_once_with(expected)

    def test_app_router_imports_and_dispatches_game4_tutorial(self):
        source = (ROOT / "news.py").read_text(encoding="utf-8")
        self.assertIn("show_game_4, show_game_4_tutorial", source)
        self.assertIn("elif st.session_state.page == 'game_4_tutorial':", source)
        self.assertIn("show_game_4_tutorial()", source)


if __name__ == "__main__":
    unittest.main()
