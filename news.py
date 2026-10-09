import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from st_clickable_images import clickable_images
from newspaper import Article
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from streamlit_autorefresh import st_autorefresh
import time
import streamlit.components.v1 as components
import random

# -------
from modules.news_ai import load_ai_model, bring_article, pick_3_lowest_count_news
from modules.db_handler import init_gspread, init_news_sheet
# -------

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

def change_page(page_name):
    st.session_state.page = page_name
    st.rerun()

def show_placeholder_page(title_name):
    st.title(title_name)
    st.info("🎮 해당 콘텐츠는 현재 준비 중입니다.")
    if st.button("⬅️ 메인으로 돌아가기"):
        change_page('main')

    if clicked_menu == 0: change_page('bank')
    elif clicked_menu == 1: change_page('ranking')
    elif clicked_menu == 2: change_page('game_1')
    elif clicked_menu == 3: change_page('game_2')
    elif clicked_menu == 4: change_page('game_3')
    elif clicked_menu == 5: change_page('game_4')
    elif clicked_menu == 6: change_page('game_5')
    elif clicked_menu == 7: change_page('exchange')
        
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
