"""Reruns and failed wallet writes never re-run AI on one article/round."""
import sys
import unittest
from pathlib import Path
from runpy import run_module
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from games.shared.round_analysis import analyze_round_once


class Session(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class FakeTransactionError(RuntimeError):
    pass


class FakeBalanceChanged(FakeTransactionError):
    def __init__(self, balances=None):
        self.balances = balances or {}
        super().__init__("balance changed")


class RoundAnalysisTests(unittest.TestCase):
    def test_summary_and_score_are_reused_after_an_unsettled_attempt(self):
        state = Session(current_user="user-a", game_1_round_id="round-1")
        summarize = AsyncMock(return_value="요약 한 번")
        similarity = Mock(return_value={"score": 72.13, "score_hundredths": 7213})

        def analyze():
            return analyze_round_once(
                state, "game_1", title="기사 A", article_text="기사 본문",
                summarize=summarize, similarity=similarity,
            )

        first = analyze()
        second = analyze()  # Retrying a wallet settlement reuses the verdict.
        self.assertEqual(first, second)
        summarize.assert_awaited_once_with("기사 본문")
        similarity.assert_called_once_with("요약 한 번", "기사 A")

    def test_failed_scoring_preserves_successful_summary(self):
        state = Session(current_user="user-a", game_3_round_id="round-3")
        summarize = AsyncMock(return_value="요약")
        similarity = Mock(side_effect=[
            RuntimeError("model busy"), {"score": 31.72},
        ])
        args = dict(title="제목", article_text="기사", summarize=summarize,
                    similarity=similarity)
        with self.assertRaises(RuntimeError):
            analyze_round_once(state, "game_3", **args)
        result = analyze_round_once(state, "game_3", **args)
        self.assertEqual(result[1]["score"], 31.72)
        summarize.assert_awaited_once()
        self.assertEqual(similarity.call_count, 2)

    def test_article_user_and_round_changes_invalidate_checkpoint(self):
        state = Session(current_user="u", game_2_round_id="r1")
        summarize = AsyncMock(return_value="요약")
        similarity = Mock(return_value={"score": 80.0})
        def call(text):
            return analyze_round_once(state, "game_2", title="제목",
                article_text=text, summarize=summarize, similarity=similarity)
        call("기사 A")
        call("기사 B")
        state["game_2_round_id"] = "r2"
        call("기사 B")
        state["current_user"] = "another"
        call("기사 B")
        self.assertEqual(summarize.await_count, 4)
        self.assertEqual(similarity.call_count, 4)

    def test_fallback_and_invalid_scores(self):
        state = Session()
        summarize = AsyncMock(return_value=None)
        similarity = Mock(return_value={"score": 54.67})
        result = analyze_round_once(
            state, "game_2", title="기사 제목", article_text="본문",
            summarize=summarize, similarity=similarity, fallback_to_title=True,
        )
        self.assertEqual(result[0], "기사 제목")
        self.assertEqual(similarity.call_args.args, ("기사 제목", "기사 제목"))
        self.assertEqual(analyze_round_once(
            state, "game_2", title="기사 제목", article_text="본문",
            summarize=summarize, similarity=similarity, fallback_to_title=True,
        ), result)
        summarize.assert_awaited_once()

        bad = Mock(return_value={"score": float("nan")})
        with self.assertRaises(ValueError):
            analyze_round_once({}, "game_1", title="t", article_text="text",
                summarize=AsyncMock(return_value="s"), similarity=bad)


class RoundSettlementRegressionTests(unittest.TestCase):
    def _fakes(self):
        st, ai, tx = MagicMock(), MagicMock(), MagicMock()
        st.button.return_value = False
        st.columns.side_effect = lambda sizes, **_kw: [
            MagicMock() for _ in range(sizes if isinstance(sizes, int) else len(sizes))
        ]
        ai.summary = AsyncMock(return_value="요약")
        ai.similarity_check.return_value = {
            "score": 74.25, "score_hundredths": 7425,
            "model_name": "test", "logit": 1.0, "normalized": .7425, "token_count": 10,
        }
        tx.TransactionError = FakeTransactionError
        tx.BalanceChanged = FakeBalanceChanged
        tx.settle_game_round.side_effect = [
            FakeTransactionError("temporary gateway failure"),
            {"reward": -1000, "new_coins": 4000, "new_streak": 0},
        ]
        deps = {
            "streamlit": st, "modules.news_ai": ai, "modules.ui_components": MagicMock(),
            "modules.db_handler": MagicMock(), "views.ranking": MagicMock(),
            "games.shared.news_flow": MagicMock(), "games.shared.betting": MagicMock(),
            "games.shared.loading": MagicMock(), "games.shared.result": MagicMock(),
            "games.shared.interest": MagicMock(apply_end_of_turn_interest=lambda g: True),
            "modules.transactions": tx,
            "streamlit.components": st.components,
            "streamlit.components.v1": st.components.v1,
            "games.game1.result_reveal": MagicMock(),
        }
        deps["games.shared.news_flow"].get_game_news_selection.return_value = (
            "기사 제목", "기사 본문", "https://example.com/story",
        )
        return st, ai, tx, deps

    def test_game1_and_game2_retry_settlement_without_recomputing(self):
        for name, module_name, fn, state_keys in (
            ("game_1", "games.game1.game1", "show_game_1",
             dict(game_1_bet=1000, game_1_predicted_digits=55)),
            ("game_2", "games.game2", "show_game_2",
             dict(game_2_tutorial_done=True, game_2_bet=1000,
                  game_2_target_num=90, game_2_user_choice="HIGH")),
        ):
            with self.subTest(game=name):
                st, ai, tx, deps = self._fakes()
                st.session_state = Session(current_user="1", current_user_data={}, **state_keys)
                with patch.dict(sys.modules, deps):
                    run = run_module(module_name)[fn]
                    run()   # TransactionError
                    self.assertNotIn(name + "_result", st.session_state)
                    run()   # Gateway recovered, cached score reused
                ai.summary.assert_awaited_once_with("기사 본문")
                ai.similarity_check.assert_called_once_with("요약", "기사 제목")
                self.assertEqual(tx.settle_game_round.call_count, 2)
                self.assertIn(name + "_result", st.session_state)

    def test_game3_reuses_selected_shared_article_on_retry(self):
        st, ai, tx, deps = self._fakes()
        st.session_state = Session(
            current_user="1", current_user_data={}, game_3_bet=1000,
            game_3_choice="홀", read_done_game_3=True,
            selected_news_game_3={
                "title": "기사 제목", "text": "기사 본문",
                "url": "https://example.com/story",
            },
        )
        st.button.return_value = True
        with patch.dict(sys.modules, deps):
            analyze = run_module("games.game3")["analyze_game_3"]
            analyze()
            self.assertNotIn("game_3_result", st.session_state)
            analyze()
        ai.summary.assert_awaited_once()
        ai.similarity_check.assert_called_once()
        self.assertEqual(tx.settle_game_round.call_count, 2)
        self.assertIn("game_3_result", st.session_state)

    def test_game4_reuses_summary_if_scoring_fails_and_is_retried(self):
        st, ai, tx, deps = self._fakes()
        st.session_state = Session(
            current_user="1", current_user_data={"코인": 5000}, game_4_bet=1000,
        )
        ai.similarity_check.side_effect = [
            RuntimeError("inference unavailable"),
            {"score": 74.25, "score_hundredths": 7425},
        ]
        with patch.dict(sys.modules, deps):
            show = run_module("games.game4")["show_game_4"]
            show.__globals__["_render_game_4_range_picker"] = Mock(return_value=None)
            show()
            self.assertNotIn("game_4_score", st.session_state)
            show()
        ai.summary.assert_awaited_once_with("기사 본문")
        self.assertEqual(ai.similarity_check.call_count, 2)
        self.assertEqual(st.session_state["game_4_score"], 74.25)

    def test_game5_candidate_analysis_is_once_per_article(self):
        st, ai, tx, deps = self._fakes()
        with patch.dict(sys.modules, deps):
            scorer = run_module("games.game5")["_score_article_once"]
        load = Mock(side_effect=lambda article: article.__setitem__("text", "본문"))
        score = Mock(side_effect=lambda article: article.update(
            score=64.3, summary="요약", score_details={"score": 64.3},
        ) or 64.3)
        scorer.__globals__["_load_article"] = load
        scorer.__globals__["_calculate_score"] = score
        candidate = {"title": "기사", "url": "https://example.com/x", "text": ""}
        self.assertEqual(scorer(candidate), 64.3)
        self.assertEqual(scorer(candidate), 64.3)
        load.assert_called_once()
        score.assert_called_once()


class ObsoleteCodeContracts(unittest.TestCase):
    def test_shared_news_reader_has_no_legacy_streamlit_layout(self):
        root = Path(__file__).resolve().parents[1]
        news = (root / "games/shared/news_flow.py").read_text(encoding="utf-8")
        self.assertNotIn("components.html(", news)
        self.assertNotIn("pixel-window-header", news)
        self.assertNotIn("immersive_reader", news)
        self.assertIn("render_news_slot(", news)
        self.assertIn("render_article_reader(", news)

    def test_all_game_rounds_keep_checkpoints_isolated(self):
        root = Path(__file__).resolve().parents[1]
        for game in (1, 2, 3, 4):
            path = ("games/game1/game1.py" if game == 1 else f"games/game{game}.py")
            code = (root / path).read_text(encoding="utf-8")
            self.assertIn("analyze_round_once(", code)
            self.assertNotIn("asyncio.run(summary(", code)
        result_css = (root / "games/game4_ui/result.css").read_text(encoding="utf-8")
        self.assertIn(".g4-final-value", result_css)
        self.assertNotIn("game4_picker_shell", result_css)


if __name__ == "__main__":
    unittest.main()
