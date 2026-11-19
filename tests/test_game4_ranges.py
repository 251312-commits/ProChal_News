"""Regression tests for game4's three percentage ranges."""

import sys
import unittest
from decimal import Decimal
from runpy import run_module
from unittest.mock import MagicMock, patch


class GameFourRangeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        dependencies = {
            "streamlit": MagicMock(),
            "streamlit.components": MagicMock(),
            "streamlit.components.v1": MagicMock(),
            "games.shared.betting": MagicMock(),
            "games.shared.news_flow": MagicMock(),
            "games.shared.loading": MagicMock(),
            "games.shared.interest": MagicMock(),
            "modules.transactions": MagicMock(),
            "modules.news_ai": MagicMock(),
            "modules.ui_components": MagicMock(),
            "views.ranking": MagicMock(),
        }
        with patch.dict(sys.modules, dependencies):
            cls.build_ranges = staticmethod(
                run_module("games.game4")["_build_dynamic_ranges"]
            )

    @staticmethod
    def _to_units(label):
        lower, upper = label.rstrip("%").split("~")
        return int(Decimal(lower) * 100), int(Decimal(upper) * 100)

    def test_correct_numeric_position_is_uniformly_selectable(self):
        expected = (
            ["74.00~75.99%", "76.00~77.99%", "78.00~79.99%"],
            ["72.00~73.99%", "74.00~75.99%", "76.00~77.99%"],
            ["70.00~71.99%", "72.00~73.99%", "74.00~75.99%"],
        )
        with patch("random.choice", side_effect=[0, 1, 2]) as pick:
            for index, ranges_expected in enumerate(expected):
                ranges, answer_index = self.build_ranges(74.25)
                self.assertEqual(answer_index, index)
                self.assertEqual(ranges, ranges_expected)
            self.assertTrue(
                all(call.args[0] == [0, 1, 2] for call in pick.call_args_list)
            )

    def test_boundary_scores_offer_only_valid_positions(self):
        cases = (
            (0.00, [0]),
            (1.99, [0]),
            (2.00, [0, 1]),
            (3.99, [0, 1]),
            (4.00, [0, 1, 2]),
            (95.99, [0, 1, 2]),
            (96.00, [1, 2]),
            (97.99, [1, 2]),
            (98.00, [2]),
            (99.99, [2]),
        )
        for score, expected_positions in cases:
            with self.subTest(score=score):
                with patch("random.choice", side_effect=lambda options: options[-1]) as pick:
                    ranges, answer_index = self.build_ranges(score)
                self.assertEqual(pick.call_args.args[0], expected_positions)
                self.assertEqual(answer_index, expected_positions[-1])
                self.assertTrue(0 <= self._to_units(ranges[0])[0])
                self.assertTrue(self._to_units(ranges[-1])[1] <= 9999)

    def test_every_possible_score_has_one_exact_correct_range(self):
        # Both ends of the valid-position set, across every hundredth
        # between 0.00% and 99.99%, including all boundary values.
        for selector in (lambda positions: positions[0],
                         lambda positions: positions[-1]):
            with patch("random.choice", side_effect=selector):
                for score_units in range(10000):
                    score = score_units / 100
                    ranges, answer_index = self.build_ranges(score)
                    parsed = [self._to_units(label) for label in ranges]
                    self.assertEqual(len(parsed), 3)
                    for index, (lower, upper) in enumerate(parsed):
                        self.assertEqual(upper - lower, 199)
                        self.assertTrue(0 <= lower <= upper <= 9999)
                        if index > 0:
                            self.assertEqual(lower, parsed[index - 1][1] + 1)
                    matches = [
                        index for index, (lower, upper) in enumerate(parsed)
                        if lower <= score_units <= upper
                    ]
                    self.assertEqual(matches, [answer_index])


if __name__ == "__main__":
    unittest.main()
