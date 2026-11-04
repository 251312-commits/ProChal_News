import sys
import unittest
from runpy import run_module
from unittest.mock import MagicMock, patch


class Session(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class NewsSlotTests(unittest.TestCase):
    def setUp(self):
        self.st, self.ai, db, self.ui = (MagicMock() for _ in range(4))
        self.st.session_state = Session(game_1_bet=1000)
        self.st.columns.return_value = [MagicMock(), MagicMock()]
        self.st.button.return_value = False
        self.component = self.st.components.v1.declare_component.return_value
        self.component.return_value = None
        self.sheet = db.init_news_sheet.return_value
        self.sheet.get_all_records.return_value = [
            {"Title": "첫 기사", "URL": "url-1", "Count": 4},
            {"Title": "둘째 기사", "URL": "url-2", "Count": 7},
        ]
        self.ai.pick_3_lowest_count_news.side_effect = lambda items: items[:3]
        self.ai.bring_article.return_value = ("첫 기사", "본문")
        modules = patch.dict(sys.modules, {
            "streamlit": self.st, "streamlit.components": self.st.components,
            "streamlit.components.v1": self.st.components.v1,
            "modules.news_ai": self.ai, "modules.db_handler": db,
            "modules.ui_components": self.ui,
        })
        modules.start()
        self.addCleanup(modules.stop)
        self.select = run_module("games.common")["get_game_news_selection"]

    def test_only_a_current_valid_choice_opens_an_article_once(self):
        waiting = (None, None, None)
        self.assertEqual(self.select("game_1"), waiting)
        args = self.component.call_args.kwargs
        self.assertEqual(args["titles"], ["첫 기사", "둘째 기사"])
        round_id = args["round_id"]
        for token, index in [("stale", 0), (round_id, -1), (round_id, 2), (round_id, True)]:
            with self.subTest(token=token, index=index):
                self.component.return_value = {"action": "choose", "round_id": token, "index": index}
                self.assertEqual(self.select("game_1"), waiting)
                self.assertEqual(self.component.call_args.kwargs["round_id"], round_id)
        self.sheet.update_cell.assert_not_called()
        self.ai.pick_3_lowest_count_news.assert_called_once()
        self.sheet.get_all_records.assert_called_once()

        self.component.return_value = {"action": "choose", "round_id": round_id, "index": 0}
        self.assertEqual(self.select("game_1"), waiting)
        self.assertEqual(self.select("game_1"), waiting)  # Replayed component value during reading.
        self.st.button.return_value = True
        self.assertEqual(self.select("game_1"), waiting)
        self.assertEqual(self.select("game_1"), ("첫 기사", "본문", "url-1"))
        self.sheet.update_cell.assert_called_once_with(2, 2, 5)
        self.ai.bring_article.assert_called_once_with("url-1")

    def test_navigation_preserves_candidates_without_counting_a_view(self):
        self.select("game_1")
        round_id = self.component.call_args.kwargs["round_id"]
        self.component.return_value = {"action": "bank", "round_id": round_id}
        self.select("game_1")
        self.ui.change_page.assert_called_once_with("bank")
        self.assertEqual(self.st.session_state.game_1_bet, 1000)

        self.select("game_1")  # Return from bank with the old component event still present.
        new_round = self.component.call_args.kwargs["round_id"]
        self.assertNotEqual(new_round, round_id)
        self.ui.change_page.assert_called_once()
        self.component.return_value = {"action": "back", "round_id": new_round}
        self.select("game_1")
        self.assertNotIn("game_1_bet", self.st.session_state)
        self.sheet.get_all_records.assert_called_once()
        self.sheet.update_cell.assert_not_called()
