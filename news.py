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
    
    sheet_url = "https://docs.google.com/spreadsheets/d/1-Kx4qK9SOV3fXF9q9jIYGefPDPQl_gkZK6iHUabKwmE/edit?usp=drivesdk"
    doc = gc.open_by_url(sheet_url)
    worksheet = doc.worksheet("Users")
    return worksheet

ws = init_gspread()

# ==========================================
# 뉴스 전용 구글 시트 워크시트 연결
# ==========================================
@st.cache_resource
def init_news_sheet():
    doc = ws.spreadsheet
    try:
        return doc.worksheet("News")
    except:
        news_ws = doc.add_worksheet(title="News", rows="100", cols="3")
        news_ws.append_row(["URL", "Count", "Title"])
        return news_ws

ws_news = init_news_sheet()

# ==========================================
# 선택 횟수 기반 최저 뉴스 3개 무작위 추출 알고리즘
# ==========================================
def pick_3_lowest_count_news(news_list):
    if len(news_list) <= 3:
        return news_list

    sorted_counts = sorted(list(set(item['count'] for item in news_list)))
    
    selected = []
    for count_val in sorted_counts:
        tier_items = [item for item in news_list if item['count'] == count_val]
        needed = 3 - len(selected)
        
        if len(tier_items) <= needed:
            selected.extend(tier_items)
        else:
            selected.extend(random.sample(tier_items, needed))
            
        if len(selected) == 3:
            break
            
    return selected

