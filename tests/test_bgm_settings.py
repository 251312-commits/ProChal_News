"""Regression checks for parent-window background music control JavaScript."""
import re
import unittest
from pathlib import Path
from unittest.mock import patch

from sounds import bgm


class BgmSettingsTests(unittest.TestCase):
    def rendered_script(self, main=True):
        recorded = []
        with patch.object(bgm.components, "html", side_effect=lambda html, **kwargs: recorded.append((html, kwargs))):
            bgm.init_seamless_bgm("https://example.org/intro.mp3", "https://example.org/loop.mp3", show_controls=main)
        self.assertEqual(len(recorded), 1)
        self.assertEqual(recorded[0][1]["height"], 0)
        return recorded[0][0]

    def test_controls_are_scoped_to_main(self):
        self.assertIn("const onMain = true", self.rendered_script(main=True))
        self.assertIn("const onMain = false", self.rendered_script(main=False))
        self.assertIn("if (!onMain)", self.rendered_script(main=False))

    def test_volume_mute_and_persistence_are_available(self):
        source = self.rendered_script()
        for token in (
            "sessionStorage", "news-bgm-preferences-v1", 'type="range"',
            'type="checkbox"', "applyPrefs(current", "intro.volume = volume",
            "loop.volume = volume", "player.muted", "pagehide",
            "beforeunload", "visibilitychange", "pointerdown",
        ):
            self.assertIn(token, source)

    def test_urls_are_safely_json_quoted(self):
        source = self.rendered_script()
        self.assertIn('const introURL = "https://example.org/intro.mp3"', source)

    def test_login_cleanup_removes_controls(self):
        recorded = []
        with patch.object(bgm.components, "html", side_effect=lambda html, **kwargs: recorded.append(html)):
            bgm.stop_bgm()
        self.assertIn('player.intro.pause()', recorded[0])
        self.assertIn('root.remove()', recorded[0])


if __name__ == "__main__":
    unittest.main()
