"""Pure badge engine tests: no Streamlit or Google Sheets connection required."""
import unittest

from modules.badges import BADGES, BADGE_BY_ID, equipped_badge, evaluate_achievements, parse_owned, serialize_owned


def round_(i, game="game_1", won=False, **kwargs):
    return {"round_id": f"r{i}", "game": game, "is_win": won, **kwargs}


class BadgeTests(unittest.TestCase):
    def test_catalog_has_twenty_five_unique_badges(self):
        self.assertEqual(len(BADGES), 25)
        self.assertEqual(len(BADGE_BY_ID), 25)
        self.assertEqual(sum(b.rarity == "legendary" for b in BADGES), 5)
        self.assertEqual(sum(b.rarity == "mythic" for b in BADGES), 2)
        self.assertEqual([b.id for b in BADGES][-5:], ["all_legendary", "bankrupt", "loan_survivor", "first_borrow", "first_repay"])

    def test_owned_and_equip_validation(self):
        self.assertEqual(parse_owned("g1_hit unknown g1_hit first_round"), ("g1_hit", "first_round"))
        self.assertEqual(serialize_owned(["g1_hit", "first_round", "g1_hit"]), "first_round g1_hit")
        self.assertIsNone(equipped_badge("g1_hit", ["first_round"]))
        self.assertIsNone(equipped_badge("0", ["g1_hit"]))
        self.assertEqual(equipped_badge("g1_hit", ["g1_hit"]).title, "소수점의 지배자")

    def test_near_miss_stacks_and_duplicate_round_is_ignored(self):
        events = [round_(1, won=False, predicted_digits=37, answer_digits=36)]
        earned = evaluate_achievements(events + events)
        self.assertTrue({"first_round", "g1_within_ten", "g1_within_three", "g1_exact_one"} <= earned)
        self.assertNotIn("g1_hit", earned)

    def test_exact_tenth_and_hit(self):
        events = [round_(1, won=False, predicted_digits=37, answer_digits=27),
                  round_(2, won=True, predicted_digits=17, answer_digits=17)]
        earned = evaluate_achievements(events)
        self.assertTrue({"g1_exact_ten", "g1_hit"} <= earned)

    def test_mixed_streak_and_reset(self):
        events = [round_(i, game=f"game_{(i % 3) + 1}", won=True) for i in range(1, 9)]
        earned = evaluate_achievements(events)
        self.assertTrue({"streak_three", "streak_five_mixed", "streak_eight_mixed"} <= earned)
        events = [round_(1, won=True), round_(2, won=True), round_(3, won=False),
                  round_(4, won=True), round_(5, won=True)]
        self.assertNotIn("streak_three", evaluate_achievements(events))

    def test_game_specific_streak_ignores_other_games(self):
        events = [round_(1, "game_3", True), round_(2, "game_2", False)]
        events += [round_(i, "game_3", True) for i in range(3, 7)]
        self.assertIn("g3_five_streak", evaluate_achievements(events))

    def test_no_awards_for_invalid_or_unsettled_events(self):
        self.assertFalse(evaluate_achievements([{"game": "game_1", "is_win": True}]))
        self.assertFalse(evaluate_achievements([{"round_id": "x", "game": "game_1", "is_win": 1}]))


if __name__ == "__main__":
    unittest.main()
