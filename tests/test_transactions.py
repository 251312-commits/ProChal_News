"""Gateway client regression tests; no external Sheets/API calls."""
import unittest
from unittest.mock import Mock, patch

import requests

from modules import transactions as tx


class Session(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.session = Session(
            current_user="11011",
            current_user_data={"학번": "11011", "코인": 5000, "연승": 2, "대출금": 1000, "대출원금": 1000},
        )
        self.secrets = {
            "transaction_endpoint": "https://script.google.com/macros/s/deployment/exec",
            "transaction_token": "secret",
        }
        self.session_patch = patch.object(tx.st, "session_state", self.session)
        self.secrets_patch = patch.object(tx.st, "secrets", self.secrets)
        self.session_patch.start()
        self.secrets_patch.start()
        self.addCleanup(self.session_patch.stop)
        self.addCleanup(self.secrets_patch.stop)

    def response(self, *, replayed=False, delta=1000, coins=6000, streak=3, loan=1000):
        result = Mock()
        result.json.return_value = {
            "ok": True, "replayed": replayed,
            "balances": {"coins": coins, "streak": streak, "loan": loan, "principal": loan},
            "settlement": {
                "delta": delta, "coins": coins, "streak": streak,
                "loan": loan, "is_win": delta > 0,
            },
        }
        return result

    def test_confirm_reuses_round_id_on_retry(self):
        with patch.object(tx.requests, "post", return_value=self.response()) as post:
            tx.confirm_bet("game_1", 1000)
            first_id = self.session.game_1_round_id
            tx.confirm_bet("game_1", 1000)
            self.assertEqual(self.session.game_1_round_id, first_id)
            self.assertEqual(post.call_count, 2)
            self.assertEqual(post.call_args_list[0].kwargs["json"]["transaction_id"],
                             post.call_args_list[1].kwargs["json"]["transaction_id"])
            self.assertEqual(self.session.current_user_data["대출금"], 1000)

    def test_settle_returns_committed_snapshot_and_does_not_repeat_id(self):
        self.session.game_2_round_id = "a" * 32
        with patch.object(tx.requests, "post", return_value=self.response(replayed=True)) as post:
            result = tx.settle_game_round("game_2", 1000, True)
            self.assertEqual((result["reward"], result["new_coins"], result["new_streak"]),
                             (1000, 6000, 3))
            self.assertTrue(result["replayed"])
            self.assertEqual(post.call_args.kwargs["json"]["transaction_id"],
                             "settle:" + "a" * 32)

    def test_insufficient_balance_is_not_optimistically_saved(self):
        error = self.response()
        error.json.return_value = {
            "ok": False, "code": "INSUFFICIENT_FUNDS",
            "balances": {"coins": 600, "streak": 2, "loan": 1000},
        }
        with patch.object(tx.requests, "post", return_value=error):
            with self.assertRaises(tx.BalanceChanged) as raised:
                tx.confirm_bet("game_3", 1000)
            self.assertEqual(raised.exception.balances["coins"], 600)
            self.assertEqual(self.session.current_user_data["코인"], 5000)
            self.assertIn("game_3_round_id", self.session)

    def test_network_timeout_retains_transaction_identity(self):
        with patch.object(tx.requests, "post", side_effect=requests.Timeout("lost response")):
            with self.assertRaises(tx.TransactionError):
                tx.confirm_bet("game_4", 1000)
            original = self.session.game_4_round_id
            with self.assertRaises(tx.TransactionError):
                tx.confirm_bet("game_4", 1000)
            self.assertEqual(self.session.game_4_round_id, original)
            self.assertEqual(self.session.current_user_data["코인"], 5000)

    def test_interest_posts_one_round_id_and_refreshes_balances(self):
        self.session.game_1_round_id = "f" * 32
        response = self.response(coins=6000, loan=1200)
        # Interest increases total debt, but must never increase borrowed principal.
        response.json.return_value["balances"]["principal"] = 1000
        response.json.return_value["interest"] = {
            "charged": 200, "loan_before": 1000, "loan_after": 1200,
        }
        with patch.object(tx.requests, "post", return_value=response) as post:
            first = tx.apply_round_interest("game_1")
            second = tx.apply_round_interest("game_1")
        self.assertEqual(first["charged"], 200)
        self.assertEqual(second["new_loan"], 1200)
        self.assertEqual(self.session.current_user_data["대출금"], 1200)
        self.assertEqual(self.session.current_user_data["대출원금"], 1000)
        self.assertEqual(post.call_count, 2)
        self.assertEqual(
            post.call_args.kwargs["json"]["transaction_id"], "interest:" + "f" * 32,
        )
        self.assertEqual(post.call_args.kwargs["json"]["kind"], "interest")

    def test_interest_fails_closed_without_round_id_or_receipt(self):
        with patch.object(tx.requests, "post") as post:
            with self.assertRaises(tx.TransactionError):
                tx.apply_round_interest("game_2")
            post.assert_not_called()

        self.session.game_2_round_id = "a" * 32
        with patch.object(tx.requests, "post", return_value=self.response()):
            with self.assertRaises(tx.TransactionError):
                tx.apply_round_interest("game_2")
        self.assertEqual(self.session.current_user_data["대출금"], 1000)

    def test_bank_sends_expected_fresh_values(self):
        with patch.object(tx.requests, "post", return_value=self.response(coins=7000, loan=3000)) as post:
            tx.bank_transaction("borrow", 2000, "borrow:" + "b" * 32)
            body = post.call_args.kwargs["json"]
            self.assertEqual((body["expected_coins"], body["expected_loan"], body["expected_principal"]),
                             (5000, 1000, 1000))
            self.assertEqual((self.session.current_user_data["코인"],
                              self.session.current_user_data["대출금"],
                              self.session.current_user_data["대출원금"]), (7000, 3000, 3000))

    def test_borrowing_can_exceed_total_debt_cap_but_not_principal_cap(self):
        self.session.current_user_data.update({"코인": 6000, "대출금": 9600, "대출원금": 8000})
        response = self.response(coins=8000, loan=11600)
        response.json.return_value["balances"]["principal"] = 10000
        with patch.object(tx.requests, "post", return_value=response) as post:
            tx.bank_transaction("borrow", 2000, "borrow:" + "c" * 32)
        body = post.call_args.kwargs["json"]
        self.assertEqual((body["expected_loan"], body["expected_principal"]), (9600, 8000))
        self.assertEqual(self.session.current_user_data["대출금"], 11600)
        self.assertEqual(self.session.current_user_data["대출원금"], 10000)

    def test_borrow_refuses_missing_principal(self):
        self.session.current_user_data.pop("대출원금")
        with patch.object(tx.requests, "post") as post:
            with self.assertRaises(tx.TransactionError):
                tx.bank_transaction("borrow", 1000, "borrow:" + "a" * 32)
        post.assert_not_called()

    def test_missing_endpoint_blocks_all_writes(self):
        self.secrets.pop("transaction_endpoint")
        with patch.object(tx.requests, "post") as post:
            with self.assertRaises(tx.TransactionError) as raised:
                tx.confirm_bet("game_5", 1000)
            self.assertEqual(raised.exception.code, "NOT_CONFIGURED")
            post.assert_not_called()


if __name__ == "__main__":
    unittest.main()
