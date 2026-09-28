import streamlit as st

# modules 분리 모듈 임포트
from modules.ui_components import (
    inject_casino_theme,
    init_seamless_bgm,
    stop_bgm
)

# views 페이지 모듈 임포트
from views.login_view import show_login_page
from views.main_view import show_main_page
from views.game1_view import show_game_1
from views.ranking_view import show_ranking

# ==========================================
# 1. 페이지 및 브라우저 글로벌 설정
# ==========================================
st.set_page_config(
    page_title="뉴스에이전놀이터",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# BGM 음원 URL
INTRO_BGM_URL = "https://raw.githubusercontent.com/251312-commits/ProChal_News/main/intro.mp3"
LOOP_BGM_URL = "https://raw.githubusercontent.com/251312-commits/ProChal_News/main/loop.mp3"

# ==========================================
# 2. 세션 상태(Session State) 초기화
# ==========================================
def init_session_state():
    """앱 구동에 필요한 기본 세션 변수들을 초기화합니다."""
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
# 3. 준비 중인 컨텐츠 플레이스홀더 화면
# ==========================================
def show_placeholder_page(title_name: str):
    """아직 개발 중인 기능 페이지의 임시 뷰"""
    st.title(title_name)
    st.info("🎮 해당 콘텐츠는 현재 준비 중입니다.")
    if st.button("⬅️ 메인으로 돌아가기", use_container_width=True):
        st.session_state.page = 'main'
        st.rerun()

# ==========================================
# 4. 메인 실행 및 페이지 라우팅
# ==========================================
def main():
    # 세션 상태 생성
    init_session_state()
    
    # 전역 테마 및 스타일 주입 (로그인 vs 메인/카지노 테마 자동 적용)
    inject_casino_theme()

    current_page = st.session_state.page

    # BGM 시스템 제어 및 페이지 라우팅
    if current_page == 'login':
        stop_bgm()  # 로그인 페이지 진입 시 BGM 끄기
        show_login_page()
    else:
        # 로그인 성공 이후 페이지 진입 시 끊김 없는 오디오 BGM 실행 (중복 재생 없음)
        init_seamless_bgm(INTRO_BGM_URL, LOOP_BGM_URL)

        # 페이지 라우터 (페이지 키 호환성 처리)
        if current_page in ['main', 'home']:
            show_main_page()
        elif current_page in ['game_1', 'game1', 'news']:
            show_game_1()
        elif current_page in ['ranking', 'hall_of_fame']:
            show_ranking()
        elif current_page in ['game_2', 'casino']:
            show_placeholder_page("🎲 게임 2 / 카지노")
        elif current_page == 'game_3':
            show_placeholder_page("🎮 게임 3")
        elif current_page == 'game_4':
            show_placeholder_page("🎮 게임 4")
        elif current_page == 'game_5':
            show_placeholder_page("🎮 게임 5")
        elif current_page == 'bank':
            show_placeholder_page("🏦 은행")
        elif current_page == 'exchange':
            show_placeholder_page("🛒 교환소")
        else:
            show_main_page()

if __name__ == "__main__":
    main()
