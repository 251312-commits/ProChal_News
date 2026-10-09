import streamlit as st
import streamlit.components.v1 as components

# DB 및 AI 모듈
from db_handler import init_gspread, init_news_sheet
from news_ai import load_ai_model, bring_article, pick_3_lowest_count_news

# UI 컴포넌트 및 BGM 모듈
from bgm import init_seamless_bgm, stop_bgm
from ui_components import change_page, inject_casino_theme

# 각 페이지 함수 모듈
from login import show_login_page
from main import show_main_page
from ranking import show_ranking
from game1 import show_game_1

ws = init_gspread()
ws_news = init_news_sheet()

# ==========================================
# 4. Streamlit 앱 라우팅 및 상태 관리
# ==========================================
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'login_step' not in st.session_state:
    st.session_state.login_step = 1
if 'temp_student_id' not in st.session_state:
    st.session_state.temp_student_id = None
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'current_user_data' not in st.session_state:
    st.session_state.current_user_data = None
        
# ==========================================
# 페이지 라우터 구역
# ==========================================
inject_casino_theme()

INTRO_BGM_URL = "https://raw.githubusercontent.com/251312-commits/ProChal_News/main/sounds/intro.mp3"
LOOP_BGM_URL = "https://raw.githubusercontent.com/251312-commits/ProChal_News/main/sounds/loop.mp3"

if st.session_state.page == 'login':
    stop_bgm()  # 로그인 화면에서는 BGM 정지
    show_login_page()
else:
    # 로그인 완료 후 메인/랭킹/게임 화면 진입 시 BGM 실행 (중복 재생 없음)
    init_seamless_bgm(INTRO_BGM_URL, LOOP_BGM_URL)
    
    if st.session_state.page == 'main':
        show_main_page()
    elif st.session_state.page == 'ranking':
        show_ranking()
    elif st.session_state.page == 'game_1':
        show_game_1()
