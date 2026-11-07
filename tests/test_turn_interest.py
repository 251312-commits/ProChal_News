"""Interest math, shared result gate, and session-level duplicate prevention."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from games.shared import interest
from modules.transactions import TransactionError


class EndOfTurnInterestTests(unittest.TestCase):
    def test_compound_math_uses_whole_coin_rounding(self):
        self.assertEqual(interest.compound_balance_after_turn(0), 0)
        self.assertEqual(interest.compound_balance_after_turn(1000), 1200)
        self.assertEqual(interest.compound_balance_after_turn(1200), 1440)
        self.assertEqual(interest.compound_balance_after_turn(3), 4)

    def test_result_gate_caches_receipt_for_same_round(self):
        state = {"game_1_round_id": "a" * 32}
        st = SimpleNamespace(session_state=state, error=Mock(), caption=Mock())
        receipt = {"charged": 200, "loan_before": 1000, "new_loan": 1200, "replayed": False}
        with patch.object(interest, "st", st), patch.object(
            interest, "apply_round_interest", return_value=receipt,
        ) as apply:
            self.assertTrue(interest.apply_end_of_turn_interest("game_1"))
            self.assertTrue(interest.apply_end_of_turn_interest("game_1"))
            apply.assert_called_once_with("game_1")
            st.caption.assert_called()
            st.error.assert_not_called()

            state["game_1_round_id"] = "b" * 32
            self.assertTrue(interest.apply_end_of_turn_interest("game_1"))
            self.assertEqual(apply.call_count, 2)

    def test_failed_interest_blocks_results_and_allows_retry(self):
        state = {"game_3_round_id": "c" * 32}
        st = SimpleNamespace(session_state=state, error=Mock(), caption=Mock())
        receipt = {"charged": 1, "loan_before": 3, "new_loan": 4}
        with patch.object(interest, "st", st), patch.object(
            interest, "apply_round_interest",
            side_effect=[TransactionError("network"), receipt],
        ) as apply:
            self.assertFalse(interest.apply_end_of_turn_interest("game_3"))
            self.assertNotIn("game_3_interest_receipt", state)
            st.error.assert_called_once()
            self.assertTrue(interest.apply_end_of_turn_interest("game_3"))
            self.assertEqual(apply.call_count, 2)

    def test_zero_debt_is_recorded_and_shown_without_extra_caption(self):
        state = {"game_5_round_id": "d" * 32}
        st = SimpleNamespace(session_state=state, error=Mock(), caption=Mock())
        with patch.object(interest, "st", st), patch.object(
            interest, "apply_round_interest",
            return_value={"charged": 0, "loan_before": 0, "new_loan": 0},
        ) as apply:
            self.assertTrue(interest.apply_end_of_turn_interest("game_5"))
            self.assertTrue(interest.apply_end_of_turn_interest("game_5"))
            apply.assert_called_once()
            st.caption.assert_not_called()


if __name__ == "__main__":
    unittest.main()
