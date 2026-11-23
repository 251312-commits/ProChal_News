"""Keep all five visible payout multipliers aligned with Apps Script settlement."""

from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


def source(path):
    return (ROOT / path).read_text(encoding="utf-8")


class GamePayoutConsistencyTests(unittest.TestCase):
    def test_apps_script_net_win_rules_match_product_spec(self):
        script = source("apps_script/Code.gs")
        self.assertIn(
            "const RULES = {game_1: 100, game_2: 2, game_3: 2, game_4: 3, game_5: 5};",
            script,
        )
        self.assertIn("const LEGACY_WIN_RULES = {game_2: 1, game_3: 1, game_4: 2};", script)
        self.assertIn("settlementDeltaMatches_", script)
        self.assertIn("tx.delta = tx.is_win ? tx.bet * RULES[tx.game]", script)
        # Fresh losses use the entire stake; only historical Game 3 receipts
        # retain the old half-stake delta on idempotent replay.
        self.assertIn(
            "tx.delta = tx.is_win ? tx.bet * RULES[tx.game] : -tx.bet;", script,
        )
        self.assertIn(
            "(!isWin && game === 'game_3' && storedDelta === -Math.floor(bet / 2))",
            script,
        )

    def test_python_game_payout_previews_are_consistent(self):
        games = {
            "games/game1/game1.py": ("GAME_1_WIN_MULTIPLIER", "100.0"),
            "games/game2.py": ("GAME_2_WIN_MULTIPLIER", "2.0"),
            "games/game3.py": ("GAME_3_WIN_MULTIPLIER", "2.0"),
            "games/game4.py": ("GAME_4_WIN_MULTIPLIER", "3.0"),
            "games/game5.py": ("GAME_5_WIN_MULTIPLIER", "5.0"),
        }
        for path, (name, value) in games.items():
            with self.subTest(game=path):
                content = source(path)
                self.assertIn(f"{name} = {value}", content)
                self.assertIn(f"payout_multiplier={name}", content)

        for game in ("games/game2.py", "games/game3.py", "games/game4.py"):
            content = source(game)
            self.assertRegex(content, r"win_multiplier=GAME_[234]_WIN_MULTIPLIER")

        self.assertIn("정답 +베팅액의 2배 · 오답 −베팅액 전부", source("games/game3.py"))
        self.assertIn("예측에 성공하면 베팅액의 2배를 획득하고, 실패하면 베팅액이 차감됩니다.", source("games/game2.py"))

    def test_documentation_uses_net_gain_not_gross_return(self):
        notes = source("docs/transaction-ledger.md")
        for game, net_gain in [(1, 100), (2, 2), (3, 2), (4, 3), (5, 5)]:
            self.assertIn(f"| {game} | +{net_gain}× |", notes)


if __name__ == "__main__":
    unittest.main()
