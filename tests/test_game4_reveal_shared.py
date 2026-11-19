"""Game 4 shared news flow and the post-settlement score reveal."""

import sys
import unittest
from runpy import run_module
from unittest.mock import MagicMock, patch


class GameFourSharedAndRevealTests(unittest.TestCase):
    def setUp(self):
        self.st = MagicMock()
        self.st.columns.side_effect = lambda sizes, **_kwargs: [
            MagicMock() for _ in range(sizes if isinstance(sizes, int) else len(sizes))
        ]
        self.st.button.return_value = False
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

    def test_reveal_hides_score_behind_rotating_question_marks(self):
        self.st.session_state.game_4_result = {
            "actual_score": 74.25,
            "is_win": True,
            "reward": 3000,
            "selected_range": "74.00~75.99%",
            "target_range": "74.00~75.99%",
            "new_coins": 4250,
            "new_streak": 2,
        }
        self.show_result()
        markup = " ".join(
            call.args[0]
            for call in self.st.html.call_args_list
            if isinstance(call.args[0], str)
        )
        self.assertIn('class="g4-reel-mystery"', markup)
        self.assertIn(">??</span>", markup)
        self.assertIn('class="g4-reel-value"', markup)
        self.assertIn("74.25%", markup)
        self.st.metric.assert_not_called()
        self.st.success.assert_called_once()
        self.tx.settle_game_round.assert_not_called()

    def test_result_does_not_reveal_if_interest_update_not_complete(self):
        self.interest.apply_end_of_turn_interest.return_value = False
        self.st.session_state.game_4_result = {"actual_score": 74.25}
        self.show_result()
        self.st.html.assert_not_called()
        self.tx.settle_game_round.assert_not_called()


if __name__ == "__main__":
    unittest.main()
