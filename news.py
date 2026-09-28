# news.py
import streamlit as st

# 분리된 모듈들 임포트 (파일명에 맞게 수정)
from modules.ui_components import inject_casino_theme, init_seamless_bgm, stop_bgm

from views.main_view import show_main_page
from views.ranking_view import show_ranking
from views.game1_view import show_game_1

# ==========================================
# 1. 세션 상태(Session State) 초기화
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

# 공통 함수: 페이지 이동용
def change_page(page_name):
    st.session_state.page = page_name
    st.rerun()

# ==========================================
# 2. 테마 및 BGM 설정
# ==========================================
inject_casino_theme()

INTRO_BGM_URL = "https://raw.githubusercontent.com/251312-commits/ProChal_News/main/intro.mp3" 
LOOP_BGM_URL = "https://raw.githubusercontent.com/251312-commits/ProChal_News/main/loop.mp3"

# ==========================================
# 3. 페이지 라우팅 (화면 분기)
# ==========================================
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
