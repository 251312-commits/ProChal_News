"""Account invariants and safe registration integration."""

import sys
import unittest
from runpy import run_module
from unittest.mock import MagicMock, patch

from modules.account_math import net_coins


class State(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__


class BankWriteTests(unittest.TestCase):
    def test_obsolete_direct_sheets_writer_fails_closed(self):
        with patch.dict(sys.modules, {
            "streamlit": MagicMock(), "gspread": MagicMock(),
            "google.oauth2.service_account": MagicMock(),
        }):
            db = run_module("modules.db_handler")
        sheet = MagicMock()
        with self.assertRaisesRegex(RuntimeError, "Unsafe bank write"):
            db["save_bank_balances"](
                sheet, "11011", 8000, 3000, expected_coins=5000, expected_loan=0
            )
        sheet.batch_update.assert_not_called()
        sheet.update_cell.assert_not_called()


class BankAccountTests(unittest.TestCase):
    def test_borrowing_and_repaying_preserve_net_coins(self):
        self.assertEqual(net_coins("5,000", ""), 5000)
        self.assertEqual(net_coins(8000, "3000.0"), 5000)
        self.assertEqual(net_coins(7000, 2000), 5000)
        self.assertEqual(net_coins(1000, 2000), -1000)

    def test_registration_uses_single_gateway_request_instead_of_gspread_writes(self):
        st, db, tx = MagicMock(), MagicMock(), MagicMock()
        st.columns.side_effect = lambda widths: [MagicMock() for _ in range(
            widths if isinstance(widths, int) else len(widths)
        )]
        st.session_state = State(login_step="2_new", temp_student_id="10101")
        st.text_input.side_effect = ["학생", "pw", "pw", "22022"]
        st.button.side_effect = lambda label, **kwargs: label == "가입완료"
        tx.transaction_id.return_value = "register:" + "a" * 32
        tx.register_player.return_value = {"coins": 6000, "streak": 0, "loan": 0}
        with patch.dict(sys.modules, {
            "streamlit": st, "modules.db_handler": db,
            "modules.transactions": tx, "modules.ui_components": MagicMock(),
        }):
            run_module("views.login")["show_login_page"]()
        tx.register_player.assert_called_once_with(
            "10101", "학생", "pw", "22022", "register:" + "a" * 32
        )
        self.assertEqual(st.session_state.current_user_data["코인"], 6000)
        self.assertEqual(st.session_state.current_user_data["대출금"], 0)
        self.assertEqual(st.session_state.current_user_data["대출원금"], 0)
        db.init_gspread.return_value.update_cell.assert_not_called()
        db.init_gspread.return_value.append_row.assert_not_called()

    def test_teacher_registration_uses_gateway_and_displays_assigned_id(self):
        st, db, tx = MagicMock(), MagicMock(), MagicMock()
        st.columns.side_effect = lambda widths: [MagicMock() for _ in range(
            widths if isinstance(widths, int) else len(widths)
        )]
        st.session_state = State(login_step="2_teacher")
        st.text_input.side_effect = ["선생님", "pw", "pw"]
        st.button.side_effect = lambda label, **kwargs: label == "선생님 가입완료"
        tx.transaction_id.return_value = "register_teacher:" + "a" * 32
        tx.register_teacher.return_value = {
            "student_id": "40101",
            "balances": {"coins": 5000, "streak": 0, "loan": 0, "principal": 0},
        }
        with patch.dict(sys.modules, {
            "streamlit": st, "modules.db_handler": db,
            "modules.transactions": tx, "modules.ui_components": MagicMock(),
        }):
            run_module("views.login")["show_login_page"]()
        tx.register_teacher.assert_called_once_with(
            "선생님", "pw", "register_teacher:" + "a" * 32,
        )
        self.assertEqual(st.session_state.current_user, "40101")
        self.assertEqual(st.session_state.teacher_registered_id, "40101")
        self.assertEqual(st.session_state.login_step, "teacher_success")
        db.init_gspread.return_value.append_row.assert_not_called()


if __name__ == "__main__":
    unittest.main()
