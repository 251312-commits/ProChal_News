"""Regression tests for betting math and rank preview.

Run from repository root:
    python -m unittest discover -s tests -v
"""

import unittest

from games.betting_math import (
    calculate_expected_gain,
    format_payout_multiplier,
    project_rank_change,
    project_standings,
    rank_by_coins,
    ranking_entries,
)


class BettingMathTests(unittest.TestCase):
    def test_dynamic_multiplier(self):
        self.assertEqual(calculate_expected_gain(500, 1.9), 950)
        self.assertEqual(calculate_expected_gain(500, 100), 50_000)
        self.assertEqual(calculate_expected_gain(100, 0), 0)
        self.assertEqual(format_payout_multiplier(1.9), "1.9x")
        self.assertEqual(format_payout_multiplier(100.0), "100x")

    def test_invalid_multipliers(self):
        for value in (-1, "NaN", float("inf"), "not a number", None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    calculate_expected_gain(500, value)

    def test_rank_climb_with_student_id(self):
        rows = [
            {"학번": "101", "아이디": "first", "코인": 2000},
            {"학번": "102", "아이디": "second", "코인": 1500},
            {"학번": "103.0", "아이디": "third", "코인": 1000},
        ]
        self.assertEqual(project_rank_change(rows, 1000, "103", "third", 950), (3, 2))
        self.assertEqual(project_rank_change(rows, 1000, "103", "third", 1001), (3, 1))

    def test_leaderboard_and_bet_rivals_use_net_coins(self):
        rows = [
            {"학번": "1", "코인": "8,500", "대출금": "6,000"},
            {"학번": "2", "코인": 1500, "대출금": ""},
            {"학번": "3", "코인": 1000, "대출금": 1200},
        ]
        leaderboard = rank_by_coins(ranking_entries(rows))
        self.assertEqual([u["coins"] for u in leaderboard], [2500, 1500, -200])
        before, after, rivals = project_standings(rows, 1000, "3", "", 2000)
        self.assertEqual((before, after), (3, 2))
        self.assertEqual([u["coins"] for u in rivals], [2500, 1800, 1500])
        self.assertEqual(rows[2]["코인"], 1000)

    def test_borrow_and_repay_do_not_move_a_players_rank(self):
        rows = [
            {"학번": "1", "코인": 1000},
            {"학번": "2", "코인": 5000, "대출금": 4500},
        ]
        for wallet, loan in ((500, 0), (5000, 4500), (1500, 1000)):
            with self.subTest(wallet=wallet, loan=loan):
                self.assertEqual(
                    project_rank_change(rows, wallet, "2", "", 600, current_loan=loan),
                    (2, 1),
                )

    def test_session_balance_overrides_cached_sheet_row(self):
        rows = [
            {"학번": "1", "아이디": "alpha", "코인": 1800},
            {"학번": "2", "아이디": "beta", "코인": 100},
            {"학번": "3", "아이디": "gamma", "코인": 1300},
        ]
        self.assertEqual(project_rank_change(rows, 1500, "2", "beta", 400), (2, 1))

    def test_ranking_page_tie_breaking_is_stable(self):
        rows = [
            {"학번": "1", "아이디": "A", "코인": 1000},
            {"학번": "2", "아이디": "B", "코인": 1000},
        ]
        self.assertEqual(project_rank_change(rows, 1000, "2", "B", 0), (2, 2))
        self.assertEqual(project_rank_change(rows, 1000, "2", "B", 50), (2, 1))

    def test_unique_nickname_fallback(self):
        rows = [
            {"학번": "100", "아이디": "A", "코인": 700},
            {"학번": "200", "아이디": "B", "코인": 600},
        ]
        self.assertEqual(project_rank_change(rows, 600, "unknown", "B", 200), (2, 1))

    def test_unknown_or_ambiguous_user_is_not_guessed(self):
        rows = [
            {"학번": "1", "아이디": "same", "코인": 1000},
            {"학번": "2", "아이디": "same", "코인": 950},
        ]
        self.assertEqual(project_rank_change([], 1000, "1", "same", 50), (None, None))
        self.assertEqual(project_rank_change(rows, 1000, "unknown", "same", 50), (None, None))
        self.assertEqual(project_rank_change(rows, 1000, "", "", 50), (None, None))

    def test_coin_parsing_from_google_sheets(self):
        rows = [
            {"학번": "1", "아이디": "A", "코인": "1,000"},
            {"학번": "2", "아이디": "B", "코인": "900.0"},
        ]
        self.assertEqual(project_rank_change(rows, 900, "2", "B", 150), (2, 1))


if __name__ == "__main__":
    unittest.main()
