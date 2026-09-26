import streamlit as st
from views.login_view import show_login_page
from views.main_view import show_main_page
from modules.ui_components import play_bgm, stop_bgm, inject_casino_theme

# 세션 상태 초기화
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'login_step' not in st.session_state:
    st.session_state.login_step = 1

# 글로벌 테마 적용
inject_casino_theme()

# 페이지 라우팅
if st.session_state.page == 'login':
    stop_bgm()
    show_login_page()

elif st.session_state.page == 'main':
    play_bgm()
    show_main_page()