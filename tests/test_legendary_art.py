"""Winged Legendary artwork regression tests.

The six Legendary assets must share a recognisable winged silhouette while
preserving each title-specific central illustration and its original ID.
Mythic art deliberately stays separate, so the fifth rarity remains higher.
"""
import unittest
from xml.etree import ElementTree as ET

from modules.badges import BADGES
from modules.badge_display import BADGE_ART_DIR

SVG_NS = "{http://www.w3.org/2000/svg}"

WING_VARIANTS = {
    "streak_eight_mixed": "#ECC46F",  # celestial gold
    "g1_hit": "#71D9EF",             # ice-blue precision
    "g4_four_streak": "#B38BEA",      # violet portal
    "g5_three_streak": "#EA729B",     # rose-red broadcast eye
    "loan_survivor": "#DAB76C",       # champagne loan survivor
    "invite_three": "#63E9C8",        # mint-green referral wings
}


class LegendaryWingArtTests(unittest.TestCase):
    def test_exactly_six_legendary_artworks_have_expanded_mirrored_wings(self):
        self.assertEqual(
            {badge.id for badge in BADGES if badge.rarity == "legendary"},
            set(WING_VARIANTS),
        )
        for badge in BADGES:
            with self.subTest(badge=badge.id):
                art = (BADGE_ART_DIR / f"{badge.id}.svg").read_text(encoding="utf-8")
                root = ET.fromstring(art)
                self.assertEqual(root.tag, SVG_NS + "svg")
                self.assertEqual(root.attrib.get("viewBox"), "0 0 256 256")
                self.assertEqual(root.find(SVG_NS + "title").text, badge.title)
                self.assertNotIn("<script", art)
                self.assertNotIn("href=", art)
                wings = root.find(f"{SVG_NS}g[@id='legendary-wings']")
                core = root.find(f"{SVG_NS}g[@id='legendary-center']")
                if badge.rarity == "legendary":
                    self.assertIsNotNone(wings)
                    self.assertIsNotNone(core)
                    self.assertIn(WING_VARIANTS[badge.id], art)
                    self.assertEqual(core.attrib.get("transform"),
                                     "translate(34.56 32) scale(.73)")
                    left = wings.find(f"{SVG_NS}g[@id='wing-left']")
                    right = wings.find(f"{SVG_NS}g[@id='wing-right']")
                    self.assertIsNotNone(left)
                    self.assertIsNotNone(right)
                    self.assertEqual(right.attrib.get("transform"),
                                     "translate(256 0) scale(-1 1)")
                    self.assertGreaterEqual(len(left.findall(SVG_NS + "path")), 5)
                    self.assertGreaterEqual(len(right.findall(SVG_NS + "path")), 5)
                    self.assertIsNotNone(
                        root.find(f"{SVG_NS}defs/{SVG_NS}linearGradient[@id='wingFeather']")
                    )
                    self.assertGreater(len(core.findall(".//" + SVG_NS + "path")), 3)
                else:
                    self.assertIsNone(wings)
                    self.assertIsNone(core)

    def test_winged_legendary_assets_remain_compact_and_self_contained(self):
        for badge_id in WING_VARIANTS:
            with self.subTest(badge=badge_id):
                data = (BADGE_ART_DIR / f"{badge_id}.svg").read_bytes()
                self.assertLess(len(data), 15000)
                self.assertNotIn(b"javascript:", data)
                self.assertNotIn(b"https://", data)
                self.assertNotIn(b" xlink:href", data)


if __name__ == "__main__":
    unittest.main()
