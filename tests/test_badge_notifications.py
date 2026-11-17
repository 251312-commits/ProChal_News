"""Regression checks for one-shot, server-confirmed badge announcements."""
from pathlib import Path
import unittest
from unittest.mock import patch

from modules import badge_notifications as notices
from modules.badges import BADGE_BY_ID


class BadgeAwardQueueTests(unittest.TestCase):
    def setUp(self):
        self.session = {"current_user": "11011"}
        self.state_patch = patch.object(notices.st, "session_state", self.session)
        self.state_patch.start()
        self.addCleanup(self.state_patch.stop)

    def test_new_badges_are_queued_once_even_if_settlement_is_replayed(self):
        self.assertEqual(
            notices.queue_badge_awards(("first_round", "g1_exact_one")),
            ("first_round", "g1_exact_one"),
        )
        self.assertEqual(notices.queue_badge_awards(("first_round",)), ())
        self.assertEqual(notices.pending_badge_ids(), ("first_round", "g1_exact_one"))
        notices.acknowledge_badge_awards(["first_round"])
        self.assertEqual(notices.pending_badge_ids(), ("g1_exact_one",))
        notices.acknowledge_badge_awards(["g1_exact_one"])
        self.assertEqual(notices.pending_badge_ids(), ())
        # Replayed transactions must not resurrect an already dismissed popup.
        self.assertEqual(notices.queue_badge_awards(["first_round"]), ())
        self.assertEqual(notices.pending_badge_ids(), ())

    def test_badges_do_not_cross_accounts(self):
        notices.queue_badge_awards(["g1_hit"])
        self.session["current_user"] = "11012"
        self.assertEqual(notices.pending_badge_ids(), ())
        self.assertEqual(notices.queue_badge_awards(["g1_hit"]), ("g1_hit",))

    def test_untrusted_ids_are_ignored(self):
        self.assertEqual(notices.queue_badge_awards(None), ())
        self.assertEqual(notices.queue_badge_awards("first_round"), ())
        self.assertEqual(
            notices.queue_badge_awards(["not-a-badge", [], "first_round", "first_round"]),
            ("first_round",),
        )
        notices.acknowledge_badge_awards(["not-a-badge", []])
        self.assertEqual(notices.pending_badge_ids(), ("first_round",))

    def test_card_metadata_is_from_catalog_and_local_svg(self):
        notices.queue_badge_awards(("first_round", "g1_hit"))
        cards = notices.pending_badge_cards()
        self.assertEqual([card["id"] for card in cards], ["first_round", "g1_hit"])
        for card in cards:
            self.assertEqual(card["title"], BADGE_BY_ID[card["id"]].title)
            self.assertTrue(card["image"].startswith("data:image/svg+xml;base64,"))
            self.assertTrue(card["rarity"])
            self.assertTrue(card["accent"].startswith("#"))


class BadgeAwardIntegrationTests(unittest.TestCase):
    def test_gateway_confirmation_points_are_all_connected(self):
        src = (Path(__file__).resolve().parents[1] / "modules" / "transactions.py").read_text(encoding="utf-8")
        self.assertIn("queue_badge_awards(newly_unlocked)", src)
        self.assertIn("queue_badge_awards(_update_session_badges(result.get(\"badges\")))", src)
        self.assertIn("queue_badge_awards(unlocked)", src)

    def test_game1_announces_only_after_score_reveal_and_acknowledges(self):
        root = Path(__file__).resolve().parents[1]
        js = (root / "games/game1/result_screen/result.js").read_text(encoding="utf-8")
        html = (root / "games/game1/result_screen/index.html").read_text(encoding="utf-8")
        host = (root / "games/game1/result_reveal.py").read_text(encoding="utf-8")
        self.assertIn("scheduleBadgeAwards();", js)
        self.assertIn("if (!fullyFinished || !revealFinished || awardsShown", js)
        self.assertIn('action: "badge_dismissed"', js)
        self.assertIn('badge_awards=pending_badge_cards()', host)
        self.assertIn('acknowledge_badge_awards(event.get("badge_ids"))', host)
        self.assertIn('class="badge-awards"', html)
        self.assertIn('aria-modal="true"', html)

    def test_main_router_does_not_open_two_dialogs_on_gallery_click(self):
        root = Path(__file__).resolve().parents[1]
        main = (root / "views/main.py").read_text(encoding="utf-8")
        router = (root / "news.py").read_text(encoding="utf-8")
        self.assertIn('st.session_state["_badge_gallery_opened_this_run"] = True', main)
        self.assertIn('if not gallery_opened and not game1_cinematic:', router)
        self.assertIn('show_pending_badge_award()', router)


if __name__ == "__main__":
    unittest.main()
