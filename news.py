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
def inject_streaming_theme():
    # 1. 다크 테마 및 빨간색 포인트 CSS
    st.markdown(
        """
        <style>
        /* 전체 배경 (어두운 회색/검정) */
        .stApp {
            background-color: #141414 !important; 
            color: #ffffff;
        }
        /* 사이드바 배경 */
        [data-testid="stSidebar"] {
            background-color: #000000 !important;
            border-right: 1px solid #333;
        }
        /* 상단 로고 스타일 (HOOHOO 느낌의 레드) */
        .logo-text {
            color: #E50914 !important;
            font-size: 1.8rem;
            font-weight: 900;
            letter-spacing: 2px;
            margin-bottom: 20px;
        }
        /* VIP 상단 바 */
        .top-bar {
            background-color: #1c1c1c;
            padding: 10px 20px;
            border-radius: 5px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            font-size: 0.9rem;
            color: #ccc;
        }
        /* 스트림릿 기본 버튼 스타일 덮어쓰기 (사이드바 메뉴용) */
        .stButton > button {
            background-color: transparent !important;
            color: #b3b3b3 !important;
            border: none !important;
            text-align: left !important;
            justify-content: flex-start !important;
            font-weight: bold;
        }
        .stButton > button:hover {
            color: #ffffff !important;
            background-color: #333333 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def render_sidebar():
    # 2. 좌측 사이드바 메뉴 렌더링
    with st.sidebar:
        st.markdown("<div class='logo-text'>≡ NEWS CASINO</div>", unsafe_allow_html=True)
        st.write("---")
        
        # 메뉴 버튼들 (클릭 시 페이지 이동)
        if st.button("🏠 홈", use_container_width=True): change_page('main')
        if st.button("🏆 실시간 랭킹", use_container_width=True): change_page('ranking')
        if st.button("🏦 내 금고 (은행)", use_container_width=True): change_page('bank')
        if st.button("🛒 코인 교환소", use_container_width=True): change_page('exchange')
        
        st.write("---")
        st.markdown("<p style='color: #666; font-size: 0.8rem;'>카테고리</p>", unsafe_allow_html=True)
        if st.button("🎮 게임 1", use_container_width=True): change_page('game_1')
        if st.button("🎮 게임 2", use_container_width=True): change_page('game_2')
            
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
    # 1. 사이드바 호출
    render_sidebar()

    st_autorefresh(interval=600000, limit=None, key="auto_refresh")

    # (유저 정보 갱신 로직 생략 - 기존과 동일하게 유지)
    user = st.session_state.current_user_data
    if not user:
        change_page('login')
        return

    # 2. 상단 바 (검색창/로그인 버튼이 있던 자리에 VIP 정보 배치)
    st.markdown(
        f"""
        <div class="top-bar">
            <span>추천 콘텐츠 및 공지사항 안내 ></span>
            <span>🎰 [VIP] {user.get('아이디', '알 수 없음')} | 💰 {user.get('코인', 0)} COIN</span>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    st.markdown("### 최신 게임을 모두 감상해보세요")

    # 3. 썸네일 그리드용 이미지 리스트 (테스트용)
    img_urls = [
        "https://picsum.photos/id/10/400/225", # 가로 비율에 맞는 해상도(16:9)
        "https://picsum.photos/id/20/400/225",
        "https://picsum.photos/id/30/400/225",
        "https://picsum.photos/id/40/400/225",
        "https://picsum.photos/id/50/400/225",
        "https://picsum.photos/id/60/400/225",
    ]
    
    # 4. 바둑판(Grid) 레이아웃 적용: flex-wrap과 폭(width) 조절
    clicked_menu = clickable_images(
        img_urls,
        titles=["게임 1", "게임 2", "게임 3", "게임 4", "게임 5", "게임 6"],
        div_style={
            "display": "flex", 
            "flex-wrap": "wrap",       # 핵심: 창 크기에 맞춰 밑으로 자동 줄바꿈
            "gap": "10px",             # 이미지 사이 간격
            "justify-content": "flex-start",
            "padding-bottom": "30px"
        },
        img_style={
            "width": "30%",            # 핵심: 한 줄에 3개씩 배치되도록 너비 설정 (모바일 환경 고려 시 변경 가능)
            "min-width": "150px",      # 너무 작아지는 것 방지
            "object-fit": "cover",      
            "border-radius": "4px",    # 넷플릭스 스타일의 약간 둥근 모서리
            "cursor": "pointer",
            "transition": "transform 0.2s" # 마우스 오버 시 애니메이션 대비
        },
        key="main_menu_grid"
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
# 바뀐 스트리밍 테마 함수 호출
inject_streaming_theme()

# 메인 페이지가 아닐 때도 사이드바를 띄우고 싶다면 각 페이지 상단에 render_sidebar()를 추가해 주면 됩니다.

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
