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
        navigate = function_from("views/bank.py", "_navigate",
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

    def test_stamp_flag_is_set_only_after_successful_persistence(self):
        class Changed(Exception):
            coins = 2_000
            loan = 1_000

        worksheet = object()
        persist = Mock()
        user = {"학번": 1234, "코인": "1,250", "대출금": ""}
        session = State(current_user="01234", current_user_data=user)
        st = Mock(session_state=session)
        save = function_from("views/bank_forms.py", "_save_balances", {
            "st": st, "init_gspread": lambda: worksheet,
            "save_bank_balances": persist, "BankBalancesChanged": Changed,
            "account_amount": account_amount,
        })

        persist.side_effect = RuntimeError("not saved")
        save(6_250, 5_000, "failed", success_state_key="bank_borrow_success")
        self.assertNotIn("bank_borrow_success", session)
        self.assertEqual((user["코인"], user["대출금"]), ("1,250", ""))
        st.error.assert_called_once()
        st.toast.assert_not_called()
        st.rerun.assert_not_called()

        persist.side_effect = Changed()
        save(6_250, 5_000, "stale", success_state_key="bank_borrow_success")
        self.assertNotIn("bank_borrow_success", session)
        self.assertEqual((user["코인"], user["대출금"]), (2_000, 1_000))
        st.rerun.assert_called_once()

        persist.side_effect = None
        save(7_000, 6_000, "saved", success_state_key="bank_borrow_success")
        persist.assert_called_with(worksheet, "01234", 7_000, 6_000,
                                   expected_coins=2_000, expected_loan=1_000)
        self.assertTrue(session.bank_borrow_success)
        self.assertEqual((user["코인"], user["대출금"]), (7_000, 6_000))
        st.toast.assert_called_with("saved")

    def test_borrow_submit_sets_the_animation_key(self):
        source = (ROOT / "views/bank_draw.py").read_text(encoding="utf-8")
        self.assertIn('BORROW_SUCCESS_KEY = "bank_borrow_success"', source)
        self.assertIn('st.session_state.pop(BORROW_SUCCESS_KEY, False)', source)
        self.assertIn('success_state_key=BORROW_SUCCESS_KEY', source)
        self.assertIn('bank-borrow-approved', source)
        self.assertNotIn('bank-borrow-stamp-object', source)

    def test_final_repayment_can_clear_a_subunit_balance(self):
        limit = function_from("views/bank_repay.py", "_repayment_limit", {"UNIT": 1_000})
        select = function_from("views/bank_repay.py", "_selected_repayment", {"UNIT": 1_000})
        self.assertEqual(select(limit(900, 650), 1_000), 650)
        self.assertEqual(select(limit(600, 650), 1_000), 0)
        self.assertEqual(select(limit(1_300, 2_000), 2_000), 1_000)

    def test_existing_button_stamp_moves_and_ink_is_below(self):
        css = (ROOT / "views/bank_draw.css").read_text(encoding="utf-8")
        self.assertIn(".st-key-bank-borrow-submit::after", css)
        self.assertIn("bank-borrow-button-stamp-press", css)
        self.assertIn("bank-borrow-button-ink", css)
        self.assertIn("bottom: -2.6cqw", css)
        self.assertIn(":has(.bank-borrow-approved)", css)
        self.assertNotIn(".bank-draw-document-title:has(.bank-borrow-stamp-effect)", css)


if __name__ == "__main__":
    unittest.main()
