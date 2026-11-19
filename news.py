import streamlit as st
import streamlit.components.v1 as components

from modules.news_ai import load_ai_model, bring_article, pick_3_lowest_count_news
from modules.ui_components import change_page, inject_casino_theme
from modules.loading_feedback import render_loading_feedback

from sounds.bgm import init_seamless_bgm, stop_bgm

from views.login import show_login_page
from views.main import show_main_page
from views.ranking import show_ranking
from views.bank import show_bank
from modules.badge_notifications import show_pending_badge_award

from games.game1.game1 import show_game_1, show_game_1_tutorial
from games.game2 import show_game_2
from games.game3 import show_game_3
from games.game4 import show_game_4, show_game_4_tutorial
from games.game5 import show_game_5, _show_article_detail, _show_result
from games.game5 import show_game_5_tutorial

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
    init_seamless_bgm(
        INTRO_BGM_URL, LOOP_BGM_URL,
        show_controls=st.session_state.page == 'main',
        suspend_for_result=(st.session_state.page == 'game_1'
                            and 'game_1_result' in st.session_state),
    )
    
    if st.session_state.page == 'main':
        show_main_page()
    elif st.session_state.page == 'ranking':
        show_ranking()
    elif st.session_state.page in ('bank', 'draw_loan', 'pay_loan'):
        show_bank()
    elif st.session_state.page == 'game_1_tutorial':
        show_game_1_tutorial()
    elif st.session_state.page == 'game_1':
        show_game_1()
    elif st.session_state.page == 'game_2':
        show_game_2()
    elif st.session_state.page == 'game_3':
        show_game_3()
    elif st.session_state.page == 'game_4_tutorial':
        show_game_4_tutorial()
    elif st.session_state.page == 'game_4':
        show_game_4()
    elif st.session_state.page == 'game_5':
        show_game_5()
    elif st.session_state.page == 'game_5_article':
        _show_article_detail()
    elif st.session_state.page == 'game_5_result':
        _show_result()
    elif st.session_state.page == 'game_5_tutorial':
        show_game_5_tutorial()

    # Show queued achievements after the active page has rendered. Game 1's
    # fullscreen musical reveal displays the same cards only after the finale.
    gallery_opened = st.session_state.pop("_badge_gallery_opened_this_run", False)
    result = st.session_state.get("game_1_result") or {}
    game1_cinematic = (
        st.session_state.page == "game_1" and isinstance(result, dict)
        and "predicted_digits" in result
    )
    if not gallery_opened and not game1_cinematic:
        show_pending_badge_award()

# A fresh render token clears client feedback after work has completed.
render_loading_feedback(enabled=st.session_state.page != "login")
