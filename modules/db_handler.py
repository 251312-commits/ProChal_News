import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# 구글 시트 기본 URL 설정
SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1-Kx4qK9SOV3fXF9q9jIYGefPDPQl_gkZK6iHUabKwmE/edit?usp=drivesdk"

# ==========================================
# 1. 구글 시트 워크시트 캐싱 연결
# ==========================================
@st.cache_resource
def get_users_worksheet():
    """Users 워크시트 객체를 연결하고 캐싱합니다."""
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=scope
    )
    gc = gspread.authorize(credentials)
    doc = gc.open_by_url(SPREADSHEET_URL)
    return doc.worksheet("Users")


@st.cache_resource
def get_news_worksheet():
    """News 워크시트 객체를 연결하고 캐싱하며, 없을 경우 자동 생성합니다."""
    ws_users = get_users_worksheet()
    doc = ws_users.spreadsheet
    try:
        return doc.worksheet("News")
    except Exception:
        news_ws = doc.add_worksheet(title="News", rows="100", cols="3")
        news_ws.append_row(["URL", "Count", "Title"])
        return news_ws


# ==========================================
# 2. 사용자(Users) 데이터 조작 함수
# ==========================================
def get_all_users():
    """전체 사용자 목록을 가져옵니다."""
    ws = get_users_worksheet()
    return ws.get_all_records()


def find_user_by_student_id(student_id: str):
    """
    학번(student_id)으로 사용자를 검색합니다.
    (행 번호 index와 사용자 정보를 반환)
    """
    users_data = get_all_users()
    clean_target_id = str(student_id).strip().replace('.0', '')

    for idx, user in enumerate(users_data):
        raw_id = str(user.get('학번', ''))
        clean_id = raw_id.split('.')[0] if '.' in raw_id else raw_id.strip()
        if clean_id == clean_target_id:
            # gspread는 1-based index이고 헤더가 1행이므로 row index = idx + 2
            return idx + 2, user
            
    return None, None


def create_user(student_id: str, username: str, initial_coins: int = 5000, streak: int = 0, referral: str = "", password: str = ""):
    """새로운 사용자를 등록합니다."""
    ws = get_users_worksheet()
    new_row = [str(student_id), username, initial_coins, streak, referral, password]
    ws.append_row(new_row)


def update_user_coins_and_streak(row_idx: int, coins: int, streak: int):
    """특정 사용자의 코인 및 연승 수를 업데이트합니다."""
    ws = get_users_worksheet()
    ws.update_cell(row_idx, 3, coins)   # 3열: 코인
    ws.update_cell(row_idx, 4, streak)  # 4열: 연승


def add_referral_reward(referral_student_id: str, reward_coins: int = 3000):
    """추천인 학번을 찾아 보상 코인을 추가 지급합니다."""
    if not referral_student_id:
        return False

    row_idx, user_info = find_user_by_student_id(referral_student_id)
    if user_info and row_idx:
        ws = get_users_worksheet()
        current_coins = int(user_info.get('코인', 0))
        new_coins = current_coins + reward_coins
        ws.update_cell(row_idx, 3, new_coins)
        return True
    return False


# ==========================================
# 3. 뉴스(News) 데이터 조작 함수
# ==========================================
def get_all_news():
    """등록된 전체 뉴스 데이터를 가져옵니다."""
    ws_news = get_news_worksheet()
    return ws_news.get_all_records()


def update_news_count(row_idx: int, new_count: int):
    """특정 뉴스의 선택 횟수(Count)를 업데이트합니다."""
    ws_news = get_news_worksheet()
    ws_news.update_cell(row_idx, 2, new_count)  # 2열: Count


def update_news_title(row_idx: int, title: str):
    """특정 뉴스의 제목(Title)을 업데이트합니다."""
    ws_news = get_news_worksheet()
    ws_news.update_cell(row_idx, 3, title)  # 3열: Title
