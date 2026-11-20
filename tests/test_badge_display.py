"""Badge gallery and nameplate contract tests without a live Streamlit server."""
import unittest

from modules.badges import BADGES
from modules.badge_display import (
    BADGE_SYMBOLS,
    LEGENDARY_ACCENTS,
    NAMEPLATE_CSS,
    badge_accent,
    badge_gallery_art_css,
    badge_gallery_css,
    badge_symbol,
    nameplate_html,
)


class BadgeGalleryTests(unittest.TestCase):
    def test_every_badge_has_a_replaceable_symbol(self):
        self.assertEqual(set(BADGE_SYMBOLS), {badge.id for badge in BADGES})
        self.assertEqual(len(BADGE_SYMBOLS), 27)
        self.assertEqual(len(set(BADGE_SYMBOLS.values())), 27)
        self.assertEqual(badge_symbol("g1_hit"), "◈")

    def test_all_twenty_seven_artworks_are_valid_standalone_svg_images(self):
        import base64
        from xml.etree import ElementTree as ET
        from modules.badge_display import BADGE_ART_DIR, badge_image_data_uri

        assets = sorted(BADGE_ART_DIR.glob("*.svg"))
        self.assertEqual(len(assets), 27)
        seen = set()
        for badge in BADGES:
            with self.subTest(badge=badge.id):
                uri = badge_image_data_uri(badge.id)
                self.assertTrue(uri.startswith("data:image/svg+xml;base64,"))
                raw = base64.b64decode(uri.partition(",")[2])
                image = ET.fromstring(raw)
                self.assertEqual(image.tag, "{http://www.w3.org/2000/svg}svg")
                self.assertEqual(image.attrib["viewBox"], "0 0 256 256")
                self.assertEqual(image.find("{http://www.w3.org/2000/svg}title").text, badge.title)
                self.assertNotIn(b"<script", raw)
                self.assertNotIn(b" xlink:href=", raw)
                self.assertNotIn(b" href=", raw)
                self.assertGreater(len(raw), 2600)
                self.assertNotIn(raw, seen)
                seen.add(raw)
        self.assertEqual(badge_image_data_uri("../../unsafe"), "")

    def test_gallery_artwork_is_loaded_once_separately_from_button_state(self):
        static = badge_gallery_art_css()
        state_css = badge_gallery_css("first_round g1_hit", "g1_hit")
        self.assertEqual(static.count("background-image:url('data:image/svg+xml;base64,"), 27)
        self.assertIn("background-repeat:no-repeat", static)
        self.assertIn("background-size:contain", static)
        self.assertIn("grayscale(1) brightness(.30)", state_css)
        self.assertNotIn("data:image/svg+xml;base64,", state_css)
        self.assertLess(len(state_css), 20000)
        self.assertIs(badge_gallery_art_css(), static)
        self.assertIs(badge_gallery_css("first_round g1_hit", "g1_hit"), state_css)

    def test_parent_injects_art_before_opening_dialog(self):
        from pathlib import Path
        main = (Path(__file__).resolve().parents[1] / "views" / "main.py").read_text(encoding="utf-8")
        self.assertIn("st.html(badge_gallery_art_css())", main)
        self.assertLess(main.index("st.html(badge_gallery_art_css())"), main.index("open_badge_gallery()", main.index("st.html(badge_gallery_art_css())")))

    def test_equipped_badge_uses_image_not_symbol(self):
        nameplate = nameplate_html("Player", "g1_hit", "g1_hit")
        self.assertIn('class="pc-nameplate-art"', nameplate)
        self.assertIn("data:image/svg+xml;base64,", nameplate)
        self.assertNotIn("◈</span>", nameplate)
        self.assertIn("pc-effect-numeric_particles", nameplate)

    def test_detail_and_tile_use_image_assets(self):
        from pathlib import Path

        source = (Path(__file__).resolve().parents[1] / "views" / "badges.py").read_text(encoding="utf-8")
        self.assertIn("badge_image_data_uri(selected_id)", source)
        self.assertIn("art_markup", source)
        self.assertIn("badge.title,", source)
        self.assertNotIn("badge_symbol(badge.id),", source)

    def test_legendary_effects_are_unique(self):
        self.assertEqual(len(LEGENDARY_ACCENTS), 6)
        for badge in BADGES:
            if badge.rarity == "legendary":
                self.assertIn(badge.id, LEGENDARY_ACCENTS)
                self.assertIn("pc-effect-" + badge.effect, NAMEPLATE_CSS)
        self.assertIn("prefers-reduced-motion", NAMEPLATE_CSS)

    def test_referral_tiers_use_unique_art_and_legendary_glow(self):
        self.assertEqual(badge_accent("invite_one"), "#B78BFF")
        self.assertEqual(badge_accent("invite_three"), "#71F4D1")
        self.assertIn("pc-effect-referral_sparks", NAMEPLATE_CSS)
        html = nameplate_html("Inviter", "invite_three", "invite_one invite_three")
        self.assertIn("pc-tier-legendary", html)
        self.assertIn("pc-effect-referral_sparks", html)
        self.assertIn('class="pc-nameplate-art"', html)

    def test_mythic_gold_and_red_have_distinct_effects(self):
        gold = nameplate_html("Collector", "all_legendary", "all_legendary")
        red = nameplate_html("Bankrupt", "bankrupt", "bankrupt")
        self.assertIn("pc-tier-mythic", gold)
        self.assertIn("pc-effect-golden_crown", gold)
        self.assertIn("pc-effect-scarlet_alarm", red)
        self.assertEqual(badge_accent("all_legendary"), "#FFE172")
        self.assertEqual(badge_accent("bankrupt"), "#FF526A")
        self.assertIn("pc-effect-loan_hourglass", NAMEPLATE_CSS)

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
        # Dynamic selectors must stay inside the style element.
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

    def test_badge_list_alone_is_a_square_scrollport(self):
        # The 27-card gallery must scroll without moving the selected details
        # or equip controls. Keep those widgets outside the keyed container.
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1] / "views" / "badges.py").read_text(encoding="utf-8")
        self.assertIn('with st.container(height=320, border=True, key="badge_gallery"):', source)
        list_start = source.index('with st.container(height=320, border=True, key="badge_gallery")')
        list_end = source.index('    # Generate the selected-card border', list_start)
        detail = source.index('    chosen = BADGE_BY_ID[selected_id]', list_end)
        equip = source.index('        if st.button("이 배지 장착"', detail)
        self.assertLess(list_start, list_end)
        self.assertLess(list_end, detail)
        self.assertLess(detail, equip)
        self.assertEqual(source.count('key="badge_gallery"'), 1)

        css = badge_gallery_css("", "first_round")
        self.assertIn("--pc-badge-side:max(", css)
        self.assertIn("calc(100dvw - 78px)", css)
        self.assertIn("calc(100dvh - 270px)", css)
        self.assertIn("aspect-ratio:1 / 1!important", css)
        self.assertIn("height:auto!important", css)
        self.assertIn("overflow-y:auto!important", css)
        self.assertIn("overflow-x:hidden!important", css)
        self.assertIn("overscroll-behavior:contain", css)
        self.assertIn("touch-action:pan-y", css)
        self.assertIn("scrollbar-width:thin", css)
        # Mobile CSS must not override the square with a full-width panel.
        self.assertNotIn("width:100%!important; max-width:100%!important;\n    overflow-x:hidden", css)

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
