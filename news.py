import streamlit as st
from newspaper import Article
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

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
# 2. 제공해주신 기사 전처리 함수들 (그대로 사용)
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
    text = re.sub(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '', text)
    text = re.sub(r'\[[^\]]*(제공|DB|재판매|캡처|사진)[^\]]*\]', '', text)
    text = re.sub(r'무단\s*전재[^\n]*', '', text)
    return remove_duplicate_and_ui_lines(text)

def bring_article(url: str):
    article_obj = Article(url, language='ko')
    article_obj.download()
    article_obj.parse()
    domain = urlparse(url).netloc
    title = get_clean_title(article_obj, domain)
    clean_article = clean_common_text(article_obj.text) # 간소화를 위해 공통 클리너만 적용
    return title, clean_article
    
def summary(article):
    return article # 아직 구현 전

def similarity_check(summary, title):
    inputs = tokenizer(summary, title, padding=True, truncation=True, return_tensors="pt", max_length=512)
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits.squeeze(-1)
        score = torch.sigmoid(logits).item()
    return round(score, 4)


# ==========================================
# 3. Streamlit 앱 로직 및 UI 구성
# ==========================================

# 가상의 데이터베이스 역할 (실제 서비스시 SQLite 등 DB 연동 필요)
if 'users_db' not in st.session_state:
    st.session_state.users_db = {} 

# 세션 상태 초기화 (페이지 라우팅 및 현재 로그인 정보)
if 'page' not in st.session_state:
    st.session_state.page = 'login'
if 'current_user' not in st.session_state:
    st.session_state.current_user = None

def change_page(page_name):
    """페이지 이동 함수"""
    st.session_state.page = page_name
    st.rerun()

def show_login_page():
    st.title("Title") # 로그인 페이지 제목
    st.markdown("subtext") # 부제목

    student_id = st.text_input("학번을 입력하세요 (숫자 5자리)", max_chars=5)
    
    if student_id:
        if len(student_id) == 5 and student_id.isdigit():
            # 기존 유저인 경우
            if student_id in st.session_state.users_db:
                st.success(f"환영합니다! {st.session_state.users_db[student_id]['username']}님")
                if st.button("로그인"):
                    st.session_state.current_user = student_id
                    change_page('main')
            
            # 신규 유저 (회원가입 절차)
            else:
                st.info("최초 로그인입니다. 프로필을 설정해주세요.")
                username = st.text_input("아이디 (랭킹용, 미입력 시 '익명' 처리)")
                referral = st.text_input("가입 초대한 친구 학번 (선택사항)")
                
                if st.button("가입 및 로그인"):
                    final_username = username if username else f"익명_{student_id}"
                    
                    # 내 프로필 생성 (기본 5000 코인)
                    st.session_state.users_db[student_id] = {
                        "username": final_username,
                        "coins": 5000,
                        "streak": 0
                    }
                    
                    # 추천인 코인 지급 로직
                    if referral and referral in st.session_state.users_db:
                        st.session_state.users_db[referral]['coins'] += 1000 # 추천인 1000코인
                        st.toast(f"{referral}님에게 초대 보상이 지급되었습니다!")
                    
                    st.session_state.current_user = student_id
                    change_page('main')
        else:
            st.error("학번은 5자리 숫자로 입력해주세요.")

def show_main_page():
    user = st.session_state.users_db[st.session_state.current_user]
    
    # 좌측 상단 상태 표시창 (Sidebar 활용)
    with st.sidebar:
        st.subheader("내 정보")
        st.write(f"**아이디:** {user['username']}")
        st.write(f"💰 **뉴스코인:** {user['coins']} 개")
        st.write(f"🔥 **연승 기록:** {user['streak']} 승")
        
        st.divider()
        if st.button("로그아웃", use_container_width=True):
            st.session_state.current_user = None
            change_page('login')

    st.title("Title") # 메인 화면 제목
    st.markdown("subtext")
    
    st.divider()
    
    # 게임 및 기능 버튼들 (그리드 레이아웃)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🎮 게임 1", use_container_width=True): change_page('game_1')
        if st.button("🎮 게임 4", use_container_width=True): change_page('game_4')
    with col2:
        if st.button("🎮 게임 2", use_container_width=True): change_page('game_2')
        if st.button("🎮 게임 5", use_container_width=True): change_page('game_5')
    with col3:
        if st.button("🎮 게임 3", use_container_width=True): change_page('game_3')
    
    st.divider()
    
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🛒 교환소", type="primary", use_container_width=True): change_page('exchange')
    with col_b:
        if st.button("🏆 랭킹", type="primary", use_container_width=True): change_page('ranking')

# 개별 게임 및 기능 페이지들
def show_game_1():
    st.title("Title") # 게임 1 제목
    st.markdown("subtext")
    
    # NLP 기능 테스트 UI 예시
    url = st.text_input("뉴스 URL을 입력하세요")
    if st.button("뉴스 분석 시작"):
        with st.spinner("기사를 가져오고 분석하는 중..."):
            title, text = bring_article(url)
            summ = summary(text)
            score = similarity_check(summ, title)
            
            st.write(f"**기사 제목:** {title}")
            st.write(f"**유사도 점수:** {score}")
            
    if st.button("⬅️ 메인으로 돌아가기"):
        change_page('main')

def show_exchange():
    st.title("Title") # 교환소 제목
    st.markdown("subtext")
    st.write("상품 목록을 여기에 구현하세요.")
    if st.button("⬅️ 메인으로 돌아가기"): change_page('main')

def show_ranking():
    st.title("Title") # 랭킹 제목
    st.markdown("subtext")
    
    # 임시 DB에서 랭킹 정렬 및 표시
    sorted_users = sorted(st.session_state.users_db.values(), key=lambda x: x['coins'], reverse=True)
    for i, user_info in enumerate(sorted_users):
        st.write(f"{i+1}위: {user_info['username']} ({user_info['coins']} 코인)")
        
    if st.button("⬅️ 메인으로 돌아가기"): change_page('main')

# 템플릿용 더미 함수들
def show_game_2(): st.title("게임 2"); st.markdown("subtext"); st.button("돌아가기", on_click=lambda: change_page('main'))
def show_game_3(): st.title("게임 3"); st.markdown("subtext"); st.button("돌아가기", on_click=lambda: change_page('main'))
def show_game_4(): st.title("게임 4"); st.markdown("subtext"); st.button("돌아가기", on_click=lambda: change_page('main'))
def show_game_5(): st.title("게임 5"); st.markdown("subtext"); st.button("돌아가기", on_click=lambda: change_page('main'))


# ==========================================
# 4. 페이지 라우터 (앱 진입점)
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
