"""Tests for the shared full-screen similarity-analysis loading UI."""
import ast
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock


ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT / "games" / "shared" / "loading.py"
CSS = ROOT / "games" / "shared" / "similarity_loading.css"


class SimilarityLoadingTests(TestCase):
    def _loader(self):
        # Isolate the context manager to avoid importing AI models / Google Sheets.
        module = ast.parse(COMMON.read_text(encoding="utf-8"))
        func = next(
            item for item in module.body
            if isinstance(item, ast.FunctionDef)
            and item.name == "similarity_analysis_loading"
        )
        scope = {
            "contextmanager": contextmanager,
            "st": SimpleNamespace(empty=MagicMock()),
            "Path": Path,
            "__file__": str(COMMON),
            "_SIMILARITY_LOADING_HTML": '<div id="pc-sim-load">분석 중</div>',
        }
        exec(compile(ast.Module(body=[func], type_ignores=[]), str(COMMON), "exec"), scope)
        return scope["similarity_analysis_loading"], scope["st"].empty

    def test_loader_visible_during_work_and_cleared_after(self):
        loader, empty = self._loader()
        with loader():
            placeholder = empty.return_value
            placeholder.markdown.assert_called_once()
            html = placeholder.markdown.call_args.args[0]
            self.assertIn('id="pc-sim-load"', html)
            self.assertIn("@keyframes pc-sim-scan", html)
            placeholder.empty.assert_not_called()
        placeholder.empty.assert_called_once()

    def test_loader_cleared_after_error(self):
        loader, empty = self._loader()
        with self.assertRaisesRegex(ValueError, "failed"):
            with loader():
                raise ValueError("failed")
        empty.return_value.empty.assert_called_once()

    def test_all_similarity_games_use_shared_screen(self):
        for number in range(1, 6):
            with self.subTest(game=number):
                game_file = ROOT / "games" / "game1" / "game1.py" if number == 1 else ROOT / "games" / f"game{number}.py"
                source = game_file.read_text(encoding="utf-8")
                self.assertIn("with similarity_analysis_loading():", source)

    def test_css_supports_mobile_and_reduced_motion(self):
        css = CSS.read_text(encoding="utf-8")
        self.assertIn("height: 100dvh", css)
        self.assertIn("max-width: 380px", css)
        self.assertIn("prefers-reduced-motion", css)
