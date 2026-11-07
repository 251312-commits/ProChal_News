"""Regression tests: repository image URLs render without runtime static copies."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from modules import ui_components as ui


ROOT = Path(__file__).resolve().parents[1]


class PublicAssetUrlTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.assets = self.root / "assets"
        self.picture = self.assets / "bank" / "card.avif"
        self.picture.parent.mkdir(parents=True)
        self.picture.write_bytes(b"original avif image")
        mock_root = patch.object(ui, "_ASSETS_ROOT", self.assets)
        mock_root.start()
        self.addCleanup(mock_root.stop)

    def test_large_assets_use_short_public_urls_without_base64_or_static_copy(self):
        with patch.object(ui, "load_local_image_as_base64", side_effect=AssertionError):
            url = ui.load_local_image_url(str(self.picture))
            parsed = urlsplit(url)
            self.assertEqual(parsed.scheme, "https")
            self.assertEqual(parsed.netloc, "raw.githubusercontent.com")
            self.assertEqual(
                parsed.path,
                "/251312-commits/ProChal_News/main/assets/bank/card.avif",
            )
            self.assertIn("v", parse_qs(parsed.query))
            self.assertNotIn("base64", url)
            self.assertNotIn("/app/static/", url)
            self.assertEqual(ui.load_local_image_url(str(self.picture)), url)
        self.assertFalse((self.root / "static").exists())

    def test_changed_asset_has_new_cache_version(self):
        first = ui.load_local_image_url(str(self.picture))
        self.picture.write_bytes(b"updated image with different length")
        second = ui.load_local_image_url(str(self.picture))
        self.assertNotEqual(first, second)

    def test_small_svg_keeps_safe_inline_image(self):
        icon = self.assets / "bank" / "crest.svg"
        icon.write_text("<svg xmlns='http://www.w3.org/2000/svg'></svg>")
        with patch.object(
            ui, "load_local_image_as_base64", return_value="data:image/svg+xml;base64,AA=="
        ) as loader:
            self.assertEqual(
                ui.load_local_image_url(str(icon)),
                "data:image/svg+xml;base64,AA==",
            )
            loader.assert_called_once_with(str(icon))

    def test_rejects_files_outside_assets_and_unknown_extensions(self):
        outside = self.root / "private.png"
        outside.write_bytes(b"private")
        with self.assertRaises(ValueError):
            ui.load_local_image_url(str(outside))
        other = self.assets / "secret.txt"
        other.write_text("not an image")
        with self.assertRaises(ValueError):
            ui.load_local_image_url(str(other))

    def test_public_urls_match_actual_repository_assets(self):
        # This test uses the real checked-in assets, not the setUp fixture.
        with patch.object(ui, "_ASSETS_ROOT", ROOT / "assets"):
            for relative in (
                "banner1.png", "bet_background.jpg", "bet_podium.png",
                "bank/bank_envelope_open.avif",
                "news_slot/news_slot_frame.webp",
                "game1_article/reader-frame.webp",
            ):
                with self.subTest(relative=relative):
                    url = ui.load_local_image_url(str(ROOT / "assets" / relative))
                    self.assertIn("/main/assets/" + relative, url)

    def test_large_image_callers_use_shared_url_loader(self):
        for path in (
            "views/main.py", "views/bank/bank.py", "views/bank/draw.py",
            "views/bank/scene.py", "games/game1/game1.py",
            "games/shared/article_reader.py", "games/shared/roulette.py",
            "games/shared/betting.py", "games/shared/result.py",
        ):
            with self.subTest(path=path):
                content = (ROOT / path).read_text(encoding="utf-8")
                self.assertIn("load_local_image_url", content)
                self.assertNotIn("load_local_image_as_base64(", content)
        result = (ROOT / "games/shared/result.py").read_text(encoding="utf-8")
        self.assertNotIn("b64encode(asset.read_bytes())", result)

    def test_runtime_generated_static_assets_are_not_required(self):
        helper = (ROOT / "modules/ui_components.py").read_text(encoding="utf-8")
        self.assertNotIn("_STATIC_ASSETS_ROOT", helper)
        self.assertNotIn("enableStaticServing", helper)
        self.assertFalse((ROOT / "static" / "README.md").exists())


if __name__ == "__main__":
    unittest.main()
