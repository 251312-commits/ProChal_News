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

# ==========================================
# 1. 효율성 극대화: AI 모델 캐싱 (최초 1회만 로드)
# ==========================================
@st.cache_resource
def load_ai_model():
    model_name = "BAAI/bge-reranker-v2-m3"
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model.eval()
    return tokenizer, model

tokenizer, model = load_ai_model()

# ==========================================
# 2. 제공해주신 기사 전처리 함수들
# ==========================================
UI_WORDS = {'광고', '본문', '전체재생', '동영상 고정', '동영상 고정 취소', '이미지 확대', '사진 확대', '기사본문'}

def get_clean_title(article_obj, domain: str) -> str:
    title = article_obj.title.strip()
    if 'kbs.co.kr' in domain or title in ['KBS', 'KBS 뉴스', 'KBS뉴스', 'KBS 기사', '']:
        og_title = article_obj.meta_data.get('og', {}).get('title')
        if og_title:
            title = og_title
        elif article_obj.html:
            soup = BeautifulSoup(article_obj.html, 'html.parser')
            og_meta = soup.find('meta', property='og:title')
            if og_meta and og_meta.get('content'):
                title = og_meta['content']
            else:
                h1_tag = soup.find('h1')
                if h1_tag:
                    title = h1_tag.get_text()

    suffixes = [' | KBS 뉴스', ' | KBS', ' - KBS뉴스', ' - KBS', ' | 연합뉴스', ' | 한겨레', ' - MBC뉴스']
    for suffix in suffixes:
        if title.endswith(suffix):
            title = title[:-len(suffix)].strip()
    return title

def is_ad_or_ui_line(line: str) -> bool:
    s = line.strip()
    if not s: return True
    if s in UI_WORDS or s in {'[광고]', '(광고)', 'AD', 'Advertisement'}: return True
    if re.match(r'^(광고|AD)\s*[:\-\|\[\(]', s) or s.endswith('(광고)'): return True
    if '광고' in s and len(s) <= 20 and not re.search(r'[다요함음]\s*[\.\!\?]?$', s): return True
    return False

def remove_duplicate_and_ui_lines(text: str) -> str:
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    cleaned_lines = [line for line in lines if not is_ad_or_ui_line(line)]
    return '\n\n'.join(list(dict.fromkeys(cleaned_lines)))

def clean_common_text(text: str) -> str:
    text = re.sub(r'【[^】]*】', '', text)
    text = re.sub(r'(사진|이미지)\s*확대[^\n]*', '', text)
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z2-9]{2,}', '', text)
    text = re.sub(r'\[[^\]]*(제공|DB|재판매|캡처|사진)[^\]]*\]', '', text)
    text = re.sub(r'무단\s*전재[^\n]*', '', text)
    return remove_duplicate_and_ui_lines(text)

def bring_article(url: str):
    article_obj = Article(url, language='ko')
    article_obj.download()
    article_obj.parse()
    domain = urlparse(url).netloc
    title = get_clean_title(article_obj, domain)
    clean_article = clean_common_text(article_obj.text)
    return title, clean_article
    
def summary(article):
    # 개발 중 임시 반환값
    return article if article else "요약본 예시 문장입니다."

