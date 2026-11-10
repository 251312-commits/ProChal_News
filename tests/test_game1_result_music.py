"""Regression coverage for Game 1's music-driven decimal reveal."""
from pathlib import Path
import unittest

from games.game1.result_reveal import RESULT_TRACKS, reveal_order


ROOT = Path(__file__).resolve().parents[1]


class ResultMusicTests(unittest.TestCase):
    def test_five_tracks_have_the_provided_drop_points(self):
        self.assertEqual(RESULT_TRACKS, (
            ("result1.mp3", 9.7, 13.2, 48.5),
            ("result2.mp3", 13.2, 15.4, 31.6),
            ("result3.mp3", 8.7, 12.8, 43.1),
            ("result4.mp3", 8.9, 11.0, 24.6),
            ("result5.mp3", 9.7, 12.0, 27.9),
        ))
        for filename, first, second, end in RESULT_TRACKS:
            self.assertTrue((ROOT / "sounds" / filename).is_file(), filename)
            self.assertTrue(0 < first < second < end)
        self.assertTrue((ROOT / "sounds" / "fail.mp3").is_file())

    def test_matching_digit_is_revealed_first_without_switching_its_place(self):
        # Target 87.02, guess 04: first decimal (0) matches.
        self.assertEqual(reveal_order(4, 8702), ([0, 1], [True, False]))
        # Target 87.24, guess 04: second decimal (4) matches.
        self.assertEqual(reveal_order(4, 8724), ([1, 0], [False, True]))
        # No matches: fail before the first drop.
        self.assertEqual(reveal_order(4, 8752), ([0, 1], [False, False]))
        # Exact match: both beats are earned.
        self.assertEqual(reveal_order(4, 8704), ([0, 1], [True, True]))
        # A rounded 100.00 remains 00, not a third decimal digit.
        self.assertEqual(reveal_order(0, 10000), ([0, 1], [True, True]))

    def test_music_clock_and_cutoff_events_live_in_frontend(self):
        js = (ROOT / "games/game1/result_screen/result.js").read_text(encoding="utf-8")
        for marker in (
            "song.currentTime",
            "spec.drop1 - 0.12",
            "spec.drop2 - 0.12",
            "song.pause()", "failSound.play()",
            "requestAnimationFrame(tick)",
            "revealDigit(args.reveal_order[0])",
            "revealDigit(args.reveal_order[1])",
            'send("streamlit:setComponentValue"',
            "ui.wallet.hidden = true",
        ):
            self.assertIn(marker, js)

    def test_score_is_settled_before_visual_reveal_and_bgm_is_suspended(self):
        game1 = (ROOT / "games/game1/game1.py").read_text(encoding="utf-8")
        self.assertLess(
            game1.index('settle_game_round("game_1"'),
            game1.index("render_game1_result_reveal(res)"),
        )
        self.assertLess(
            game1.index('apply_end_of_turn_interest("game_1")'),
            game1.index("render_game1_result_reveal(res)"),
        )
        bgm = (ROOT / "sounds/bgm.py").read_text(encoding="utf-8")
        self.assertIn("host.__newsResultActive", bgm)
        self.assertIn("suspend_for_result", bgm)


if __name__ == "__main__":
    unittest.main()