# ==========================================
# [공통 UI] 4초 네온 화려한 슬롯머신
# ==========================================
def get_game_news_selection(game_id: str):
    news_key = f"selected_news_{game_id}"
    candidates_key = f"candidates_{game_id}"
    read_done_key = f"read_done_{game_id}"

    if st.session_state.get(read_done_key, False):
        chosen = st.session_state[news_key]
        return chosen['title'], chosen['text'], chosen['url']

    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap');

        [data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #ffffff !important;
            border: 3.5px solid #2d1842 !important;
            border-radius: 6px !important;
            box-shadow: 6px 6px 0px #2d1842 !important;
            padding: 0px 0px 14px 0px !important;
            margin-top: 10px !important;
            margin-bottom: 25px !important;
            overflow: hidden !important;
        }

        [data-testid="stVerticalBlockBorderWrapper"] > div {
            padding: 0px 14px 10px 14px !important;
        }

        .pixel-window-header {
            background: linear-gradient(90deg, #a382de 0%, #d8b4f8 100%);
            color: #2d1842;
            padding: 8px 12px;
            margin: 0 -14px 15px -14px !important;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 3.5px solid #2d1842;
            font-family: 'Press Start 2P', monospace;
            font-size: 10px;
            font-weight: bold;
        }
        .pixel-window-controls {
            display: flex;
            gap: 4px;
        }
        .pixel-control-btn {
            width: 16px;
            height: 16px;
            background: #ffffff;
            color: #2d1842;
            border: 2px solid #2d1842;
            font-size: 9px;
            font-weight: bold;
            display: flex;
            align-items: center;
            justify-content: center;
            line-height: 1;
        }

        .pixel-timer-box {
            background-color: #000000;
            border: 2.5px solid #00ffcc;
            box-shadow: 3px 3px 0px #2d1842;
            color: #00ffcc;
            padding: 8px 12px;
            font-family: 'Press Start 2P', monospace;
            font-size: 11px;
            text-align: center;
            margin-bottom: 12px;
            border-radius: 4px;
        }
        .pixel-article-title {
            color: #2d1842;
            font-size: 1.05rem;
            font-weight: 900;
            margin-bottom: 12px;
            line-height: 1.4;
        }
        .pixel-article-body {
            background-color: #fcfaff;
            border: 2.5px solid #2d1842;
            border-radius: 6px;
            padding: 16px;
            color: #1e1b2e;
            font-size: 0.93rem;
            line-height: 1.6;
            max-height: 280px;
            overflow-y: auto;
            margin-bottom: 15px;
            white-space: pre-line;
            box-shadow: inset 2px 2px 5px rgba(0,0,0,0.06);
        }

        iframe[title="streamlit.components.v1.component_html"] {
            display: none !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    if news_key not in st.session_state or not st.session_state[news_key]:
        st.markdown(
            """
            <style>
            .slot-machine-banner {
                background: linear-gradient(135deg, #110620 0%, #32004a 50%, #0d001a 100%);
                border: 3px solid #00ffcc;
                border-radius: 6px;
                padding: 10px 12px;
                text-align: center;
                color: #fffb00;
                font-family: 'Press Start 2P', monospace;
                font-size: 10px;
                text-shadow: 0 0 8px #ff00ff, 0 0 12px #00ffff;
                box-shadow: 0 0 15px rgba(0, 255, 204, 0.6), inset 0 0 10px rgba(255, 0, 255, 0.4);
                margin-bottom: 16px;
                letter-spacing: 1px;
                animation: bannerGlow 1s ease-in-out infinite alternate;
            }
            @keyframes bannerGlow {
                0% { border-color: #00ffcc; box-shadow: 0 0 12px rgba(0,255,204,0.6); }
                100% { border-color: #ff00ff; box-shadow: 0 0 20px rgba(255,0,255,0.9); }
            }

            div[data-testid="stElementContainer"]:nth-child(2) > div[data-testid="stButton"] > button,
            div[data-testid="stElementContainer"]:nth-child(3) > div[data-testid="stButton"] > button,
            div[data-testid="stElementContainer"]:nth-child(4) > div[data-testid="stButton"] > button {
                position: relative !important;
                overflow: hidden !important;
                min-height: 72px !important;
                background-color: #ffffff !important;
                color: #2d1842 !important;
                border: 3.5px solid #2d1842 !important;
                border-radius: 6px !important;
                box-shadow: 4px 4px 0px #2d1842 !important;
                padding: 14px 16px !important;
                font-size: 0.95rem !important;
                font-weight: 800 !important;
                text-align: left !important;
                line-height: 1.4 !important;
                white-space: normal !important;
                word-break: keep-all !important;
                margin-bottom: 12px !important;
                transition: all 0.12s ease !important;
            }

            div[data-testid="stElementContainer"]:nth-child(2) > div[data-testid="stButton"] > button::before,
            div[data-testid="stElementContainer"]:nth-child(3) > div[data-testid="stButton"] > button::before,
            div[data-testid="stElementContainer"]:nth-child(4) > div[data-testid="stButton"] > button::before {
                content: "✨ 💎 ❓  SLOT SPINNING  ❓ 💎 ✨\\A🎰  🌟  💎  ❓  💎  🌟  🎰\\A✨ 💎 ❓  SLOT SPINNING  ❓ 💎 ✨";
                white-space: pre-wrap;
                position: absolute;
                top: 0; left: 0; right: 0; bottom: 0;
                display: flex;
                align-items: center;
                justify-content: center;
                font-family: 'Press Start 2P', monospace;
                font-size: 11px;
                color: #fffb00;
                background: linear-gradient(120deg, #2b004f, #61007d, #9c0062, #005f73);
                background-size: 300% 300%;
                text-shadow: 0 0 6px #00ffff, 0 0 10px #ff00ff;
                z-index: 5;
                pointer-events: none;
                line-height: 1.8;
                text-align: center;
                border-radius: 3px;
            }

            div[data-testid="stElementContainer"]:nth-child(2) > div[data-testid="stButton"] > button::before {
                animation: slotReelVertical 0.08s linear infinite, rainbowShift 1.2s ease infinite alternate, reelStop 0.01s linear 3.0s forwards;
            }
            div[data-testid="stElementContainer"]:nth-child(2) > div[data-testid="stButton"] > button p {
                animation: titlePopReveal 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) 3.0s both !important;
            }

            div[data-testid="stElementContainer"]:nth-child(3) > div[data-testid="stButton"] > button::before {
                animation: slotReelVertical 0.08s linear infinite, rainbowShift 1.2s ease infinite alternate, reelStop 0.01s linear 3.5s forwards;
            }
            div[data-testid="stElementContainer"]:nth-child(3) > div[data-testid="stButton"] > button p {
                animation: titlePopReveal 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) 3.5s both !important;
            }

            div[data-testid="stElementContainer"]:nth-child(4) > div[data-testid="stButton"] > button::before {
                animation: slotReelVertical 0.08s linear infinite, rainbowShift 1.2s ease infinite alternate, reelStop 0.01s linear 4.0s forwards;
            }
            div[data-testid="stElementContainer"]:nth-child(4) > div[data-testid="stButton"] > button p {
                animation: titlePopReveal 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) 4.0s both !important;
            }

            @keyframes slotReelVertical {
                0% { transform: translateY(-38px); filter: blur(3px); }
                50% { transform: translateY(0px); filter: blur(1px); }
                100% { transform: translateY(38px); filter: blur(3px); }
            }
            @keyframes rainbowShift {
                0% { background-position: 0% 50%; }
                100% { background-position: 100% 50%; }
            }
            @keyframes reelStop {
                to { opacity: 0; visibility: hidden; }
            }
            @keyframes titlePopReveal {
                0% { transform: scale(0.1); opacity: 0; }
                65% { transform: scale(1.25); opacity: 1; }
                85% { transform: scale(0.95); opacity: 1; }
                100% { transform: scale(1.0); opacity: 1; }
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        if candidates_key not in st.session_state:
            raw_records = ws_news.get_all_records()
            news_data = []

            with st.spinner("🎰 슬롯머신 기사 추천 중..."):
                for idx, row in enumerate(raw_records):
                    url = str(row.get('URL', '')).strip()
                    if not url:
                        continue
                    try:
                        count = int(row.get('Count', 0))
                    except:
                        count = 0
                    title = str(row.get('Title', '')).strip()
                    
                    if not title or title == "None":
                        try:
                            title, _ = bring_article(url)
                            ws_news.update_cell(idx + 2, 3, title)
                        except:
                            title = f"뉴스 기사 #{idx+1}"

                    news_data.append({
                        'row_idx': idx + 2,
                        'url': url,
                        'count': count,
                        'title': title
                    })

            if not news_data:
                st.warning("구글 시트 'News' 탭에 등록된 뉴스 URL이 없습니다.")
                return None, None, None

            st.session_state[candidates_key] = pick_3_lowest_count_news(news_data)

        candidates = st.session_state[candidates_key]

        components.html(
            """
            <script>
            (function() {
                try {
                    var AudioContext = window.AudioContext || window.webkitAudioContext;
                    if (!AudioContext) return;
                    var ctx = new AudioContext();
                    var now = ctx.currentTime;

                    for (var t = 0; t < 3.9; t += 0.07) {
                        var osc = ctx.createOscillator();
                        var gain = ctx.createGain();
                        osc.type = 'triangle';
                        osc.frequency.setValueAtTime(180 + Math.random() * 220, now + t);
                        gain.gain.setValueAtTime(0.04, now + t);
                        gain.gain.exponentialRampToValueAtTime(0.001, now + t + 0.05);
                        osc.connect(gain);
                        gain.connect(ctx.destination);
                        osc.start(now + t);
                        osc.stop(now + t + 0.05);
                    }

                    function playTakImpact(time, pitch) {
                        var osc = ctx.createOscillator();
                        var gain = ctx.createGain();
                        osc.type = 'square';
                        osc.frequency.setValueAtTime(pitch, time);
                        osc.frequency.exponentialRampToValueAtTime(70, time + 0.15);
                        gain.gain.setValueAtTime(0.25, time);
                        gain.gain.exponentialRampToValueAtTime(0.001, time + 0.15);
                        osc.connect(gain);
                        gain.connect(ctx.destination);
                        osc.start(time);
                        osc.stop(time + 0.15);
                    }

                    playTakImpact(now + 3.0, 500);
                    playTakImpact(now + 3.5, 680);
                    playTakImpact(now + 4.0, 880);

                    function playFanfareNote(freq, time, dur) {
                        var o = ctx.createOscillator();
                        var g = ctx.createGain();
                        o.type = 'sine';
                        o.frequency.setValueAtTime(freq, time);
                        g.gain.setValueAtTime(0.18, time);
                        g.gain.exponentialRampToValueAtTime(0.001, time + dur);
                        o.connect(g);
                        g.connect(ctx.destination);
                        o.start(time);
                        o.stop(time + dur);
                    }
                    playFanfareNote(523.25, now + 4.1, 0.12);
                    playFanfareNote(659.25, now + 4.22, 0.12);
                    playFanfareNote(783.99, now + 4.34, 0.12);
                    playFanfareNote(1046.50, now + 4.46, 0.35);
                } catch(e) {}
            })();
            </script>
            """,
            height=0,
            width=0
        )

        with st.container(border=True):
            st.markdown(
                """
                <div class="pixel-window-header">
                    <span>👾 SELECT_ARTICLE.EXE</span>
                    <div class="pixel-window-controls">
                        <div class="pixel-control-btn">-</div>
                        <div class="pixel-control-btn">□</div>
                        <div class="pixel-control-btn">×</div>
                    </div>
                </div>
                <div class="slot-machine-banner">
                    ✨🎰 4 SECONDS NEON SLOT: REVEALING ARTICLES! 🎰✨
                </div>
                """,
                unsafe_allow_html=True
            )

            for idx, item in enumerate(candidates):
                if st.button(f"📰 {item['title']}", key=f"btn_{game_id}_{idx}", use_container_width=True):
                    new_count = item['count'] + 1
                    ws_news.update_cell(item['row_idx'], 2, new_count)

                    with st.spinner("선택 기사 읽어오는 중..."):
                        try:
                            title, clean_text = bring_article(item['url'])
                        except:
                            title = item['title']
                            clean_text = "본문 내용을 가져오는 데 실패했습니다."

                    st.session_state[news_key] = {
                        'title': title,
                        'text': clean_text,
                        'url': item['url']
                    }
                    del st.session_state[candidates_key]
                    st.rerun()

        return None, None, None

    chosen = st.session_state[news_key]

    st.markdown(
        """
        <style>
        div[data-testid="stButton"] > button {
            background-color: #ffffff !important;
            color: #2d1842 !important;
            border: 2.5px solid #2d1842 !important;
            border-radius: 6px !important;
            box-shadow: 4px 4px 0px #2d1842 !important;
            padding: 12px 16px !important;
            font-size: 0.95rem !important;
            font-weight: 800 !important;
            margin-top: 10px !important;
            transition: all 0.12s ease !important;
        }
        div[data-testid="stButton"] > button:hover {
            background-color: #f3e8ff !important;
            color: #7e22ce !important;
            transform: translate(-2px, -2px) !important;
            box-shadow: 6px 6px 0px #2d1842 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    with st.container(border=True):
        st.markdown(
            """
            <div class="pixel-window-header">
                <span>👾 READ_ARTICLE.EXE</span>
                <div class="pixel-window-controls">
                    <div class="pixel-control-btn">-</div>
                    <div class="pixel-control-btn">□</div>
                    <div class="pixel-control-btn">×</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        col_info, col_timer = st.columns([2.5, 1.5])
        
        with col_info:
            st.markdown(f"<div class='pixel-article-title'>📰 {chosen['title']}</div>", unsafe_allow_html=True)
            
        with col_timer:
            st.markdown(
                """
                <div class="pixel-timer-box">
                    TIME: <span id="pixel_timer_num">30</span>S
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown(f"<div class='pixel-article-body'>{chosen['text']}</div>", unsafe_allow_html=True)

        next_clicked = st.button("▶ 다 읽었으면 다음", key=f"next_btn_{game_id}", use_container_width=True)

        components.html(
            f"""
            <script>
            (function() {{
                var sec = 30;
                var parentDoc = window.parent.document;
                
                var timerInterval = setInterval(function() {{
                    sec--;
                    var timerElem = parentDoc.getElementById("pixel_timer_num");
                    if (timerElem) {{
                        timerElem.innerText = sec > 0 ? sec : 0;
                    }}
                    if (sec <= 0) {{
                        clearInterval(timerInterval);
                        var btns = Array.from(parentDoc.querySelectorAll('button'));
                        var targetBtn = btns.find(b => b.innerText.includes('다 읽었으면 다음'));
                        if (targetBtn) {{
                            targetBtn.click();
                        }}
                    }}
                }}, 1000);
            }})();
            </script>
            """,
            height=0,
            width=0
        )

        if next_clicked:
            st.session_state[read_done_key] = True
            st.rerun()

    return None, None, None
    
# ==========================================
# 🎵 BGM 시스템 (Intro ➔ Loop 자동 전환 & 끊김 방지)
# ==========================================
def init_seamless_bgm(intro_url: str, loop_url: str):
    components.html(
        f"""
        <script>
        (function() {{
            var parentDoc = window.parent.document;
            
            // 이미 플레이어가 실행 중이라면 중복 생성하지 않음 (새로고침 시 끊김 방지)
            if (parentDoc.getElementById('global_bgm_player')) return;

            var bgmContainer = parentDoc.createElement('div');
            bgmContainer.id = 'global_bgm_player';
            bgmContainer.style.display = 'none';

            var introAudio = new Audio('{intro_url}');
            var loopAudio = new Audio('{loop_url}');
            
            introAudio.volume = 0.4;
            loopAudio.volume = 0.4;
            loopAudio.loop = true;

            // 인트로가 끝나면 루프 음원 연속 재생
            introAudio.addEventListener('ended', function() {{
                loopAudio.play().catch(function(e) {{
                    console.log("Loop playback failed:", e);
                }});
            }});

            // 브라우저 자동재생 정책(Autoplay Policy) 대응
            function startBgm() {{
                var promise = introAudio.play();
                if (promise !== undefined) {{
                    promise.catch(function(error) {{
                        // 첫 클릭/키 입력 시 BGM 자동 재생 시작
                        var enableAudio = function() {{
                            introAudio.play();
                            parentDoc.removeEventListener('click', enableAudio);
                            parentDoc.removeEventListener('keydown', enableAudio);
                        }};
                        parentDoc.addEventListener('click', enableAudio);
                        parentDoc.addEventListener('keydown', enableAudio);
                    }});
                }}
            }}

            startBgm();
            parentDoc.body.appendChild(bgmContainer);
        }})();
        </script>
        """,
        height=0,
        width=0
    )


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

def show_game_1():
    st.title("🎮 게임 1: 뉴스 예측 게임")
    title, article_text, url = get_game_news_selection("game_1")
    if not title:
        return

def show_game_2(): show_placeholder_page("게임 2")
def show_game_3(): show_placeholder_page("게임 3")
def show_game_4(): show_placeholder_page("게임 4")
def show_game_5(): show_placeholder_page("게임 5")
def show_exchange(): show_placeholder_page("🛒 교환소")
def show_bank(): show_placeholder_page("🏦 은행")
    
# GitHub Raw URL 형식 예시
INTRO_BGM_URL = "https://raw.githubusercontent.com/사용자계정/리포지토리명/main/intro.mp3"
LOOP_BGM_URL = "https://raw.githubusercontent.com/사용자계정/리포지토리명/main/loop.mp3"

# BGM 실행
init_seamless_bgm(INTRO_BGM_URL, LOOP_BGM_URL)

def inject_casino_theme():
    if st.session_state.get('page') == 'login':
        st.markdown(
            """
            <style>
            .block-container {
                padding-top: 2rem !important;
            }
            .stApp {
                background-color: #f4f6f9 !important;
                background-image: none !important;
                color: #1e293b !important;
            }
            [data-testid="stVerticalBlockBorderWrapper"] {
                background: #ffffff !important;
                border-radius: 18px !important;
                padding: 25px 20px !important;
                border: 1px solid #e2e8f0 !important;
                box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.08), 0 8px 10px -6px rgba(0, 0, 0, 0.04) !important;
            }
            h1, h2, h3 {
                color: #1e3a8a !important;
                text-shadow: none !important;
                text-align: center !important;
                font-weight: 800 !important;
            }
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
        st.markdown(
            """
            <style>
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

def show_login_page():
    _, col_main, _ = st.columns([1, 2.5, 1])

    with col_main:
        with st.container(border=True):
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
                            st.session_state.login_step = '2_exist'
                        else:
                            st.session_state.login_step = '2_new'
                        st.rerun()
                    else:
                        st.error("학번은 5자리 숫자로 입력해주세요.")

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
                <div class="neon-sub-text-2">당신도 가능하다 인생역전</div>
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

# ==========================================
# 🏆 네온 화려함 & 디폴트 애니메이션 랭킹 화면
# ==========================================
def show_ranking():
    users_data = ws.get_all_records()
    if not users_data:
        st.warning("등록된 유저 데이터가 없습니다.")
        if st.button("⬅️ 메인으로 돌아가기"): change_page('main')
        return

    processed_users = []
    for u in users_data:
        try:
            coin_val = int(u.get('코인', 0))
        except:
            coin_val = 0
        processed_users.append({
            'id': str(u.get('학번', '')).strip().replace('.0', ''),
            'nickname': str(u.get('아이디', '익명')).strip(),
            'coins': coin_val
        })
    
    sorted_users = sorted(processed_users, key=lambda x: x['coins'], reverse=True)
    for idx, u in enumerate(sorted_users):
        u['rank'] = idx + 1

    current_sid = st.session_state.get('current_user', '')
    my_info = next((u for u in sorted_users if u['id'] == current_sid), None)
    
    if not my_info and st.session_state.get('current_user_data'):
        my_nick = st.session_state.current_user_data.get('아이디', '')
        my_info = next((u for u in sorted_users if u['nickname'] == my_nick), None)

    my_rank = my_info['rank'] if my_info else 0
    my_nickname = my_info['nickname'] if my_info else (st.session_state.current_user_data.get('아이디', '나') if st.session_state.get('current_user_data') else '나')
    my_coins = my_info['coins'] if my_info else 0

    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Press+Start+2P&family=Gowun+Dodum&family=Noto+Sans+KR:wght@700;900&display=swap');

        .ranking-container, .ranking-container * {
            box-sizing: border-box !important;
        }

        .ranking-container {
            font-family: 'Gowun Dodum', 'Noto Sans KR', sans-serif;
            background: linear-gradient(135deg, #110022 0%, #1a0933 50%, #0d001a 100%);
            padding: 18px 14px;
            border-radius: 20px;
            color: #ffffff;
            border: 2px solid #00ffcc;
            animation: pulseGlow 3s infinite alternate;
            margin-bottom: 20px;
            width: 100%;
        }

        @keyframes pulseGlow {
            0% { border-color: #00ffcc; box-shadow: 0 0 15px rgba(0, 255, 204, 0.4); }
            50% { border-color: #ff00ff; box-shadow: 0 0 25px rgba(255, 0, 255, 0.6); }
            100% { border-color: #00ffcc; box-shadow: 0 0 15px rgba(0, 255, 204, 0.4); }
        }

        .ranking-header-title {
            text-align: center;
            font-family: 'Press Start 2P', monospace;
            font-size: 13px;
            color: #fffb00;
            text-shadow: 0 0 8px #ff00ff, 0 0 15px #00ffff;
            margin-bottom: 16px;
            letter-spacing: 1px;
        }

        .my-rank-card {
            background: linear-gradient(120deg, #1f113a 0%, #2e1052 50%, #1a0833 100%);
            border: 2px solid #ffd700;
            border-radius: 14px;
            padding: 12px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 22px;
            box-shadow: 0 0 15px rgba(255, 215, 0, 0.4), inset 0 0 8px rgba(255, 215, 0, 0.2);
            width: 100%;
        }
        .my-rank-badge {
            font-size: 1.1rem;
            font-weight: 900;
            color: #ffd700;
            text-shadow: 0 0 8px rgba(255, 215, 0, 0.8);
            margin-right: 8px;
            white-space: nowrap;
        }
        .my-nickname {
            font-size: 1rem;
            font-weight: 800;
            color: #ffffff;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        .top3-container {
            display: flex;
            justify-content: center;
            align-items: flex-end;
            gap: 8px;
            margin-bottom: 24px;
            width: 100%;
        }
        
        /* 공통 현수막 스타일 (클릭 호버 확대 제거) */
        .banner-box {
            flex: 1;
            min-width: 0;
            border-radius: 14px;
            padding: 12px 4px 14px 4px;
            text-align: center;
            color: #ffffff;
            position: relative;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
        }

        /* 디폴트 커졌다 작아지는 애니메이션 적용 */
        .banner-gold {
            background: linear-gradient(180deg, #ffd700 0%, #b8860b 60%, #5c4000 100%);
            border: 2.5px solid #fffb00;
            min-height: 135px;
            box-shadow: 0 0 20px rgba(255, 215, 0, 0.7);
            animation: goldPulse 2s ease-in-out infinite alternate;
        }
        .banner-silver {
            background: linear-gradient(180deg, #e0e0e0 0%, #757575 60%, #303030 100%);
            border: 2px solid #ffffff;
            min-height: 115px;
            box-shadow: 0 0 12px rgba(255, 255, 255, 0.4);
            animation: silverPulse 2.4s ease-in-out infinite alternate 0.3s;
        }
        .banner-bronze {
            background: linear-gradient(180deg, #cd7f32 0%, #8b4513 60%, #3e1e07 100%);
            border: 2px solid #ffaa66;
            min-height: 102px;
            box-shadow: 0 0 12px rgba(205, 127, 50, 0.5);
            animation: bronzePulse 2.8s ease-in-out infinite alternate 0.6s;
        }

        @keyframes goldPulse {
            0% { transform: translateY(-5px) scale(0.96); }
            100% { transform: translateY(-5px) scale(1.05); }
        }
        @keyframes silverPulse {
            0% { transform: scale(0.96); }
            100% { transform: scale(1.04); }
        }
        @keyframes bronzePulse {
            0% { transform: scale(0.96); }
            100% { transform: scale(1.04); }
        }

        .crown-icon {
            font-size: 1.8rem;
            line-height: 1;
            margin-bottom: 4px;
            filter: drop-shadow(0 0 6px rgba(255,255,255,0.8));
        }
        .crown-gold {
            animation: crownFloat 2s ease-in-out infinite;
            font-size: 2.2rem;
        }

        @keyframes crownFloat {
            0%, 100% { transform: translateY(0) rotate(0deg); }
            50% { transform: translateY(-6px) rotate(-6deg); }
        }

        .banner-nickname {
            font-size: 0.88rem;
            font-weight: 900;
            margin: 4px 0;
            text-shadow: 1px 1px 4px rgba(0,0,0,0.9);
            width: 100%;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .banner-coin-tag {
            background: rgba(0, 0, 0, 0.5);
            border-radius: 20px;
            padding: 3px 8px;
            font-size: 0.75rem;
            font-weight: 800;
            display: inline-block;
            border: 1px solid rgba(255,255,255,0.4);
            white-space: nowrap;
            color: #00ffcc;
            text-shadow: 0 0 5px #00ffcc;
        }

        .rank-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
            width: 100%;
        }
        .rank-item {
            background: rgba(255, 255, 255, 0.07);
            backdrop-filter: blur(5px);
            border-radius: 12px;
            padding: 10px 14px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border: 1px solid rgba(255, 255, 255, 0.15);
            color: #ffffff;
            width: 100%;
        }
        .rank-item.is-me {
            background: linear-gradient(90deg, rgba(255,0,255,0.25) 0%, rgba(138,43,226,0.3) 100%);
            border: 2px solid #ff00ff;
            box-shadow: 0 0 10px rgba(255, 0, 255, 0.5);
        }
        .rank-number {
            font-size: 1rem;
            font-weight: 900;
            color: #00ffcc;
            text-shadow: 0 0 6px #00ffcc;
            width: 30px;
            flex-shrink: 0;
        }
        .rank-nickname {
            font-size: 0.9rem;
            font-weight: 800;
            color: #ffffff;
            flex: 1;
            padding: 0 8px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .coin-box {
            background: rgba(0, 0, 0, 0.4);
            border: 1.5px solid #ffd700;
            border-radius: 20px;
            padding: 3px 9px;
            font-size: 0.8rem;
            font-weight: 900;
            color: #ffd700;
            display: flex;
            align-items: center;
            gap: 4px;
            flex-shrink: 0;
            white-space: nowrap;
            box-shadow: 0 0 8px rgba(255, 215, 0, 0.3);
        }
        .ellipsis-divider {
            text-align: center;
            color: #ff00ff;
            font-size: 1.1rem;
            font-weight: bold;
            margin: 4px 0;
            letter-spacing: 4px;
            text-shadow: 0 0 8px #ff00ff;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    rank_str = f"{my_rank}위" if my_rank > 0 else "순위 밖"
    
    top1 = next((u for u in sorted_users if u['rank'] == 1), None)
    top2 = next((u for u in sorted_users if u['rank'] == 2), None)
    top3 = next((u for u in sorted_users if u['rank'] == 3), None)

    top2_html = f'<div class="banner-box banner-silver"><div class="crown-icon">🥈</div><div class="banner-nickname">{top2["nickname"]}</div><div class="banner-coin-tag">🪙 {top2["coins"]:,}</div></div>' if top2 else '<div class="banner-box banner-silver" style="opacity:0.3;"><div class="crown-icon">🥈</div>-</div>'
    top1_html = f'<div class="banner-box banner-gold"><div class="crown-icon crown-gold">👑</div><div class="banner-nickname">{top1["nickname"]}</div><div class="banner-coin-tag">🪙 {top1["coins"]:,}</div></div>' if top1 else '<div class="banner-box banner-gold" style="opacity:0.3;"><div class="crown-icon crown-gold">👑</div>-</div>'
    top3_html = f'<div class="banner-box banner-bronze"><div class="crown-icon">🥉</div><div class="banner-nickname">{top3["nickname"]}</div><div class="banner-coin-tag">🪙 {top3["coins"]:,}</div></div>' if top3 else '<div class="banner-box banner-bronze" style="opacity:0.3;"><div class="crown-icon">🥉</div>-</div>'

    list_items_html = ""
    display_ranks = set()
    for r in [4, 5]:
        if r <= len(sorted_users):
            display_ranks.add(r)
    if my_rank > 0:
        for r in range(my_rank - 1, my_rank + 2):
            if 4 <= r <= len(sorted_users):
                display_ranks.add(r)

    sorted_ranks = sorted(list(display_ranks))
    if sorted_ranks:
        prev_r = 3
        for r in sorted_ranks:
            if r > prev_r + 1:
                list_items_html += '<div class="ellipsis-divider">• • •</div>'
            row = next((u for u in sorted_users if u['rank'] == r), None)
            if row:
                is_me = (my_info and row['id'] == my_info['id'])
                is_me_class = "is-me" if is_me else ""
                me_label = " (나)" if is_me else ""
                list_items_html += f'<div class="rank-item {is_me_class}"><div class="rank-number">{r}</div><div class="rank-nickname">{row["nickname"]}{me_label}</div><div class="coin-box">🪙 {row["coins"]:,}</div></div>'
            prev_r = r

    full_ranking_html = f'''
    <div class="ranking-container">
        <div class="ranking-header-title">🏆 HALL OF FAME 🏆</div>
        <div class="my-rank-card">
            <div style="display:flex; align-items:center; overflow:hidden;">
                <span class="my-rank-badge">{rank_str}</span>
                <span class="my-nickname">👤 {my_nickname} (나)</span>
            </div>
            <div class="coin-box">🪙 {my_coins:,} C</div>
        </div>
        <div class="top3-container">
            {top2_html}
            {top1_html}
            {top3_html}
        </div>
        {'<div class="rank-list">' + list_items_html + '</div>' if list_items_html else ''}
    </div>
    '''

    st.markdown(full_ranking_html, unsafe_allow_html=True)

    if st.button("⬅️ 메인으로 돌아가기", use_container_width=True):
        change_page('main')

# ==========================================
# 5. 페이지 라우터
# ==========================================
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