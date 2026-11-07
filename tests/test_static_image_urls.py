"""Regression tests for short, cacheable Streamlit static image URLs."""

from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from modules import ui_components as ui


ROOT = Path(__file__).resolve().parents[1]


class StaticImageUrlTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        self.asset_root = root / "assets"
        self.static_root = root / "static" / "assets"
        self.source = self.asset_root / "bank" / "card.avif"
        self.source.parent.mkdir(parents=True)
        self.source.write_bytes(b"sample image version one")
        self.enabled = True
        self.base_path = "nested/app"

        for context in (
            patch.object(ui, "_ASSETS_ROOT", self.asset_root),
            patch.object(ui, "_STATIC_ASSETS_ROOT", self.static_root),
            patch.object(ui.st, "get_option", side_effect=self._get_option),
        ):
            context.start()
            self.addCleanup(context.stop)

    def _get_option(self, name):
        if name == "server.enableStaticServing":
            return self.enabled
        if name == "server.baseUrlPath":
            return self.base_path
        raise AssertionError(f"Unexpected Streamlit option: {name}")

    def test_first_call_copies_and_rerun_uses_same_url(self):
        with patch.object(
            ui, "load_local_image_as_base64",
            side_effect=AssertionError("No Base64 should be transferred"),
        ):
            url = ui.load_local_image_url(str(self.source))
            self.assertTrue(url.startswith(
                "/nested/app/app/static/assets/bank/card.avif?v="
            ))
            self.assertNotIn("base64", url)
            self.assertEqual(
                (self.static_root / "bank" / "card.avif").read_bytes(),
                self.source.read_bytes(),
            )
            with patch.object(
                ui.shutil, "copy2", side_effect=AssertionError("Unnecessary copy")
            ):
                self.assertEqual(ui.load_local_image_url(str(self.source)), url)

    def test_modified_asset_updates_static_copy_and_url(self):
        first = ui.load_local_image_url(str(self.source))
        self.source.write_bytes(b"sample image version two is a longer file")
        second = ui.load_local_image_url(str(self.source))
        self.assertNotEqual(first, second)
        self.assertEqual(
            (self.static_root / "bank" / "card.avif").read_bytes(),
            self.source.read_bytes(),
        )

    def test_rejects_outside_assets_and_unknown_extensions(self):
        outside = self.asset_root.parent / "private.png"
        outside.write_bytes(b"private")
        with self.assertRaises(ValueError):
            ui.load_local_image_url(str(outside))
        other = self.asset_root / "secret.txt"
        other.write_text("not an image")
        with self.assertRaises(ValueError):
            ui.load_local_image_url(str(other))

    def test_disabled_static_setting_preserves_base64_fallback(self):
        self.enabled = False
        with patch.object(
            ui, "load_local_image_as_base64", return_value="data:image/avif;base64,AA=="
        ) as encode:
            self.assertEqual(
                ui.load_local_image_url(str(self.source)),
                "data:image/avif;base64,AA==",
            )
            encode.assert_called_once_with(str(self.source))
        self.assertFalse((self.static_root / "bank" / "card.avif").exists())

    def test_repository_enables_static_serving(self):
        config = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text())
        self.assertTrue(config["server"]["enableStaticServing"])
        self.assertTrue((ROOT / "static").is_dir())

    def test_large_image_callers_are_migrated_from_base64(self):
        for path in (
            "views/main.py", "views/bank/bank.py", "views/bank/draw.py",
            "views/bank/scene.py", "games/game1/game1.py",
            "games/shared/article_reader.py", "games/shared/roulette.py",
            "games/shared/betting.py", "games/shared/result.py",
        ):
            with self.subTest(path=path):
                content = (ROOT / path).read_text(encoding="utf-8")
                self.assertNotIn("load_local_image_as_base64(", content)
        result = (ROOT / "games/shared/result.py").read_text(encoding="utf-8")
        self.assertNotIn("b64encode(asset.read_bytes())", result)


if __name__ == "__main__":
    unittest.main()
