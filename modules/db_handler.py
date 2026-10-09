import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

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
