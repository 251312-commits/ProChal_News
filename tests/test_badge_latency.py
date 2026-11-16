"""Short-lived badge UI cache and single-RPC behavior; no live network."""
import unittest
from unittest.mock import patch

from views import badges as gallery


class BadgeLatencyTests(unittest.TestCase):
    def test_sync_policy_throttles_reopen_and_dialog_reruns(self):
        self.assertTrue(gallery.badge_sync_due({}, 200.0))
        recently_synced = {
            "badge_gallery_synced": True,
            "badge_gallery_checked_at": 200.0,
        }
        self.assertFalse(gallery.badge_sync_due(recently_synced, 200.0))
        self.assertFalse(gallery.badge_sync_due(recently_synced, 289.0))
        self.assertTrue(gallery.badge_sync_due(recently_synced, 290.0))
        self.assertTrue(gallery.badge_sync_due(recently_synced, 220.0, force=True))
        # A monotonic clock reset (e.g., process restart) invalidates the cache.
        self.assertTrue(gallery.badge_sync_due(recently_synced, 1.0))

    def test_failed_network_attempts_have_a_short_cooldown(self):
        failed = {
            "badge_gallery_synced": False,
            "badge_gallery_sync_error": True,
            "badge_gallery_checked_at": 100.0,
        }
        self.assertFalse(gallery.badge_sync_due(failed, 119.0))
        self.assertTrue(gallery.badge_sync_due(failed, 120.0))
        self.assertTrue(gallery.badge_sync_due(failed, 101.0, force=True))

    def test_same_account_reopening_preserves_confirmed_profile(self):
        state = {
            "current_user": "11011",
            "badge_gallery_owner": "11011",
            "badge_gallery_synced": True,
            "badge_gallery_checked_at": 200.0,
            "badge_gallery_selected": "g1_hit",
        }
        with patch.object(gallery.st, "session_state", state), patch.object(
            gallery, "badge_gallery_dialog"
        ) as dialog:
            gallery.open_badge_gallery()
        dialog.assert_called_once()
        self.assertTrue(state["badge_gallery_synced"])
        self.assertEqual(state["badge_gallery_checked_at"], 200.0)
        self.assertEqual(state["badge_gallery_selected"], "g1_hit")

    def test_other_user_invalidates_cached_badge_profile(self):
        state = {
            "current_user": "22022",
            "badge_gallery_owner": "11011",
            "badge_gallery_synced": True,
            "badge_gallery_checked_at": 200.0,
            "badge_gallery_selected": "g1_hit",
            "badge_pending_equip": {"badge_id": "g1_hit"},
        }
        with patch.object(gallery.st, "session_state", state), patch.object(
            gallery, "badge_gallery_dialog"
        ):
            gallery.open_badge_gallery()
        self.assertEqual(state["badge_gallery_owner"], "22022")
        self.assertNotIn("badge_gallery_synced", state)
        self.assertNotIn("badge_gallery_checked_at", state)
        self.assertNotIn("badge_gallery_selected", state)
        self.assertNotIn("badge_pending_equip", state)

    def test_successful_equip_retains_confirmed_cache_for_next_open(self):
        state = {"badge_gallery_synced": True, "badge_gallery_checked_at": 0}
        with patch.object(gallery.st, "session_state", state), patch.object(
            gallery, "equip_badge", return_value={"equipped": "first_round"}
        ) as write, patch.object(gallery.st, "rerun") as rerun, patch.object(
            gallery, "monotonic", return_value=1234.0
        ):
            gallery._apply_equipped_badge("first_round")
        write.assert_called_once()
        rerun.assert_called_once()
        self.assertEqual(state["badge_gallery_checked_at"], 1234.0)
        self.assertTrue(state["badge_gallery_synced"])
        self.assertFalse(gallery.badge_sync_due(state, 1240.0))
        self.assertNotIn("badge_pending_equip", state)


if __name__ == "__main__":
    unittest.main()
