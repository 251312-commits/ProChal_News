"""Tests for the shared full-screen similarity-analysis loading UI."""
import ast
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import MagicMock, patch

from games.shared import loading as loader_module


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
            "_similarity_video_markup": lambda: "",
        }
        exec(compile(ast.Module(body=[func], type_ignores=[]), str(COMMON), "exec"), scope)
        return scope["similarity_analysis_loading"], scope["st"].empty

    def test_loader_visible_during_work_and_cleared_after(self):
        loader, empty = self._loader()
        with loader():
            placeholder = empty.return_value
            placeholder.html.assert_called_once()
            placeholder.markdown.assert_not_called()
            html = placeholder.html.call_args.args[0]
            self.assertIn('id="pc-sim-load"', html)
            self.assertIn("@keyframes pc-sim-scan", html)
            self.assertIn("animation: pc-sim-reveal 1ms step-end 200ms forwards", html)
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
        self.assertIn("overflow: hidden;", css)
        self.assertIn("grid-template-rows: auto auto minmax(0, 1fr) auto auto auto", css)
        self.assertIn("max-height: 100dvh", css)
        self.assertIn("max-height: 620px", css)
        self.assertIn("max-height: 480px", css)
        self.assertIn("min-height: 0;", css)
        self.assertIn(".pc-sim-video-frame", css)
        self.assertIn(".pc-sim-video {", css)

    def test_optional_clips_do_not_hide_original_loading_art(self):
        with TemporaryDirectory() as empty:
            with patch.object(loader_module, "_VIDEO_DIRECTORY", Path(empty)):
                self.assertEqual(loader_module._similarity_video_markup(), "")
        html = loader_module._SIMILARITY_LOADING_HTML
        self.assertIn('pc-sim-paper-left', html)
        self.assertIn('pc-sim-paper-right', html)
        self.assertIn('pc-sim-meter', html)
        self.assertIn('PC_SIM_VIDEO_SLOT', html)

    def test_video_audio_button_uses_browser_click_bridge(self):
        source = COMMON.read_text(encoding="utf-8")
        bridge = (COMMON.parent / "similarity_video_controls.js").read_text(encoding="utf-8")
        self.assertIn('components.html(f"<script>{_VIDEO_SOUND_JS}</script>"', source)
        self.assertIn('pc-sim-sound-toggle', source)
        self.assertIn('doc.addEventListener("click", toggleSound)', bridge)
        self.assertIn('video.muted = !turnOn', bridge)
        self.assertIn('video.play()', bridge)

    def test_video_html_is_rendered_as_html_not_markdown_code(self):
        video = """
          <div class="pc-sim-video-frame">
            <video class="pc-sim-video" controls muted playsinline>
              <source src="https://example.invalid/Video1.mp4" type="video/mp4">
            </video>
          </div>
        """
        with patch.object(loader_module, "_similarity_video_markup", return_value=video):
            with patch.object(loader_module.st, "empty") as empty:
                with patch.object(loader_module.components, "html") as bridge:
                    with loader_module.similarity_analysis_loading():
                        rendered = empty.return_value.html.call_args.args[0]
                        self.assertIn('<video class="pc-sim-video"', rendered)
                        self.assertIn('<source src="https://example.invalid/Video1.mp4"', rendered)
                        self.assertNotIn("PC_SIM_VIDEO_SLOT", rendered)
                        empty.return_value.html.assert_called_once()
                        empty.return_value.markdown.assert_not_called()
                    empty.return_value.empty.assert_called_once()
                    bridge.assert_called_once()

    def test_no_video_still_renders_original_newspaper_as_html(self):
        with patch.object(loader_module, "_similarity_video_markup", return_value=""):
            with patch.object(loader_module.st, "empty") as empty:
                with patch.object(loader_module.components, "html") as bridge:
                    with loader_module.similarity_analysis_loading():
                        rendered = empty.return_value.html.call_args.args[0]
                        self.assertIn('pc-sim-paper-left', rendered)
                        self.assertIn('pc-sim-paper-right', rendered)
                        empty.return_value.markdown.assert_not_called()
                    bridge.assert_not_called()

    def test_random_clip_stays_small_autoplays_muted_and_keeps_sound_controls(self):
        with TemporaryDirectory() as folder:
            source = Path(folder)
            for name in ("Video1.mp4", "Video2.mp4", "Video3.mp4"):
                (source / name).write_bytes(b"test")
            with patch.object(loader_module, "_VIDEO_DIRECTORY", source):
                with patch.object(loader_module, "choice", return_value="Video3.mp4") as choose:
                    html = loader_module._similarity_video_markup()
            choose.assert_called_once_with(["Video1.mp4", "Video2.mp4", "Video3.mp4"])
            self.assertIn('class="pc-sim-video"', html)
            self.assertIn("Video3.mp4?", html)
            self.assertIn('controls autoplay muted playsinline', html)
            self.assertIn('loop preload="auto"', html)
            self.assertIn('--pc-video-aspect:16 / 9', html)
            self.assertNotIn("data:video", html)
