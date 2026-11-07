"""Regression tests for bank navigation and post-save stamping."""

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from modules.account_math import account_amount


ROOT = Path(__file__).resolve().parents[1]


class State(dict):
    """The two Streamlit session_state access patterns used by bank views."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as error:
            raise AttributeError(name) from error

    def __setattr__(self, name, value):
        self[name] = value


def function_from(path, name, namespace):
    """Compile the actual function without importing Streamlit or Google APIs."""
    module = ast.parse((ROOT / path).read_text(encoding="utf-8"))
    fn = next(node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == name)
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(ROOT / path), "exec"), namespace)
    return namespace[name]


class BankAnimationTests(unittest.TestCase):
    def test_letter_only_opens_for_borrowing(self):
        session = State(page="bank")
        navigate = function_from("views/bank/bank.py", "_navigate",
                                 {"st": SimpleNamespace(session_state=session)})
        navigate("pay_loan")
        self.assertEqual(session.page, "pay_loan")
        self.assertFalse(session.bank_open_letter)
        session.page = "bank"
        navigate("draw_loan")
        self.assertTrue(session.bank_open_letter)
        session.page = "pay_loan"
        navigate("draw_loan")
        self.assertFalse(session.bank_open_letter)

    def test_stamp_flag_is_set_only_after_confirmed_ledger_write(self):
        class TransactionError(Exception):
            pass

        class BalanceChanged(TransactionError):
            balances = {"coins": 2_000, "streak": 2, "loan": 1_000}

        persist = Mock()
        user = {"학번": "01234", "코인": "1,250", "대출금": "", "연승": 0}
        session = State(current_user="01234", current_user_data=user)
        st = Mock(session_state=session)
        def sync(balances):
            user.update({
                "코인": balances["coins"], "연승": balances["streak"],
                "대출금": balances["loan"],
            })
        save = function_from("views/bank/forms.py", "_save_balances", {
            "st": st, "bank_transaction": persist,
            "transaction_id": lambda kind: kind + ":" + "a" * 32,
            "TransactionError": TransactionError, "BalanceChanged": BalanceChanged,
            "update_session_balances": sync, "account_amount": account_amount,
        })

        persist.side_effect = TransactionError("not saved")
        save(6_250, 5_000, "failed", success_state_key="bank_borrow_success")
        self.assertNotIn("bank_borrow_success", session)
        self.assertEqual((user["코인"], user["대출금"]), ("1,250", ""))
        self.assertEqual(session.bank_pending_transaction["kind"], "borrow")
        st.error.assert_called_once()
        st.toast.assert_not_called()
        st.rerun.assert_not_called()

        persist.side_effect = BalanceChanged()
        save(6_250, 5_000, "stale", success_state_key="bank_borrow_success")
        self.assertNotIn("bank_borrow_success", session)
        self.assertNotIn("bank_pending_transaction", session)
        self.assertEqual((user["코인"], user["대출금"]), (2_000, 1_000))
        st.rerun.assert_called_once()

        persist.side_effect = lambda *_: sync({"coins": 7_000, "streak": 2, "loan": 6_000})
        save(7_000, 6_000, "saved", success_state_key="bank_borrow_success")
        persist.assert_called_with("borrow", 5000, "borrow:" + "a" * 32)
        self.assertTrue(session.bank_borrow_success)
        self.assertNotIn("bank_pending_transaction", session)
        self.assertEqual((user["코인"], user["대출금"]), (7_000, 6_000))
        st.toast.assert_called_with("saved")

    def test_borrow_submit_sets_the_animation_key(self):
        source = (ROOT / "views/bank/draw.py").read_text(encoding="utf-8")
        self.assertIn('BORROW_SUCCESS_KEY = "bank_borrow_success"', source)
        self.assertIn('st.session_state.pop(BORROW_SUCCESS_KEY, False)', source)
        self.assertIn('success_state_key=BORROW_SUCCESS_KEY', source)
        self.assertIn('bank-borrow-approved', source)
        self.assertNotIn('bank-borrow-stamp-object', source)

    def test_final_repayment_can_clear_a_subunit_balance(self):
        limit = function_from("views/bank/repay.py", "_repayment_limit", {"UNIT": 1_000})
        select = function_from("views/bank/repay.py", "_selected_repayment", {"UNIT": 1_000})
        self.assertEqual(select(limit(900, 650), 1_000), 650)
        self.assertEqual(select(limit(600, 650), 1_000), 0)
        self.assertEqual(select(limit(1_300, 2_000), 2_000), 1_000)

    def test_existing_button_stamp_moves_and_ink_is_below(self):
        css = (ROOT / "views/bank/draw.css").read_text(encoding="utf-8")
        self.assertIn(".st-key-bank-borrow-submit::after", css)
        self.assertIn("bank-borrow-button-stamp-press", css)
        self.assertIn("bank-borrow-button-ink", css)
        self.assertIn("bottom: -2.6cqw", css)
        self.assertIn(":has(.bank-borrow-approved)", css)
        self.assertNotIn(".bank-draw-document-title:has(.bank-borrow-stamp-effect)", css)


if __name__ == "__main__":
    unittest.main()
