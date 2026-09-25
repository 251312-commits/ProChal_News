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
if 'login_step' not in st.session_state:
    st.session_state.login_step = 1  # 1: 학번 입력, 2_exist: 비밀번호 입력, 2_new: 회원가입
if 'temp_student_id' not in st.session_state:
    st.session_state.temp_student_id = None
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
    if st.session_state.get('page') == 'login':
        # 🔵 [로그인 전용] 밝은 회색 배경 & 전문적인 블루 테마
        st.markdown(
            """
            <style>
            /* 1. 로그인 페이지: 상단 여백 최적화 및 밝은 회색 배경 */
            .block-container {
                padding-top: 2rem !important;
            }
            .stApp {
                background-color: #f4f6f9 !important;
                background-image: none !important;
                color: #1e293b !important;
            }

            /* 2. 카드 형태 */
            [data-testid="stVerticalBlockBorderWrapper"] {
                background: #ffffff !important;
                border-radius: 18px !important;
                padding: 25px 20px !important;
                border: 1px solid #e2e8f0 !important;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04) !important;
            }

            /* 3. 타이틀 및 헤더 */
            h1, h2, h3 {
                color: #1e3a8a !important;
                text-shadow: none !important;
                text-align: center !important;
                font-weight: 800 !important;
            }

            /* 4. 아이콘 원형 */
            .user-icon-circle {
                width: 75px;
                height: 75px;
                background: #eff6ff;
                border: 2px solid #3b82f6;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 15px auto;
                font-size: 36px;
                color: #2563eb;
            }

            /* 5. 입력창 스타일 */
            .stTextInput > div > div > input {
                background-color: #f8fafc !important;
                color: #0f172a !important;
                font-weight: 600 !important;
                border: 1.5px solid #cbd5e1 !important;
                border-radius: 10px !important;
                height: 48px !important;
                text-align: center !important;
            }
            .stTextInput > div > div > input:focus {
                border-color: #2563eb !important;
                box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2) !important;
                background-color: #ffffff !important;
            }
            .stTextInput label {
                color: #334155 !important;
                font-weight: 600 !important;
            }

            /* 6. 버튼 스타일 */
            .stButton > button {
                background: #2563eb !important;
                color: #ffffff !important;
                font-weight: 700 !important;
                font-size: 1rem !important;
                border-radius: 10px !important;
                height: 48px !important;
                border: none !important;
                box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.25) !important;
            }

            /* 7. 주의사항 안내 박스 */
            .warning-note {
                background-color: #fef2f2;
                border-left: 4px solid #ef4444;
                color: #991b1b;
                padding: 12px;
                border-radius: 8px;
                font-size: 0.85rem;
                text-align: left;
                margin-top: 15px;
                margin-bottom: 15px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
    else:
        # ⬛ [메인 화면 전용] 상단 여백 축소 + 기존 블랙 카지노 테마
        st.markdown(
            """
            <style>
            /* 🚨 핵심: 메인 화면 상단 공백/여백 대폭 제거 */
            .block-container {
                padding-top: 1.2rem !important;
                padding-bottom: 1rem !important;
            }
            header[data-testid="stHeader"] {
                background-color: transparent !important;
            }

            .stApp {
                background-color: #05000a !important; 
                background-image: none !important; 
                color: #ffffff;
            }
            .neon-promo-banner {
                display: flex;
                flex-direction: row;
                background-color: #110022;
                border: 2px solid #8A2BE2;
                box-shadow: 0 0 15px #8A2BE2, inset 0 0 10px #8A2BE2;
                margin-top: 5px;
                margin-bottom: 25px;
                padding: 10px;
                border-radius: 5px;
                align-items: stretch;
            }
            .neon-left-box {
                flex: 1.2;
                box-shadow: 0 0 15px rgba(255, 0, 255, 0.5), inset 0 0 10px rgba(255, 0, 255, 0.3);
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                padding: 10px;
                background: rgba(255, 0, 255, 0.05);
                border-radius: 5px;
            }
            .neon-numbers {
                color: #FFFFFF;
                font-size: 1.8rem;
                font-weight: 900;
                text-shadow: 2px 2px 0px #FF00FF, 0 0 15px #FF00FF;
                text-align: center;
                line-height: 1.2;
            }
            .neon-numbers span { color: #FF00FF; }
            .neon-right-box {
                flex: 1;
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                padding-left: 15px;
                text-align: center;
            }
            .neon-logo-text {
                color: #ffffff;
                font-size: 3.5rem;
                font-weight: 900;
                text-shadow: 0 0 20px #8A2BE2, 0 0 40px #FF00FF;
                margin-bottom: -10px;
                letter-spacing: -3px;
            }
            .neon-sub-text {
                color: #FFD700;
                font-weight: 900;
                font-size: 1.1rem;
                text-shadow: 1px 1px 2px #000;
                margin-top: 5px;
            }
            .neon-sub-text-2 { color: #FF6347; font-weight: 900; font-size: 1rem; }
            h1, h2, h3 {
                color: #ffffff !important;
                text-shadow: 0 0 10px #8A2BE2, 0 0 20px #FF00FF !important;
                text-align: center;
            }
            .stButton > button {
                background: linear-gradient(to right, #4B0082, #8A2BE2) !important;
                color: #ffffff !important;
                font-weight: 900 !important;
                border: none !important;
                box-shadow: 0 0 10px #FF00FF;
            }
            .stTextInput > div > div > input {
                background-color: #000000 !important;
                color: #FF00FF !important;
                font-weight: bold;
                border: 2px solid #8A2BE2 !important;
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
    # 가운데 정렬 레이아웃
    _, col_main, _ = st.columns([1, 2.5, 1])

    with col_main:
        # 📦 입력 요소 전체를 보증하는 카드 컨테이너
        with st.container(border=True):
            # 로그인 카드 헤더
            st.markdown(
                """
                <div style="text-align: center; margin-bottom: 20px;">
                    <div class="user-icon-circle">👤</div>
                    <h2 style="margin-bottom: 6px; margin-top: 0;">Title</h2>
                    <p style="color: #64748b; font-size: 0.9rem; margin-bottom: 0;">학번을 입력하여 로그인해주세요.</p>
                </div>
                """,
                unsafe_allow_html=True
            )

            # ----------------------------------------------------
            # STEP 1: 학번 확인
            # ----------------------------------------------------
            if st.session_state.login_step == 1:
                student_id = st.text_input("학번", max_chars=5, placeholder="학번 5자리 입력", key="input_sid")
                
                if st.button("다음 (Next)", use_container_width=True):
                    clean_id = student_id.strip()
                    if clean_id.isdigit() and len(clean_id) == 5:
                        users_data = ws.get_all_records()
                        
                        user_info = None
                        for item in users_data:
                            raw_sheet_id = str(item.get('학번', ''))
                            sheet_id = raw_sheet_id.split('.')[0] if '.' in raw_sheet_id else raw_sheet_id.strip()
                            if sheet_id == clean_id:
                                user_info = item
                                break
                        
                        st.session_state.temp_student_id = clean_id
                        
                        if user_info:
                            st.session_state.temp_user_data = user_info
                            st.session_state.login_step = '2_exist'  # 기존 계정 -> 비밀번호
                        else:
                            st.session_state.login_step = '2_new'    # 신규 계정 -> 회원가입
                        st.rerun()
                    else:
                        st.error("학번은 5자리 숫자로 입력해주세요.")

            # ----------------------------------------------------
            # STEP 2-1: 기존 유저 비밀번호 입력
            # ----------------------------------------------------
            elif st.session_state.login_step == '2_exist':
                st.info(f"현재 {st.session_state.temp_student_id}으로 로그인 중입니다.")
                password = st.text_input("비밀번호", type="password", placeholder="비밀번호 입력", key="input_pw_login")
                
                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("이전", use_container_width=True):
                        st.session_state.login_step = 1
                        st.rerun()
                with col_b2:
                    if st.button("로그인", use_container_width=True):
                        saved_pw = str(st.session_state.temp_user_data.get('비밀번호', ''))
                        if password == saved_pw:
                            st.session_state.current_user = st.session_state.temp_student_id
                            st.session_state.current_user_data = st.session_state.temp_user_data
                            st.session_state.login_step = 1
                            change_page('main')
                        else:
                            st.error("비밀번호가 일치하지 않습니다.")

            # ----------------------------------------------------
            # STEP 2-2: 신규 유저 회원가입
            # ----------------------------------------------------
            elif st.session_state.login_step == '2_new':
                st.success(f"신규 가입 대상 학번: {st.session_state.temp_student_id}")
                
                username = st.text_input("아이디 (닉네임)", placeholder="사용할 닉네임", key="input_uname")
                password = st.text_input("비밀번호", type="password", placeholder="비밀번호 설정", key="input_pw1")
                password_confirm = st.text_input("비밀번호 확인", type="password", placeholder="비밀번호 재입력", key="input_pw2")
                referral = st.text_input("추천인 학번 (선택)", placeholder="초대한 친구 학번", key="input_ref")

                st.markdown(
                    """
                    <div class="warning-note">
                        ⚠️ <b>주의사항:</b> 설정한 비밀번호는 보안상 추후 변경이 어려우니 반드시 기억해 두시기 바랍니다!
                    </div>
                    """,
                    unsafe_allow_html=True
                )

                col_b1, col_b2 = st.columns(2)
                with col_b1:
                    if st.button("이전", use_container_width=True):
                        st.session_state.login_step = 1
                        st.rerun()
                with col_b2:
                    if st.button("가입완료", use_container_width=True):
                        if not username.strip():
                            st.error("닉네임을 입력해 주세요.")
                        elif not password:
                            st.error("비밀번호를 입력해 주세요.")
                        elif password != password_confirm:
                            st.error("비밀번호 확인이 일치하지 않습니다.")
                        else:
                            clean_id = st.session_state.temp_student_id
                            final_username = username.strip()
                            initial_coins = 5000
                            users_data = ws.get_all_records()

                            if referral.strip():
                                clean_ref = referral.strip()
                                ref_info = next((item for item in users_data if str(item.get('학번', '')).split('.')[0] == clean_ref), None)
                                if ref_info:
                                    row_idx = users_data.index(ref_info) + 2
                                    new_coins = int(ref_info.get('코인', 0)) + 3000
                                    ws.update_cell(row_idx, 3, new_coins)
                                    initial_coins += 1000
                                    st.toast("🎉 추천인 보상 코인이 지급되었습니다!")

                            new_row = [clean_id, final_username, initial_coins, 0, referral.strip(), password]
                            ws.append_row(new_row)

                            st.session_state.current_user = clean_id
                            st.session_state.current_user_data = {
                                "학번": clean_id,
                                "아이디": final_username,
                                "코인": initial_coins,
                                "연승": 0,
                                "비밀번호": password
                            }
                            st.session_state.login_step = 1
                            change_page('main')
        
        # 로그인 폼 네온 박스 종료
        st.markdown('</div>', unsafe_allow_html=True)
        
def show_main_page():
    st_autorefresh(interval=600000, limit=None, key="auto_refresh")

    users_data = ws.get_all_records()
    updated_info = next((item for item in users_data if str(item.get('학번', '')).strip().replace('.0', '') == st.session_state.current_user), None)
    
    if updated_info:
        st.session_state.current_user_data = updated_info

    user = st.session_state.current_user_data
    
    if not user:
        change_page('login')
        return
    
    # 🚨 이미지 스타일의 좌우 분할 네온 배너 HTML
    st.markdown(
        f"""
        <div style="color: white; font-weight: bold; font-size: 0.9rem; margin-bottom: -5px;">안전의대명사 뉴스에이전놀이터</div>
        <div style="color: #FF00FF; font-weight: bold; font-size: 0.8rem; margin-bottom: 5px;">실시간 뉴스 미니게임</div>
        
        <div class="neon-promo-banner">
            <div class="neon-left-box">
                <div class="neon-numbers">
                    VIP <span>{user.get('아이디', '알 수 없음')}</span><br>
                    보유 <span>{user.get('코인', 0)}</span> C<br>
                    🔥<span>{user.get('연승', 0)}</span> 연승중🔥
                </div>
            </div>
            <div class="neon-right-box">
                <div class="neon-logo-text">NEWS</div>
                <div style="background: #FF00FF; color: white; padding: 2px 10px; border-radius: 10px; font-weight: bold; margin-top: 5px;">유익하다!</div>
                <div class="neon-sub-text">친구 초대 시 3000코인 지급</div>
                <div class="neon-sub-text-2">당신도 가능하다 일획천금</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    img_urls = [
        "https://github.com/user-attachments/assets/331b7b2e-c4f5-4087-9f6b-9e672afb9568", 
        "https://github.com/user-attachments/assets/24bc9c42-e6c0-4f6f-a3a1-e1cce8fd66f3", 
        "https://github.com/user-attachments/assets/caf0511f-54f9-4d1e-8d6d-318e6886f2b4", 
        "https://github.com/user-attachments/assets/2893591d-30c2-485a-adcc-f8bd2ed94aa6", 
        "https://picsum.photos/id/50/800/110", 
        "https://picsum.photos/id/60/800/110", 
        "https://picsum.photos/id/70/800/110", 
        "https://picsum.photos/id/80/800/110"  
    ]
    
    clicked_menu = clickable_images(
        img_urls,
        titles=["🏦 은행", "🏆 랭킹", "게임 1", "게임 2", "게임 3", "게임 4", "게임 5", "🛒 교환소"],
        div_style={
            "display": "flex", 
            "flex-direction": "column", 
            "gap": "15px",
            "justify-content": "center",
            "padding-bottom": "30px",
            "background-color": "#05000a" 
        },
        img_style={
            "width": "100%",            
            "height": "110px",          
            "object-fit": "cover",      
            "border-radius": "5px", 
            "border": "2px solid #8A2BE2", 
            "box-shadow": "0 0 10px rgba(138, 43, 226, 0.8)",
            "cursor": "pointer"
        },
        key="main_menu_banners"
    )

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
