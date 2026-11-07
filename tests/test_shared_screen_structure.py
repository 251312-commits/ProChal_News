"""Static architecture and syntax regressions for reusable game screens."""
import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
GAMES = ROOT / "games"
SHARED = GAMES / "shared"


class SharedScreenStructureTests(unittest.TestCase):
    def test_all_shared_modules_and_games_parse(self):
        names = [
            "betting.py", "news_flow.py", "roulette.py",
            "article_reader.py", "loading.py",
        ]
        for path in [
            *(SHARED / name for name in names),
            GAMES / "game1" / "game1.py",
            *(GAMES / f"game{i}.py" for i in range(2, 6)),
            SHARED / "result.py",
            SHARED / "interest.py",
            ROOT / "news.py",
        ]:
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file(), path)
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_each_result_applies_interest_before_reveal(self):
        files = [
            GAMES / "game1" / "game1.py",
            *(GAMES / f"game{i}.py" for i in range(2, 6)),
        ]
        for index, game_file in enumerate(files, start=1):
            source = game_file.read_text(encoding="utf-8")
            self.assertIn("from games.shared.interest import apply_end_of_turn_interest", source)
            self.assertIn(f'if not apply_end_of_turn_interest("game_{index}"):', source)

    def test_game_one_only_screens_are_in_its_own_module(self):
        source = (GAMES / "game1" / "game1.py").read_text(encoding="utf-8")
        self.assertIn("def render_game1_prediction_picker(", source)
        self.assertIn("def show_game_1_tutorial(", source)
        for obsolete in [
            "game1_prediction_ui.py", "game1_tutorial.py",
            "game1_article_ui.py", "news_roulette.py", "news_roulette2.py",
        ]:
            self.assertFalse((GAMES / obsolete).exists(), obsolete)

    def test_game_specific_rules_reuse_betting_and_news_screens(self):
        for game in range(1, 6):
            game_file = GAMES / "game1" / "game1.py" if game == 1 else GAMES / f"game{game}.py"
            source = game_file.read_text(encoding="utf-8")
            with self.subTest(game=game):
                self.assertIn("render_betting_ui", source)
        source = (GAMES / "game2.py").read_text(encoding="utf-8")
        self.assertIn("immersive_reader=True", source)
        self.assertNotIn("from games.news_roulette2", source)
        roulette = (SHARED / "roulette.py").read_text(encoding="utf-8")
        self.assertIn("round_id", roulette)
        self.assertIn("allow_direct_url", roulette)
        self.assertIn("allow_back", roulette)
        reader = (SHARED / "article_reader.py").read_text(encoding="utf-8")
        self.assertIn('round_key = f"{game_id}_reader_round"', reader)

    def test_game_ui_assets_remain_resolvable(self):
        self.assertTrue((SHARED / "low_balance.css").is_file())
        self.assertTrue((SHARED / "similarity_loading.css").is_file())
        self.assertTrue((SHARED / "news_slot" / "slot.js").is_file())
        self.assertTrue((SHARED / "article_reader" / "reader.js").is_file())
        for frontend, scripts in {
            "article_reader": ("index.html", "reader.css", "reader.js"),
            "news_slot": ("index.html", "slot.css", "slot.js"),
        }.items():
            for filename in scripts:
                with self.subTest(frontend=frontend, filename=filename):
                    self.assertTrue((SHARED / frontend / filename).is_file())
            self.assertFalse((GAMES / frontend).exists(), frontend)
        reader = (SHARED / "article_reader.py").read_text(encoding="utf-8")
        roulette = (SHARED / "roulette.py").read_text(encoding="utf-8")
        self.assertIn('HERE = Path(__file__).resolve().parent', reader)
        self.assertIn('HERE = Path(__file__).resolve().parent', roulette)
        self.assertIn('path=str(HERE / "article_reader")', reader)
        self.assertIn('path=str(HERE / "news_slot")', roulette)
        self.assertIn('ASSETS = HERE.parents[1] / "assets"', reader)
        self.assertIn('ASSETS = HERE.parents[1] / "assets"', roulette)
        self.assertTrue((GAMES / "game1" / "prediction_screen" / "prediction.js").is_file())
        self.assertTrue((GAMES / "game1" / "game1_tutorial.css").is_file())
        self.assertFalse((GAMES / "game1.py").exists())
        self.assertFalse((GAMES / "game1_tutorial.css").exists())
        self.assertFalse((GAMES / "prediction_screen").exists())
        for obsolete in ("common.py", "betting_math.py", "result_reveal.py", "score_stage.py"):
            self.assertFalse((GAMES / obsolete).exists(), obsolete)


if __name__ == "__main__":
    unittest.main()
