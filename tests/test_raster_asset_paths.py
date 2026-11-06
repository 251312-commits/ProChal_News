"""Protect the repository's PNG/JPEG layout and module-relative image paths."""
import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}


class RasterAssetPathTests(unittest.TestCase):
    def test_all_png_and_jpeg_files_live_under_assets(self):
        rasters = [
            path for path in ROOT.rglob("*")
            if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
            and ".git" not in path.parts
        ]
        self.assertTrue(rasters, "No PNG or JPEG assets were found")
        for path in rasters:
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertTrue(path.is_relative_to(ASSETS))

    def test_static_python_raster_filenames_exist_in_assets(self):
        # Catch outdated hard-coded names without importing database or Streamlit.
        for code in (*ROOT.glob("games/*.py"), *ROOT.glob("views/*.py"),
                     *ROOT.glob("modules/*.py")):
            tree = ast.parse(code.read_text(encoding="utf-8"), filename=str(code))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                    continue
                name = node.value
                if Path(name).suffix.lower() not in IMAGE_SUFFIXES:
                    continue
                # Code may name assets by basename or by path relative to assets/.
                relative = name.removeprefix("assets/")
                with self.subTest(code=code.name, asset=name):
                    self.assertTrue(
                        (ASSETS / relative).is_file()
                        or any(path.is_file() for path in ASSETS.rglob(Path(relative).name)),
                        f"{code.relative_to(ROOT)} references a missing image: {name}",
                    )

    def test_image_call_sites_do_not_depend_on_current_working_directory(self):
        common = (ROOT / "games/common.py").read_text(encoding="utf-8")
        main = (ROOT / "views/main.py").read_text(encoding="utf-8")
        game1 = (ROOT / "games/game1.py").read_text(encoding="utf-8")
        self.assertIn('Path(__file__).resolve().parents[1] / "assets"', common)
        self.assertIn('str(_ASSET_ROOT / filename)', common)
        self.assertIn('Path(__file__).resolve().parents[1] / "assets"', main)
        self.assertIn('str(assets_dir / f"banner{index}.png")', main)
        self.assertIn(' / "assets" / "bet_background.jpg"', game1)
        self.assertNotIn('bg_image_path="assets/bg.png"', game1)

    def test_expected_root_images_exist(self):
        for name in (
            *(f"banner{i}.png" for i in range(1, 8)),
            "bet_background.jpg", "bet_crown.png", "bet_news_cards.png",
            "bet_podium.png", "bet_coin_stack.png",
        ):
            with self.subTest(name=name):
                self.assertTrue((ASSETS / name).is_file(), name)


if __name__ == "__main__":
    unittest.main()
