"""Game 4 shared news flow and the post-settlement score reveal."""

import sys
import unittest
from runpy import run_module
from unittest.mock import MagicMock, patch


class Session(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class GameFourSharedAndRevealTests(unittest.TestCase):
    def setUp(self):
        self.st = MagicMock()
        self.st.session_state = Session()
        self.st.columns.side_effect = lambda sizes, **_kwargs: [
            MagicMock() for _ in range(sizes if isinstance(sizes, int) else len(sizes))
        ]
        self.st.button.return_value = False
        self.st.dialog.side_effect = lambda _title: lambda fn: fn
        self.news = MagicMock()
        self.interest = MagicMock()
        self.interest.apply_end_of_turn_interest.return_value = True
        self.tx = MagicMock()
        deps = {
            "streamlit": self.st,
            "streamlit.components": self.st.components,
            "streamlit.components.v1": self.st.components.v1,
            "games.shared.betting": MagicMock(),
            "games.shared.news_flow": self.news,
            "games.shared.loading": MagicMock(),
            "games.shared.interest": self.interest,
            "modules.transactions": self.tx,
            "modules.news_ai": MagicMock(),
            "modules.ui_components": MagicMock(),
            "views.ranking": MagicMock(),
        }
        with patch.dict(sys.modules, deps):
            functions = run_module("games.game4")
        self.show_game_4 = functions["show_game_4"]
        self.show_result = functions["_show_game_4_result"]

    def test_article_selection_uses_shared_immersive_news_and_reader(self):
        self.st.session_state = {"game_4_bet": 1000}
        self.news.get_game_news_selection.return_value = (None, None, None)
        self.show_game_4()
        self.news.get_game_news_selection.assert_called_once_with(
            "game_4", win_multiplier=3.0, immersive_reader=True
        )
        self.tx.settle_game_round.assert_not_called()

    def test_final_result_is_immediate_and_evidence_button_opens_dialog(self):
        self.st.session_state.game_4_result = {
            "actual_score": 74.25,
            "is_win": True,
            "reward": 3000,
            "selected_range": "74.00~75.99%",
            "target_range": "74.00~75.99%",
            "new_coins": 4250,
            "new_streak": 2,
            "title": "기사 제목",
            "summary": "AI 모델의 요약문",
            "score_details": {
                "model_name": "reranker-example",
                "token_count": 100,
                "logit": 1.11,
                "normalized": 0.75,
            },
        }
        self.st.button.side_effect = lambda _label, **kwargs: (
            kwargs.get("key") == "game4_result_evidence"
        )
        self.show_result()
        markup = " ".join(
            str(call.args[0])
            for call in self.st.html.call_args_list
        )
        self.assertIn('class="g4-final-value"', markup)
        self.assertIn("74.25%", markup)
        self.assertNotIn('class="g4-reel-mystery"', markup)
        self.assertIn("reranker-example", str(self.st.caption.call_args_list))
        self.assertIn("AI 모델의 요약문", str(self.st.write.call_args_list))
        self.assertIn("기사 제목", str(self.st.write.call_args_list))
        self.assertIn("score-diagram", markup)
        self.st.success.assert_called_once()
        self.tx.settle_game_round.assert_not_called()

    def test_confirmed_game4_settles_once_before_picker_reveal(self):
        class Session(dict):
            __getattr__ = dict.__getitem__
            __setattr__ = dict.__setitem__

        self.st.session_state = Session({
            "game_4_bet": 1000,
            "game_4_round_id": "abc",
            "game_4_range": 0,
            "game_4_score": 74.25,
            "game_4_ranges": ["70.00~71.99%", "72.00~73.99%", "74.00~75.99%"],
            "game_4_answer_index": 2,
            "game_4_summary": "저장된 요약",
            "game_4_score_details": {
                "model_name": "reranker-example", "token_count": 100,
                "logit": 1.11, "normalized": 0.75,
            },
            "current_user_data": {"코인": 5000},
        })
        self.news.get_game_news_selection.return_value = ("제목", "기사", "url")
        self.tx.settle_game_round.return_value = {
            "reward": -1000, "new_coins": 4000, "new_streak": 0,
        }
        picker = MagicMock(side_effect=[None, "reveal_complete"])
        self.show_game_4.__globals__["_render_game_4_range_picker"] = picker

        self.show_game_4()
        self.tx.settle_game_round.assert_called_once_with("game_4", 1000, False)
        self.assertEqual(self.st.session_state.game_4_result["summary"], "저장된 요약")
        self.assertEqual(self.st.session_state.game_4_result["score_details"]["logit"], 1.11)
        self.assertNotIn("game4_reveal_done", self.st.session_state)
        self.assertEqual(picker.call_args.kwargs["answer_index"], 2)
        self.assertEqual(picker.call_args.kwargs["selected_index"], 0)
        self.assertEqual(picker.call_args.kwargs["actual_score"], 74.25)

        self.show_game_4()
        self.assertTrue(self.st.session_state.game4_reveal_done)
        self.tx.settle_game_round.assert_called_once()
        self.st.rerun.assert_called_once()

        self.show_game_4()
        self.tx.settle_game_round.assert_called_once()
        self.assertEqual(picker.call_count, 2)
        self.st.success.assert_not_called()
        self.st.error.assert_called_once()

    def test_result_does_not_reveal_if_interest_update_not_complete(self):
        self.interest.apply_end_of_turn_interest.return_value = False
        self.st.session_state.game_4_result = {"actual_score": 74.25}
        self.show_result()
        self.st.html.assert_not_called()
        self.tx.settle_game_round.assert_not_called()


if __name__ == "__main__":
    unittest.main()
