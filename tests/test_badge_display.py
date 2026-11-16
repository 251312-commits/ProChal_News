"""Badge gallery and nameplate contract tests without a live Streamlit server."""
import unittest

from modules.badges import BADGES
from modules.badge_display import (
    BADGE_SYMBOLS,
    LEGENDARY_ACCENTS,
    NAMEPLATE_CSS,
    badge_accent,
    badge_gallery_css,
    badge_symbol,
    nameplate_html,
)


class BadgeGalleryTests(unittest.TestCase):
    def test_every_badge_has_a_replaceable_symbol(self):
        self.assertEqual(set(BADGE_SYMBOLS), {badge.id for badge in BADGES})
        self.assertEqual(len(BADGE_SYMBOLS), 20)
        self.assertEqual(len(set(BADGE_SYMBOLS.values())), 20)
        self.assertEqual(badge_symbol("g1_hit"), "◈")

    def test_legendary_effects_are_unique(self):
        self.assertEqual(len(LEGENDARY_ACCENTS), 4)
        for badge in BADGES:
            if badge.rarity == "legendary":
                self.assertIn(badge.id, LEGENDARY_ACCENTS)
                self.assertIn("pc-effect-" + badge.effect, NAMEPLATE_CSS)
        self.assertIn("prefers-reduced-motion", NAMEPLATE_CSS)

    def test_unearned_badge_can_never_change_displayed_nameplate(self):
        self.assertEqual(nameplate_html("User", "g1_hit", "first_round"), "User")
        self.assertEqual(nameplate_html("User", "0", "g1_hit"), "User")
        self.assertEqual(nameplate_html("User", "invalid", "g1_hit"), "User")

    def test_nameplate_escapes_all_user_controlled_text(self):
        html = nameplate_html('<script>alert(1)</script>', "g1_hit", "g1_hit")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("pc-tier-legendary", html)
        self.assertIn("pc-effect-numeric_particles", html)
        self.assertIn("소수점의 지배자 배지", html)
        self.assertNotIn("소수점의 지배자</span>", html)  # icon-only next to name

    def test_rare_and_epic_share_tier_colors(self):
        self.assertEqual(badge_accent("streak_three"), badge_accent("g1_within_three"))
        self.assertEqual(badge_accent("streak_five_mixed"), badge_accent("g1_exact_one"))

    def test_gallery_css_is_one_complete_style_element(self):
        # Regression: appending per-card selectors AFTER </style> rendered raw
        # CSS text in the popup instead of styling the badge buttons.
        css = badge_gallery_css("first_round g1_hit", "g1_hit")
        self.assertEqual(css.count("<style>"), 1)
        self.assertEqual(css.count("</style>"), 1)
        self.assertTrue(css.rstrip().endswith("</style>"))
        before_close, after_close = css.split("</style>")
        self.assertEqual(after_close.strip(), "")
        for badge in BADGES:
            self.assertIn(".st-key-badge_card_" + badge.id, before_close)
        self.assertIn("background:#141218", before_close)
        self.assertIn("color:#80E3FF", before_close)

    def test_mobile_gallery_styles_target_actual_streamlit_columns(self):
        css = badge_gallery_css("", "first_round")
        self.assertIn('[data-testid="stColumn"]', css)
        self.assertNotIn('[data-testid="column"]', css)
        self.assertIn('[role="dialog"]:has(.st-key-badge_gallery)', css)
        self.assertIn("max-width:calc(100dvw - 16px)", css)
        self.assertIn("max-height:calc(100dvh - 16px)", css)
        self.assertIn("flex-flow:row nowrap", css)
        self.assertIn("overflow-x:hidden", css)

    def test_dialog_uses_small_width_and_html_renderers(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1] / "views" / "badges.py").read_text(encoding="utf-8")
        self.assertIn('width="small"', source)
        self.assertNotIn('width="large"', source)
        self.assertIn('st.html(badge_gallery_css(', source)
        self.assertNotIn('unsafe_allow_html=True', source)

    def test_locked_grid_is_dark_and_unlocked_grid_uses_rarity_color(self):
        css = badge_gallery_css("first_round g1_hit", "g1_hit")
        self.assertIn(".st-key-badge_card_g1_hit", css)
        self.assertIn("color:#80E3FF", css)
        self.assertIn(".st-key-badge_card_g2_both_fifteen", css)
        self.assertIn("color:#4F4C59", css)
        self.assertIn("background:#141218", css)


if __name__ == "__main__":
    unittest.main()
