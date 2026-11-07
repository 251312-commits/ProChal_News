import sys
import unittest
from runpy import run_module
from unittest.mock import AsyncMock, MagicMock, patch

from modules.score_math import score_hundredths


class Session(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class GameOneTests(unittest.TestCase):
    def test_settles_once_using_the_displayed_fractional_digits(self):
        st, ai, db, common, tx = (MagicMock() for _ in range(5))
        st.button.return_value = False
        st.columns.side_effect = lambda count: [MagicMock() for _ in range(count)]
        ai.summary = AsyncMock(return_value="요약문")
        common.get_game_news_selection.return_value = ("제목", "본문", "url")
        sheet = db.init_gspread.return_value
        sheet.get_all_records.return_value = [{"학번": "1", "코인": 2000, "연승": 0}]
        dependencies = {
            "streamlit": st, "modules.news_ai": ai, "modules.db_handler": db,
            "modules.ui_components": MagicMock(), "views.ranking": MagicMock(),
            "games.shared.news_flow": MagicMock(get_game_news_selection=common.get_game_news_selection),
            "games.shared.betting": MagicMock(),
            "games.shared.loading": MagicMock(),
            "games.shared.result": MagicMock(),
            "games.shared.interest": MagicMock(apply_end_of_turn_interest=lambda game: True),
            "modules.transactions": tx,
            "streamlit.components": st.components,
            "streamlit.components.v1": st.components.v1,
        }
        with patch.dict(sys.modules, dependencies):
            play_round = run_module("games.game1.game1")["show_game_1"]
            for normalized, guess, wins in [
                (0.8704, 4, True), (0.8704, 87, False), (0.99995, 0, True)
            ]:
                with self.subTest(normalized=normalized, guess=guess):
                    units = score_hundredths(normalized)
                    ai.similarity_check.reset_mock()
                    tx.settle_game_round.reset_mock()
                    tx.settle_game_round.return_value = {
                        "reward": 100_000 if wins else -1000,
                        "new_coins": 102_000 if wins else 1000,
                        "new_streak": 1 if wins else 0,
                    }
                    ai.similarity_check.return_value = {"score": units / 100, "score_hundredths": units}
                    st.session_state = Session(
                        current_user="1", current_user_data={}, game_1_bet=1000,
                        game_1_predicted_digits=guess,
                    )
                    play_round()
                    play_round()
                    result = st.session_state.game_1_result
                    self.assertEqual(result["is_win"], wins)
                    self.assertEqual(result["reward"], 100_000 if wins else -1000)
                    ai.similarity_check.assert_called_once_with("요약문", "제목")
                    tx.settle_game_round.assert_called_once_with("game_1", 1000, wins)
