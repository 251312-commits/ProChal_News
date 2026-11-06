import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from modules.account_math import account_amount

# ==========================================
# 3. 구글 시트 연결 캐싱 (gspread)
# ==========================================
@st.cache_resource
def init_gspread():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )
    gc = gspread.authorize(credentials)
    
    sheet_url = "https://docs.google.com/spreadsheets/d/1-Kx4qK9SOV3fXF9q9jIYGefPDPQl_gkZK6iHUabKwmE/edit?usp=drivesdk"
    doc = gc.open_by_url(sheet_url)
    worksheet = doc.worksheet("Users")
    return worksheet


class BankBalancesChanged(Exception):
    def __init__(self, coins, loan):
        super().__init__("Displayed balances differ from the sheet")
        self.coins = coins
        self.loan = loan


def save_bank_balances(worksheet, student_id, coins: int, loan: int, *,
                       expected_coins: int, expected_loan: int) -> None:
    """Save the wallet (C) and debt (G) in a single Sheets request."""
    sid = str(student_id or "").strip().removesuffix(".0")
    student_ids = worksheet.col_values(1)
    matches = [
        row for row, value in enumerate(student_ids[1:], start=2)
        if str(value).strip().removesuffix(".0") == sid
    ]
    if not sid or len(matches) != 1:
        raise LookupError("Expected one student row")
    row = matches[0]
    cells = worksheet.batch_get([f"C{row}", f"G{row}"], value_render_option="UNFORMATTED_VALUE")
    current_coins, current_loan = (
        account_amount(cell[0][0] if cell and cell[0] else 0, strict=True)
        for cell in cells
    )
    if current_loan < 0:
        raise ValueError("Negative debt balance")
    if (current_coins, current_loan) != (expected_coins, expected_loan):
        raise BankBalancesChanged(current_coins, current_loan)
    worksheet.batch_update([
        {"range": f"C{row}", "values": [[coins]]},
        {"range": f"G{row}", "values": [[loan]]},
    ])


# ==========================================
# 뉴스 전용 구글 시트 워크시트 연결
# ==========================================
@st.cache_resource
def init_news_sheet():
    ws = init_gspread()  # 2. ws 객체를 먼저 가져오도록 수정
    doc = ws.spreadsheet
    try:
        return doc.worksheet("News")
    except:
        news_ws = doc.add_worksheet(title="News", rows="100", cols="3")
        news_ws.append_row(["URL", "Count", "Title"])
        return news_ws
