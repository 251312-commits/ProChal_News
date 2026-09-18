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
    return int(round(score * 100))

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
def show_bank(): show_placeholder_page("🏦 은행")

# ------------------------------------------
# 레이아웃
# ------------------------------------------
def inject_casino_theme():
    st.markdown(
        """
        <style>
        /* 1. 깔끔한 블랙 배경 */
        .stApp {
            background-color: #0a0a0a !important; /* 깊은 검은색 */
            background-image: none !important; /* 기존 붉은 이미지 제거 */
            color: #ffffff;
        }

        /* 2. 로그인 타이틀 등 (골드 네온) */
        h1, h2, h3 {
            color: #FFD700 !important;
            text-shadow: 0 0 10px #FFD700, 0 0 20px #B8860B !important;
            text-align: center;
        }

        /* 3. 메인 상단 말풍선 (금색 그라데이션) */
        .header-container {
            display: flex;
            align-items: center;
            justify-content: center;
            margin-top: 10px;
            margin-bottom: 25px;
        }
        .speech-bubble {
            position: relative;
            background: linear-gradient(135deg, #FFDF00 0%, #D4AF37 100%);
            color: #000000;
            padding: 10px 25px;
            border-radius: 12px;
            font-size: 1.6rem;
            font-weight: 900;
            box-shadow: 0 4px 15px rgba(212, 175, 55, 0.5);
            border: 2px solid #FFF8DC;
            z-index: 2;
        }
        .speech-bubble::after {
            content: '';
            position: absolute;
            top: 50%;
            right: -14px;
            margin-top: -10px;
            border-left: 14px solid #D4AF37;
            border-top: 10px solid transparent;
            border-bottom: 10px solid transparent;
        }
        .diagonal-text {
            transform: rotate(-10deg);
            color: #FFD700;
            font-size: 1.1rem;
            font-weight: 900;
            margin-left: 20px;
            text-shadow: 2px 2px 5px rgba(0,0,0,0.9);
            z-index: 1;
        }

        /* 4. VIP 코인 정보창 (블랙 & 골드 테두리) */
        .vip-info-box {
            background: linear-gradient(135deg, #1a1a1a, #000000);
            color: #FFD700;
            padding: 15px;
            border: 1px solid #FFD700;
            border-radius: 10px;
            font-size: 1.3rem;
            font-weight: 900;
            text-align: center;
            box-shadow: 0 4px 15px rgba(255, 215, 0, 0.2);
            margin-bottom: 30px;
        }

        /* 5. 버튼 & 입력창 스타일 덮어쓰기 */
        .stButton > button {
            background: linear-gradient(to right, #B8860B, #FFDF00) !important;
            color: #000 !important;
            font-weight: 900 !important;
            font-size: 1.2rem !important;
            border-radius: 8px !important;
            border: none !important;
        }
        .stTextInput > div > div > input {
            background-color: #111 !important;
            color: #FFD700 !important;
            border: 2px solid #D4AF37 !important;
            text-align: center;
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

    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        student_id = st.text_input("학번 입력 (5자리)", max_chars=5, placeholder="입력 후 반드시 Enter를 눌러주세요")
        
        if student_id:
            clean_id = student_id.strip()
            
            if clean_id.isdigit():
                users_data = ws.get_all_records() 
                
                # 🚨 무조건 문자열로 변환 후 찌꺼기를 잘라내고 비교하는 로직
                user_info = None
                for item in users_data:
                    raw_sheet_id = str(item.get('학번', ''))
                    
                    # '12345.0' 등 소수점이 섞여 들어오면 '.'을 기준으로 쪼개서 앞자리(12345)만 취함
                    if '.' in raw_sheet_id:
                        sheet_id = raw_sheet_id.split('.')[0]
                    else:
                        sheet_id = raw_sheet_id.strip()
                        
                    if sheet_id == clean_id:
                        user_info = item
                        break
                
                if user_info:
                    st.success(f"🎟️ VIP 확인 완료: {user_info.get('아이디', '알 수 없음')}님")
                    if st.button("입장하기 (Log In)", use_container_width=True):
                        st.session_state.current_user = clean_id
                        st.session_state.current_user_data = user_info
                        change_page('main')
                else:
                    st.info("신규 플레이어입니다. 닉네임을 설정해주세요.")
                    username = st.text_input("닉네임 (미입력 시 '익명' 처리)", placeholder="도박사_01")
                    referral = st.text_input("추천인 학번 (선택사항)")
                    
                    if st.button("가입 및 입장", use_container_width=True):
                        final_username = username if username else f"익명_{clean_id}"
                        initial_coins = 5000
                        
                        # 추천인 학번 확인에도 동일한 방식 적용
                        if referral:
                            clean_referral = referral.strip()
                            referral_info = None
                            
                            for item in users_data:
                                raw_ref_id = str(item.get('학번', ''))
                                if '.' in raw_ref_id:
                                    ref_id = raw_ref_id.split('.')[0]
                                else:
                                    ref_id = raw_ref_id.strip()
                                    
                                if ref_id == clean_referral:
                                    referral_info = item
                                    break
                            
                            if referral_info:
                                row_idx = users_data.index(referral_info) + 2 
                                new_coins = int(referral_info.get('코인', 0)) + 3000
                                ws.update_cell(row_idx, 3, new_coins)
                                initial_coins += 1000
                                st.toast(f"🎉 추천인 보상! 본인 +1000 코인, {clean_referral}님 +3000 코인 지급!")
                            else:
                                st.toast("해당 학번이 없어 추천인 보상이 지급되지 않았습니다.")
                        
                        # 시트에 새로 저장할 때 문자열 그대로 넘겨서 데이터 타입 충돌 방지
                        new_row = [clean_id, final_username, initial_coins, 0, referral.strip()]
                        ws.append_row(new_row)
                        
                        st.session_state.current_user = clean_id
                        st.session_state.current_user_data = {
                            "학번": clean_id, "아이디": final_username, "코인": initial_coins, "연승": 0
                        }
                        change_page('main')
            else:
                st.error("학번은 숫자로만 입력해주세요.")

def show_main_page():
    # 1. 자동 새로고침 및 데이터 갱신
    st_autorefresh(interval=600000, limit=None, key="auto_refresh")

    users_data = ws.get_all_records()
    updated_info = next((item for item in users_data if str(item.get('학번', '')).strip().replace('.0', '') == st.session_state.current_user), None)
    
    if updated_info:
        st.session_state.current_user_data = updated_info

    user = st.session_state.current_user_data
    
    # 🚨 안전장치: 유저 데이터가 유실되었을 경우 로그인 화면으로 강제 복귀
    if not user:
        change_page('login')
        return
    
    # 2. 상단 말풍선 타이틀 & 사선 부제목
    st.markdown(
        """
        <div class="header-container">
            <div class="speech-bubble">NEWS CASINO</div>
            <div class="diagonal-text">오늘의 잭팟은?</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 3. VIP 유저 정보 (안전한 .get() 메서드 사용)
    st.markdown(
        f"""
        <div class="vip-info-box" style="margin-bottom: 30px;">
            🎰 [VIP] {user.get('아이디', '알 수 없음')} | 💰 {user.get('코인', 0)} COIN | 🔥 {user.get('연승', 0)} WINS
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    # 4. 사용할 와이드 배너 이미지 URL 목록
    img_urls = [
    "https://picsum.photos/id/10/800/110", # 0. 은행
    "https://picsum.photos/id/20/800/110", # 1. 랭킹
    "https://picsum.photos/id/30/800/110", # 2. 게임 1
    "https://picsum.photos/id/40/800/110", # 3. 게임 2
    "https://picsum.photos/id/50/800/110", # 4. 게임 3
    "https://picsum.photos/id/60/800/110", # 5. 게임 4
    "https://picsum.photos/id/70/800/110", # 6. 게임 5
    "https://picsum.photos/id/80/800/110"  # 7. 교환소
]
    
    # 5. 세로형 와이드 배너 단일 렌더링
    clicked_menu = clickable_images(
        img_urls,
        titles=["🏦 은행", "🏆 랭킹", "게임 1", "게임 2", "게임 3", "게임 4", "게임 5", "🛒 교환소"],
        div_style={
            "display": "flex", 
            "flex-direction": "column", 
            "gap": "15px",
            "justify-content": "center",
            "padding-bottom": "30px"
        },
        img_style={
            "width": "100%",            
            "height": "110px",          
            "object-fit": "cover",      
            "border-radius": "10px", 
            "border": "2px solid #FFD700", 
            "box-shadow": "0 4px 10px rgba(255, 215, 0, 0.2)",
            "cursor": "pointer"
        },
        key="main_menu_banners"
    )

    # 6. 배너 클릭 라우팅
    if clicked_menu == 0: change_page('bank')
    elif clicked_menu == 1: change_page('ranking')
    elif clicked_menu == 2: change_page('game_1')
    elif clicked_menu == 3: change_page('game_2')
    elif clicked_menu == 4: change_page('game_3')
    elif clicked_menu == 5: change_page('game_4')
    elif clicked_menu == 6: change_page('game_5')
    elif clicked_menu == 7: change_page('exchange')
    
    # 4. 사용할 와이드 배너 이미지 URL 목록 (은행, 랭킹을 최상단으로 배치)
    img_urls = [
        "https://images.unsplash.com/photo-1601597111158-2fceff292cdc?w=800", # 0. 은행 (금고/돈 사진)
        "https://images.unsplash.com/photo-1579547621113-e4bb34dc4bb6?w=800", # 1. 랭킹 (트로피/왕관 사진)
        "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=800", # 2. 게임 1
        "https://images.unsplash.com/photo-1511512578047-dfb367046420?w=800", # 3. 게임 2
        "https://images.unsplash.com/photo-1596838132731-3301c3fd4317?w=800", # 4. 게임 3
        "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=800", # 5. 게임 4
        "https://images.unsplash.com/photo-1511512578047-dfb367046420?w=800", # 6. 게임 5
        "https://images.unsplash.com/photo-1596838132731-3301c3fd4317?w=800"  # 7. 교환소
    ]
    
    # 5. 세로형 와이드 배너 생성
    clicked_menu = clickable_images(
        img_urls,
        titles=["🏦 은행", "🏆 랭킹", "게임 1", "게임 2", "게임 3", "게임 4", "게임 5", "🛒 교환소"],
        div_style={
            "display": "flex", 
            "flex-direction": "column", 
            "gap": "15px",
            "justify-content": "center"
        },
        img_style={
            "width": "100%",            # 모바일 꽉 차게
            "height": "110px",          # 가로로 긴 형태 유지
            "object-fit": "cover",      
            "border-radius": "10px", 
            "border": "2px solid #ffd700", 
            "box-shadow": "0 4px 10px rgba(255, 42, 42, 0.3)",
            "cursor": "pointer"
        },
        key="main_menu_banners_2"
    )

    # 6. 배너 클릭 시 페이지 이동 (라우팅)
    if clicked_menu == 0: change_page('bank')     # 은행 연결 추가됨
    elif clicked_menu == 1: change_page('ranking') # 랭킹 연결 추가됨
    elif clicked_menu == 2: change_page('game_1')
    elif clicked_menu == 3: change_page('game_2')
    elif clicked_menu == 4: change_page('game_3')
    elif clicked_menu == 5: change_page('game_4')
    elif clicked_menu == 6: change_page('game_5')
    elif clicked_menu == 7: change_page('exchange')
        
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
# 🚨 테마 적용 함수 호출: 이 한 줄을 추가하면 모든 페이지에 카지노 레이아웃이 씌워집니다.
inject_casino_theme()

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
elif st.session_state.page == 'ranking': show_ranking()
