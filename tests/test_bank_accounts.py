import sys
import unittest
from runpy import run_module
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from modules.account_math import net_coins


class BankWriteTests(unittest.TestCase):
    def setUp(self):
        with patch.dict(sys.modules, {
            "streamlit": MagicMock(), "gspread": MagicMock(),
            "google.oauth2.service_account": MagicMock(),
        }):
            db = run_module("modules.db_handler")
        self.save = db["save_bank_balances"]
        self.changed = db["BankBalancesChanged"]
        self.sheet = MagicMock()
        self.sheet.col_values.return_value = ["학번", "00011", "11011.0"]

    def test_loan_only_moves_the_wallet_and_debt_columns(self):
        self.sheet.batch_get.side_effect = [[[[5000]], []], [[[5000]], [[1000]]]]
        self.save(self.sheet, "00011", 8000, 3000, expected_coins=5000, expected_loan=0)
        self.save(self.sheet, "11011", 4000, 0, expected_coins=5000, expected_loan=1000)
        self.assertEqual([call.args[0] for call in self.sheet.batch_get.call_args_list],
                         [["C2", "G2"], ["C3", "G3"]])
        self.assertEqual([call.args[0] for call in self.sheet.batch_update.call_args_list], [
            [{"range": "C2", "values": [[8000]]}, {"range": "G2", "values": [[3000]]}],
            [{"range": "C3", "values": [[4000]]}, {"range": "G3", "values": [[0]]}],
        ])

    def test_missing_or_duplicate_student_cannot_write(self):
        for ids in (["학번"], ["학번", "11011", "11011.0"]):
            self.sheet.col_values.return_value = ids
            with self.assertRaises(LookupError):
                self.save(self.sheet, "11011", 8000, 3000, expected_coins=5000, expected_loan=0)
        self.sheet.batch_update.assert_not_called()

    def test_stale_or_invalid_balances_cannot_write(self):
        for wallet, debt in [(5100, 0), (5000, 900)]:
            self.sheet.batch_get.return_value = [[[wallet]], [[debt]]]
            with self.assertRaises(self.changed) as error:
                self.save(self.sheet, "11011", 8000, 3000, expected_coins=5000, expected_loan=0)
            self.assertEqual((error.exception.coins, error.exception.loan), (wallet, debt))
        for debt in ("문자", -1000, 1.25):
            self.sheet.batch_get.return_value = [[[5000]], [[debt]]]
            with self.assertRaises(ValueError):
                self.save(self.sheet, "11011", 8000, 3000, expected_coins=5000, expected_loan=0)
        self.sheet.batch_update.assert_not_called()


class BankAccountTests(unittest.TestCase):
    def test_borrowing_and_repaying_preserve_net_coins(self):
        self.assertEqual(net_coins("5,000", ""), 5000)
        self.assertEqual(net_coins(8000, "3000.0"), 5000)
        self.assertEqual(net_coins(7000, 2000), 5000)
        self.assertEqual(net_coins(1000, 2000), -1000)

    def test_registration_starts_debt_in_column_g(self):
        st, db = MagicMock(), MagicMock()
        st.columns.side_effect = lambda widths: [MagicMock() for _ in range(
            widths if isinstance(widths, int) else len(widths)
        )]
        st.session_state = SimpleNamespace(login_step="2_new", temp_student_id="11011")
        st.text_input.side_effect = ["학생", "pw", "pw", ""]
        st.button.side_effect = lambda label, **kwargs: label == "가입완료"
        with patch.dict(sys.modules, {
            "streamlit": st, "modules.db_handler": db, "modules.ui_components": MagicMock(),
        }):
            run_module("views.login")["show_login_page"]()
        db.init_gspread.return_value.append_row.assert_called_once_with(
            ["11011", "학생", 5000, 0, "", "pw", 0]
        )
        self.assertEqual(st.session_state.current_user_data["대출금"], 0)
