"""Regression tests for bank navigation and post-save stamping."""

import ast
from pathlib import Path
from types import SimpleNamespace
import unittest


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
        saved = []
        class Worksheet:
            def find(self, student_id, in_column):
                self_id = (student_id, in_column)
                saved.append(self_id)
                return SimpleNamespace(row=3)
            def update(self, range_name, values):
                saved.append((range_name, values))

        session = State(current_user_data={"학번": "student01", "코인": 1_250, "대출금": 3_000})
        notices = []
        st = SimpleNamespace(session_state=session,
                             toast=lambda message: notices.append(message),
                             rerun=lambda: notices.append("rerun"),
                             error=lambda message: notices.append("error"))
        save = function_from("views/bank_forms.py", "_save_balances",
                             {"st": st, "init_gspread": Worksheet})
        save(6_250, 8_000, "saved", success_state_key="bank_borrow_success")
        self.assertTrue(session.bank_borrow_success)
        self.assertEqual(session.current_user_data["코인"], 6_250)
        self.assertEqual(saved[-1], ("C3:D3", [[6_250, 8_000]]))
        self.assertEqual(notices, ["saved", "rerun"])

        class BrokenWorksheet(Worksheet):
            def update(self, range_name, values):
                raise RuntimeError("not saved")

        failed_state = State(current_user_data={"학번": "student01", "코인": 1_250, "대출금": 3_000})
        failures = []
        failed_st = SimpleNamespace(session_state=failed_state,
                                    toast=lambda _: failures.append("toast"),
                                    rerun=lambda: failures.append("rerun"),
                                    error=lambda _: failures.append("error"))
        failed_save = function_from("views/bank_forms.py", "_save_balances",
                                    {"st": failed_st, "init_gspread": BrokenWorksheet})
        failed_save(6_250, 8_000, "not saved", success_state_key="bank_borrow_success")
        self.assertNotIn("bank_borrow_success", failed_state)
        self.assertEqual(failed_state.current_user_data["코인"], 1_250)
        self.assertEqual(failures, ["error"])

    def test_borrow_submit_sets_the_animation_key(self):
        source = (ROOT / "views/bank_draw.py").read_text(encoding="utf-8")
        self.assertIn('BORROW_SUCCESS_KEY = "bank_borrow_success"', source)
        self.assertIn('st.session_state.pop(BORROW_SUCCESS_KEY, False)', source)
        self.assertIn('success_state_key=BORROW_SUCCESS_KEY', source)
        self.assertIn('bank-borrow-stamp-effect', source)


if __name__ == "__main__":
    unittest.main()
