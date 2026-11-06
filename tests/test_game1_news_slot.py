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
        self.image_url = "https://images.press.example/story.jpg"
        self.ai.bring_article.return_value = ("첫 기사", "본문", self.image_url)
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
        self.assertIs(args["continuous_reel"], True)
        self.assertIs(args["allow_back"], False)
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
        reader_round = self.component.call_args.kwargs["round_id"]
        self.component.return_value = {"action": "predict", "round_id": reader_round}
        self.assertEqual(self.select("game_1"), waiting)
        self.assertEqual(self.select("game_1"), ("첫 기사", "본문", "url-1"))
        self.assertNotIn("candidates_game_1", self.st.session_state)
        self.sheet.update_cell.assert_called_once_with(2, 2, 5)
        self.ai.bring_article.assert_called_once_with("url-1", include_image=True)

    def test_reader_navigation_uses_live_data_and_preserves_the_stake(self):
        self.st.session_state.current_user_data = {"코인": 2300}
        url = "https://www.press.example/story"
        self.sheet.get_all_records.return_value[0]["URL"] = url
        self.select("game_1")
        slot_round = self.component.call_args.kwargs["round_id"]
        self.component.return_value = {"action": "choose", "round_id": slot_round, "index": 0}
        self.select("game_1")
        self.select("game_1", win_multiplier=100)
        args = self.component.call_args.kwargs
        self.assertEqual((args["title"], args["text"]), ("첫 기사", "본문"))
        self.assertEqual((args["url"], args["source"]), (url, "press.example"))
        self.assertEqual(args["image_url"], self.image_url)
        self.assertEqual((args["coins"], args["reward"]), (2300, 100_000))

        self.component.return_value = {"action": "bank", "round_id": args["round_id"]}
        self.select("game_1")
        self.select("game_1")  # Replayed event when returning from the bank.
        self.ui.change_page.assert_called_once_with("bank")
        next_round = self.component.call_args.kwargs["round_id"]
        self.assertNotEqual(args["round_id"], next_round)
        self.assertEqual(self.st.session_state.selected_news_game_1["url"], url)
        self.component.return_value = {"action": "back", "round_id": next_round}
        self.select("game_1")
        self.select("game_1")
        self.assertEqual(self.component.call_args.kwargs["round_id"], next_round)
        self.assertEqual(self.component.call_args.kwargs["url"], url)
        self.assertEqual(self.st.session_state.game_1_bet, 1000)
        self.component.return_value = {"action": "predict", "round_id": next_round}
        self.select("game_1")
        self.assertEqual(self.select("game_1"), ("첫 기사", "본문", url))
        self.sheet.update_cell.assert_called_once_with(2, 2, 5)
        self.ai.bring_article.assert_called_once_with(url, include_image=True)
        self.ai.pick_3_lowest_count_news.assert_called_once()

    def test_other_games_still_use_their_existing_reader(self):
        self.st.session_state.selected_news_game_2 = {
            "title": "제목", "text": "본문", "url": "url-2",
        }
        self.st.button.return_value = True
        self.assertEqual(self.select("game_2"), (None, None, None))
        self.assertEqual(self.select("game_2"), ("제목", "본문", "url-2"))
        self.component.assert_not_called()

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
        self.select("game_1")
        self.assertEqual(self.component.call_args.kwargs["round_id"], new_round)
        self.assertEqual(self.component.call_args.kwargs["titles"], ["첫 기사", "둘째 기사"])
        self.assertEqual(self.st.session_state.game_1_bet, 1000)
        self.ai.pick_3_lowest_count_news.assert_called_once()
        self.sheet.get_all_records.assert_called_once()
        self.sheet.update_cell.assert_not_called()

    def test_game2_slot_still_returns_to_betting(self):
        render_slot = run_module("games.news_roulette2")["render_news_slot"]
        self.st.session_state.game_2_bet = 500
        candidates = [("기사", "url-2")]
        render_slot(candidates)
        args = self.component.call_args.kwargs
        self.assertIs(args.get("allow_back", True), True)
        self.component.return_value = {"action": "back", "round_id": args["round_id"]}
        render_slot(candidates)
        self.assertNotIn("game_2_bet", self.st.session_state)
        self.assertNotIn("game_2_slot_round", self.st.session_state)
        self.st.rerun.assert_called_once()
