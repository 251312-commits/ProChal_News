"""Regression tests for a fixed-height, six-slot ranking list."""

import unittest

from views.ranking_display import select_ranking_rows


class RankingDisplayTests(unittest.TestCase):
    def test_top_ranks_show_four_through_nine(self):
        for my_rank in (1, 3, 4, 5, 6, 7):
            with self.subTest(rank=my_rank):
                self.assertEqual(select_ranking_rows(40, my_rank), [4, 5, 6, 7, 8, 9])

    def test_middle_rank_preserves_gap_and_neighbors(self):
        self.assertEqual(select_ranking_rows(40, 8), [4, 5, "...", 7, 8, 9])
        self.assertEqual(select_ranking_rows(40, 23), [4, 5, "...", 22, 23, 24])

    def test_last_and_second_last_rows_shift_up(self):
        self.assertEqual(select_ranking_rows(40, 39), [4, 5, "...", 38, 39, 40])
        self.assertEqual(select_ranking_rows(40, 40), [4, 5, "...", 38, 39, 40])

    def test_small_leaderboards_use_empty_slots_to_keep_height(self):
        self.assertEqual(select_ranking_rows(9, 9), [4, 5, 6, 7, 8, 9])
        self.assertEqual(select_ranking_rows(7, 7), [4, 5, 6, 7, None, None])
        self.assertEqual(select_ranking_rows(4, 4), [4, None, None, None, None, None])
        self.assertEqual(select_ranking_rows(3, 3), [None] * 6)

    def test_missing_user_shows_first_six_lower_ranks(self):
        self.assertEqual(select_ranking_rows(40, 0), [4, 5, 6, 7, 8, 9])

    def test_six_valid_slots_for_every_possible_rank(self):
        for total in range(1, 51):
            for my_rank in range(1, total + 1):
                with self.subTest(total=total, my_rank=my_rank):
                    rows = select_ranking_rows(total, my_rank)
                    numeric_ranks = [r for r in rows if isinstance(r, int)]
                    self.assertEqual(len(rows), 6)
                    self.assertEqual(numeric_ranks, sorted(set(numeric_ranks)))
                    self.assertTrue(all(4 <= r <= total for r in numeric_ranks))
                    self.assertLessEqual(rows.count("..."), 1)
                    if my_rank >= 4:
                        self.assertIn(my_rank, numeric_ranks)


if __name__ == "__main__":
    unittest.main()
