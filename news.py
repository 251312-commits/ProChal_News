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
            background-color: #05000a !important; 
            background-image: none !important; 
            color: #ffffff;
        }

        /* 2. 사설 배너 스타일 컨테이너 (메인 페이지용) */
        .neon-promo-banner {
            display: flex;
            flex-direction: row;
            background-color: #110022;
            border: 2px solid #8A2BE2;
            box-shadow: 0 0 15px #8A2BE2, inset 0 0 10px #8A2BE2;
            margin-top: 10px;
            margin-bottom: 30px;
            padding: 10px;
            border-radius: 5px;
            align-items: stretch;
        }

        /* 3. 배너 왼쪽 (점선 제거, 은은한 네온 효과만 유지) */
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
        .neon-numbers span {
            color: #FF00FF;
        }

        /* 4. 배너 오른쪽 (로고 및 VIP 텍스트) */
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
            color: #ffffff; /* 흰색으로 변경 */
            font-size: 3.5rem;
            font-weight: 900;
            text-shadow: 0 0 20px #8A2BE2, 0 0 40px #FF00FF; /* 보라/핑크 후광 유지 */
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
        .neon-sub-text-2 {
            color: #FF6347;
            font-weight: 900;
            font-size: 1rem;
        }

        /* 5. 로그인 페이지 전용 네온 폼 박스 (점선 제거) */
        .neon-login-box {
            background-color: #0d001a;
            box-shadow: 0 0 20px rgba(138, 43, 226, 0.5), inset 0 0 15px rgba(255, 0, 255, 0.3);
            padding: 30px;
            border-radius: 10px;
            margin-top: 20px;
        }
        .login-warning {
            color: #FF00FF;
            font-weight: 900;
            font-size: 1.2rem;
            text-align: center;
            text-shadow: 0 0 10px #FF00FF;
            margin-bottom: 20px;
        }

        /* 기타 스트림릿 UI 덮어쓰기 */
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
    # 상단 텍스트를 배팅 사이트 홍보물 스타일로 화려하게 변경
    st.markdown(
        """
        <div style="text-align: center; margin-bottom: 30px;">
            <div style="color: white; font-weight: 900; font-size: 1.3rem; margin-bottom: -10px; text-shadow: 0 0 5px #fff;">★ 업계 1위 메이저 안전공원 ★</div>
            <div class="neon-logo-text" style="font-size: 4rem;">NEWS PLAY</div>
            <div style="color: #FF00FF; font-weight: bold; font-size: 1.1rem; margin-top: 15px; text-shadow: 0 0 10px #FF00FF;">
                가입즉시 5,000C 지급 | 무한 매충 | 먹튀 이력 절대 ZERO
            </div>
        </div>
        """, unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # 로그인 폼을 감싸는 네온 점선 박스 시작
        st.markdown('<div class="neon-login-box">', unsafe_allow_html=True)
        st.markdown('<div class="login-warning">⚠️ 가입코드 1111 / 학번으로 즉시 안전입장 ⚠️</div>', unsafe_allow_html=True)
        
        student_id = st.text_input("고유 식별번호 (학번 5자리)", max_chars=5, placeholder="입력 후 반드시 Enter를 눌러주세요")
        
        if student_id:
            clean_id = student_id.strip()
            
            if clean_id.isdigit():
                users_data = ws.get_all_records() 
                
                user_info = None
                for item in users_data:
                    raw_sheet_id = str(item.get('학번', ''))
                    
                    if '.' in raw_sheet_id:
                        sheet_id = raw_sheet_id.split('.')[0]
                    else:
                        sheet_id = raw_sheet_id.strip()
                        
                    if sheet_id == clean_id:
                        user_info = item
                        break
                
                if user_info:
                    st.success(f"✔️ 안전 계좌 확인 완료: {user_info.get('아이디', '알 수 없음')}님 환영합니다.")
                    if st.button("🚀 초고속 안전 입장 🚀", use_container_width=True):
                        st.session_state.current_user = clean_id
                        st.session_state.current_user_data = user_info
                        change_page('main')
                else:
                    st.info("🚨 [신규 가입 안내] 닉네임을 설정하고 꽁머니를 받으세요!")
                    username = st.text_input("닉네임 (미입력 시 '익명' 처리)", placeholder="도박사_01")
                    referral = st.text_input("지인 추천 코드 (선택사항)")
                    
                    if st.button("💰 가입 및 꽁머니 수령 💰", use_container_width=True):
                        final_username = username if username else f"익명_{clean_id}"
                        initial_coins = 5000
                        
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
                                st.toast(f"🎉 지인 추천 이벤트 적용! 본인 +1000C, {clean_referral}님 +3000C 지급!")
                            else:
                                st.toast("해당 추천 코드가 존재하지 않습니다.")
                        
                        new_row = [clean_id, final_username, initial_coins, 0, referral.strip()]
                        ws.append_row(new_row)
                        
                        st.session_state.current_user = clean_id
                        st.session_state.current_user_data = {
                            "학번": clean_id, "아이디": final_username, "코인": initial_coins, "연승": 0
                        }
                        change_page('main')
            else:
                st.error("학번은 숫자로만 입력 가능합니다.")
        
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
        <div style="color: #FF00FF; font-weight: bold; font-size: 0.8rem; margin-bottom: 5px;">실시간 뉴스 / 라이브 게임 / 미니게임</div>
        
        <div class="neon-promo-banner">
            <div class="neon-left-box">
                <div class="neon-numbers">
                    VIP <span>{user.get('아이디', '알 수 없음')}</span> 입장<br>
                    보유 <span>{user.get('코인', 0)}</span> C<br>
                    현재 <span>{user.get('연승', 0)}</span> 연승중
                </div>
            </div>
            <div class="neon-right-box">
                <div class="neon-logo-text">NEWS</div>
                <div style="background: #FF00FF; color: white; padding: 2px 10px; border-radius: 10px; font-weight: bold; margin-top: 5px;">가입코드 1111</div>
                <div class="neon-sub-text">가입첫충 30% 무한매충 10%</div>
                <div class="neon-sub-text-2">뉴스 카지노 상한 5천만원</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    img_urls = [
        "https://picsum.photos/id/10/800/110", 
        "https://picsum.photos/id/20/800/110", 
        "https://picsum.photos/id/30/800/110", 
        "https://picsum.photos/id/40/800/110", 
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
