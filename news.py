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
# 메인 화면 정의
# ------------------------------------------
def show_login_page():
    st.title("뉴스 게임 서비스")
    st.markdown("학번으로 로그인하여 시작하세요.")

    student_id = st.text_input("학번을 입력하세요 (숫자 5자리)", max_chars=5)
    
    if student_id:
        if student_id.isdigit():
            users_data = ws.get_all_records() 
            user_info = next((item for item in users_data if str(item['학번']) == student_id), None)
            
            if user_info:
                st.success(f"환영합니다! {user_info['아이디']}님")
                if st.button("로그인"):
                    st.session_state.current_user = student_id
                    st.session_state.current_user_data = user_info
                    change_page('main')
                        # 신규 유저 (회원가입 절차)
            else:
                st.info("최초 로그인입니다. 프로필을 설정해주세요.")
                username = st.text_input("아이디 (랭킹용, 미입력 시 '익명' 처리)")
                referral = st.text_input("가입 초대한 친구 학번 (선택사항)")
                
                if st.button("가입 및 로그인"):
                    final_username = username if username else f"익명_{student_id}"
                    initial_coins = 5000
                    
                    # 친구 초대 보상 확인 및 처리
                    if referral:
                        referral_info = next((item for item in users_data if str(item['학번']) == referral), None)
                        
                        # 1. 초대한 친구가 이미 가입한 유저인 경우
                        if referral_info:
                            # 초대한 친구에게 2000코인 지급 (구글 시트 업데이트)
                            row_idx = users_data.index(referral_info) + 2 
                            new_coins = int(referral_info['코인']) + 2000
                            ws.update_cell(row_idx, 3, new_coins)
                            
                            # 새로 가입하는 본인에게 1000코인 추가 (총 6000코인)
                            initial_coins += 1000
                            
                            st.toast(f"초대 보상 적용 성공! 본인 1000코인, {referral}님 2000코인 추가 지급!")
                        # 2. 초대한 친구가 미가입 상태인 경우
                        else:
                            st.toast("해당 학번의 가입 내역이 없어 초대 보상이 지급되지 않았습니다.")
                    
                    new_row = [student_id, final_username, initial_coins, 0, referral]
                    ws.append_row(new_row)
                    
                    st.session_state.current_user = student_id
                    st.session_state.current_user_data = {
                        "학번": student_id, "아이디": final_username, "코인": initial_coins, "연승": 0
                    }
                    change_page('main')

        else:
            st.error("학번은 5자리 숫자로 입력해주세요.")

def show_main_page():
    # 자동 새로고침 (1분마다 갱신)
    st_autorefresh(interval=600000, limit=None, key="auto_refresh")

    users_data = ws.get_all_records()
    updated_info = next((item for item in users_data if str(item['학번']) == st.session_state.current_user), None)
    if updated_info:
        st.session_state.current_user_data = updated_info

    user = st.session_state.current_user_data
    
    # 1. 상단 바: 유저 정보 | 타이틀 | 로그아웃 (비율 3:4:1)
    top_col1, top_col2, top_col3 = st.columns([3, 4, 1])
    
    with top_col1:
        st.markdown(f"**{user['아이디']}** | 💰 {user['코인']} | 🔥 {user['연승']}")
        
    with top_col2:
        st.markdown("<h2 style='text-align: center; margin-top: -15px;'>Title</h2>", unsafe_allow_html=True)
        
    with top_col3:
        if st.button("Log out", use_container_width=True):
            st.session_state.current_user = None
            st.session_state.current_user_data = None
            change_page('login')

    st.write("") # 간격 조절
    
    # 사용할 이미지 URL 또는 로컬 경로 리스트 (예시 이미지 주소)
    game1_img = "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=300"
    game2_img = "https://images.unsplash.com/photo-1511512578047-dfb367046420?w=300"
    game3_img = "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=300"
    game4_img = "https://images.unsplash.com/photo-1511512578047-dfb367046420?w=300"
    game5_img = "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=300"
    rank_img = "https://images.unsplash.com/photo-1511512578047-dfb367046420?w=300"
    exchange_img = "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=300"
    
    # 2. 중단 그리드: 4개의 열로 분할
    mid_col1, mid_col2, mid_col3, mid_col4 = st.columns([3, 3, 1.5, 1.5])
    
    with mid_col1:
        # 1번째 이미지 버튼
                clicked_game1 = clickable_images(
            [game1_img],
            titles=["게임 1"],
            div_style={"display": "flex", "justify-content": "center"},
            img_style={
                "width": "100%",           # 컬럼 너비에 꽉 차게
                "aspect-ratio": "4/3",     # 원하는 비율 지정 (예: 16/9, 1/1, 4/3)
                "object-fit": "cover",     # 지정된 비율에 맞춰 이미지를 자름 (찌그러짐 방지)
                "border-radius": "10px", 
                "cursor": "pointer", 
                "margin-bottom": "10px"
            },
            key="game1_btn"
        )

        if clicked_game1 > -1: # 이미지가 클릭되었다면 (-1 초과)
            change_page('game_1')

        # 2번째 이미지 버튼
        clicked_game2 = clickable_images(
            [game2_img],
            titles=["게임 2"],
            div_style={"display": "flex", "justify-content": "center"},
            img_style={"width": "100%", "border-radius": "10px", "cursor": "pointer"},
            key="game2_btn"
        )
        if clicked_game2 > -1:
            change_page('game_2')
            
    with mid_col2:
        clicked_game3 = clickable_images(
            [game3_img],
            titles=["게임 3"],
            div_style={"display": "flex", "justify-content": "center"},
            img_style={"width": "100%", "border-radius": "10px", "cursor": "pointer"},
            key="game3_btn"
        )
        if clicked_game3 > -1:
            change_page('game_3')
        
        clicked_game4 = clickable_images(
            [game4_img],
            titles=["게임 4"],
            div_style={"display": "flex", "justify-content": "center"},
            img_style={"width": "100%", "border-radius": "10px", "cursor": "pointer"},
            key="game4_btn"
        )
        if clicked_game2 > -1:
            change_page('game_2')
            
    with mid_col3:
        clicked_game5 = clickable_images(
            [game5_img],
            titles=["게임 5"],
            div_style={"display": "flex", "justify-content": "center"},
            img_style={"width": "100%", "border-radius": "10px", "cursor": "pointer"},
            key="game5_btn"
        )
        if clicked_game5 > -1:
            change_page('game_5')
            
    with mid_col4:
        clicked_exchange = clickable_images(
            [exchange_img],
            titles=["교환소"],
            div_style={"display": "flex", "justify-content": "center"},
            img_style={"width": "100%", "border-radius": "10px", "cursor": "pointer"},
            key="exchange_btn"
        )
        if clicked_exchange > -1:
            change_page('exchange')

    # 3. 하단 바: 랭킹 (전체 너비 사용)
    if st.button("Ranking", use_container_width=True): 
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