def similarity_check(summary_text, title):
    inputs = tokenizer(summary_text, title, padding=True, truncation=True, return_tensors="pt", max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits.squeeze(-1)
        score = torch.sigmoid(logits).item()
    return round(score, 4)

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
    
    # 🚨 본인 구글 시트 URL 입력 필요
    sheet_url = "https://docs.google.com/spreadsheets/d/1-Kx4qK9SOV3fXF9q9jIYGefPDPQl_gkZK6iHUabKwmE/edit?usp=drivesdk"
    doc = gc.open_by_url(sheet_url)
    worksheet = doc.worksheet("Users")
    return worksheet

ws = init_gspread()

# ==========================================
# 4. Streamlit 앱 라우팅 및 상태 관리
# ==========================================
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'current_user_data' not in st.session_state:
    st.session_state.current_user_data = None

def change_page(page_name):
    st.session_state.page = page_name
    st.rerun()

# ------------------------------------------
# 미구현 기능 플레이스홀더 (에러 방지용)
# ------------------------------------------
def show_placeholder_page(title_name):
    st.title(title_name)
    st.info("🎮 해당 콘텐츠는 현재 준비 중입니다.")
    if st.button("⬅️ 메인으로 돌아가기"):
        change_page('main')

def show_game_1(): show_placeholder_page("게임 1")
def show_game_2(): show_placeholder_page("게임 2")
def show_game_3(): show_placeholder_page("게임 3")
def show_game_4(): show_placeholder_page("게임 4")
def show_game_5(): show_placeholder_page("게임 5")
def show_exchange(): show_placeholder_page("🛒 교환소")

# ------------------------------------------
# 레이아웃
# ------------------------------------------
def inject_casino_theme():
    st.markdown(
        """
        <style>
        /* 1. 빨강/검정 카지노 배경 이미지 & 다크 필터 */
        .stApp {
            /* 룰렛/카드의 묵직한 레드블랙 느낌 이미지 URL */
            background-image: url("https://images.unsplash.com/photo-1596838132731-3301c3fd4317?q=80&w=1920"); 
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            /* 배경을 붉고 어둡게 눌러주는 효과 */
            background-color: rgba(30, 0, 0, 0.85); 
            background-blend-mode: multiply;
            color: #ffffff;
        }

        /* 2. 네온 사인 타이틀 (레드 & 골드) */
        h1 {
            color: #ff2a2a !important;
            text-shadow: 0 0 10px #ff2a2a, 0 0 20px #8b0000, 0 0 30px #8b0000 !important;
            text-align: center;
        }
        h2, h3 {
            color: #ffd700 !important;
            text-shadow: 0 0 10px #ffd700, 0 0 20px #aa771c !important;
            text-align: center;
        }

        /* 3. 화려한 베팅 버튼 스타일 */
        .stButton > button {
            background: linear-gradient(to right, #8b0000, #ff2a2a) !important;
            border: 1px solid #ffd700 !important;
            color: white !important;
            font-weight: 900 !important;
            font-size: 1.2rem !important;
            border-radius: 8px !important;
            box-shadow: 0 4px 15px 0 rgba(255, 42, 42, 0.6) !important;
            transition: all 0.3s ease-in-out !important;
            width: 100%;
        }
        .stButton > button:hover {
            transform: scale(1.05);
            box-shadow: 0 6px 20px 0 rgba(255, 215, 0, 0.8) !important;
            border: 1px solid #ffffff !important;
        }

        /* 4. 텍스트 입력창 (다크 & 레드 포인트) */
        .stTextInput > div > div > input {
            background-color: rgba(0, 0, 0, 0.7) !important;
            color: #ffd700 !important;
            border: 2px solid #8b0000 !important;
            border-radius: 5px !important;
            font-weight: bold;
            text-align: center;
        }
        .stTextInput > div > div > input:focus {
            border-color: #ffd700 !important;
            box-shadow: 0 0 10px #ffd700 !important;
        }

        /* 5. VIP 코인 정보창 */
        .vip-info-box {
            background: linear-gradient(135deg, #2a0800, #5c0000, #2a0800);
            color: #ffd700;
            padding: 15px;
            border: 1px solid #ffd700;
            border-radius: 10px;
            font-size: 1.3rem;
            font-weight: 900;
            text-align: center;
            box-shadow: 0 4px 15px rgba(255, 215, 0, 0.3);
            margin-bottom: 20px;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

# ------------------------------------------
# 메인 화면 정의
# ------------------------------------------
def show_login_page():
    # 상단 텍스트를 화려하게 변경
    st.markdown("<h1>🎰 NEWS CASINO VIP 🎰</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 1.2rem; color: #ffd700; margin-bottom: 30px;'>선수 입장. 학번을 입력하여 게임에 참여하세요.</p>", unsafe_allow_html=True)

    # 가운데 정렬을 위해 컬럼 분할 (양옆 여백)
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        student_id = st.text_input("학번 입력 (5자리)", max_chars=5, placeholder="예: 12345")
        
        if student_id:
            if student_id.isdigit():
                users_data = ws.get_all_records() 
                user_info = next((item for item in users_data if str(item['학번']) == student_id), None)
                
                if user_info:
                    st.success(f"🎟️ VIP 확인 완료: {user_info['아이디']}님")
                    if st.button("입장하기 (Log In)"):
                        st.session_state.current_user = student_id
                        st.session_state.current_user_data = user_info
                        change_page('main')
                else:
                    st.info("신규 플레이어입니다. 닉네임을 설정해주세요.")
                    username = st.text_input("닉네임 (미입력 시 '익명' 처리)", placeholder="도박사_01")
                    referral = st.text_input("추천인 학번 (선택사항)")
                    
                    if st.button("가입 및 입장"):
                        final_username = username if username else f"익명_{student_id}"
                        initial_coins = 5000
                        
                        # (기존 추천인 처리 로직 동일하게 유지)
                        if referral:
                            referral_info = next((item for item in users_data if str(item['학번']) == referral), None)
                            if referral_info:
                                row_idx = users_data.index(referral_info) + 2 
                                new_coins = int(referral_info['코인']) + 3000
                                ws.update_cell(row_idx, 3, new_coins)
                                initial_coins += 1000
                                st.toast(f"🎉 추천인 보상!")
                            else:
                                st.toast("해당 학번이 없어 보상이 지급되지 않았습니다.")
                        
                        new_row = [student_id, final_username, initial_coins, 0, referral]
                        ws.append_row(new_row)
                        
                        st.session_state.current_user = student_id
                        st.session_state.current_user_data = {
                            "학번": student_id, "아이디": final_username, "코인": initial_coins, "연승": 0
                        }
                        change_page('main')
            else:
                st.error("학번은 숫자로만 입력해주세요.")

        else:
            st.error("학번은 5자리 숫자로 입력해주세요.")

def show_main_page():
    # 1. 자동 새로고침 및 유저 데이터 갱신
    st_autorefresh(interval=600000, limit=None, key="auto_refresh")

    users_data = ws.get_all_records()
    updated_info = next((item for item in users_data if str(item['학번']) == st.session_state.current_user), None)
    if updated_info:
        st.session_state.current_user_data = updated_info

    user = st.session_state.current_user_data
    
    # 2. 모바일 친화적인 상단 UI (컬럼 제거)
    st.markdown(
        f"""
        <div class="vip-info-box">
            🎰 [VIP] {user['아이디']} | 💰 {user['코인']} COIN | 🔥 {user['연승']} WINS
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    if st.button("🚪 로그아웃", use_container_width=True):
        st.session_state.current_user = None
        st.session_state.current_user_data = None
        change_page('login')

    st.write("") # 간격 조절
    
    # 사용할 이미지 URL 리스트 (가로로 긴 와이드 해상도 이미지를 쓰면 더 좋습니다)
    img_urls = [
        "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=800", # 게임 1
        "https://images.unsplash.com/photo-1511512578047-dfb367046420?w=800", # 게임 2
        "https://images.unsplash.com/photo-1596838132731-3301c3fd4317?w=800", # 게임 3
        "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=800", # 게임 4
        "https://images.unsplash.com/photo-1511512578047-dfb367046420?w=800", # 게임 5
        "https://images.unsplash.com/photo-1596838132731-3301c3fd4317?w=800"  # 교환소
    ]
    
    # 3. 세로형 와이드 배너 리스트 생성 (핵심 변경점)
    clicked_menu = clickable_images(
        img_urls,
        titles=["게임 1", "게임 2", "게임 3", "게임 4", "게임 5", "🛒 교환소"],
        div_style={
            "display": "flex", 
            "flex-direction": "column", # 요소를 아래로 한 줄씩 쌓음
            "gap": "15px",              # 배너 사이의 간격
            "justify-content": "center"
        },
        img_style={
            "width": "100%",            # 모바일 화면 너비에 꽉 차게
            "height": "120px",          # 가로로 긴 배너 느낌을 주는 고정 높이
            "object-fit": "cover",      # 비율이 달라도 이미지가 예쁘게 잘림
            "border-radius": "10px", 
            "border": "2px solid #ffd700", # 카지노 테마에 맞는 황금색 테두리
            "box-shadow": "0 4px 10px rgba(255, 42, 42, 0.3)",
            "cursor": "pointer"
        },
        key="main_menu_banners"
    )

    # 4. 단일 클릭 이벤트 처리 (라우팅)
    if clicked_menu == 0: change_page('game_1')
    elif clicked_menu == 1: change_page('game_2')
    elif clicked_menu == 2: change_page('game_3')
    elif clicked_menu == 3: change_page('game_4')
    elif clicked_menu == 4: change_page('game_5')
    elif clicked_menu == 5: change_page('exchange')

    st.write("")

    # 5. 하단 랭킹 버튼
    if st.button("🏆 실시간 랭킹 보기", use_container_width=True): 
        change_page('ranking')
def show_ranking():
    st.title("🏆 실시간 랭킹")
    st.markdown("보유 코인 기준 순위입니다.")
    
    users_data = ws.get_all_records()
    sorted_users = sorted(users_data, key=lambda x: int(x['코인']), reverse=True)
    
    for i, user_info in enumerate(sorted_users):
        st.write(f"**{i+1}위**: {user_info['아이디']} ({user_info['코인']} 코인)")
        
    if st.button("⬅️ 메인으로 돌아가기"): change_page('main')

# ==========================================
# 5. 페이지 라우터
# ==========================================
if st.session_state.page == 'login':
    show_login_page()
elif st.session_state.page == 'main':
    show_main_page()
elif st.session_state.page == 'game_1': show_game_1()
elif st.session_state.page == 'game_2': show_game_2()
elif st.session_state.page == 'game_3': show_game_3()
elif st.session_state.page == 'game_4': show_game_4()
elif st.session_state.page == 'game_5': show_game_5()
elif st.session_state.page == 'exchange': show_exchange()
elif st.session_state.page == 'ranking': show_ranking()
