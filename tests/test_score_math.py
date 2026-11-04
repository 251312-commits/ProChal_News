import unittest

from modules.score_math import score_hundredths


class ScoreMathTests(unittest.TestCase):
    def test_rounds_once_in_hundredths_of_a_point(self):
        for normalized, expected in [
            (0.0, 0),
            (0.00005, 1),     # 0.005 points -> 0.01
            (0.8704, 8704),  # 87.04, a leading-zero prediction
            (0.87045, 8705),  # halfway between 87.04 and 87.05
            (0.879949, 8799),
            (0.87995, 8800),  # rounding carries into the whole part
            (0.999949, 9999),
            (0.99995, 10000),
            (1.0, 10000),
        ]:
            with self.subTest(normalized=normalized):
                self.assertEqual(score_hundredths(normalized), expected)
