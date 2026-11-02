import streamlit as st
import base64
import streamlit.components.v1 as components
from modules.news_ai import bring_article, pick_3_lowest_count_news
from modules.db_handler import init_news_sheet
from modules.ui_components import change_page

ws_news = init_news_sheet()

# 정의된 함수: load_local_image_as_base64, get_game_news_selection, check_user_coins_or_pop_bank(min_required=1000), render_betting_ui

@st.cache_data
def load_local_image_as_base64(file_path: str) -> str:
    with open(file_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()
    return f"data:image/png;base64,{encoded}"

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


@st.dialog("🚨 잔액 부족!")
def _no_money_modal(min_required, current_coins):
    """코인 부족 시 뜨는 네온 스타일 모달 팝업"""
    st.markdown(
        f"""
        <style>
        .bank-popup-container {{
            text-align: center;
            padding: 10px 5px;
        }}
        .bank-popup-icon {{
            font-size: 3.5rem;
            margin-bottom: 10px;
            animation: bankBounce 1.5s infinite ease-in-out;
        }}
        @keyframes bankBounce {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(-8px); }}
        }}
        .bank-popup-title {{
            color: #ff0055;
            font-size: 1.3rem;
            font-weight: 900;
            text-shadow: 0 0 10px rgba(255, 0, 85, 0.6);
            margin-bottom: 12px;
        }}
        .bank-popup-desc {{
            color: #e0e0e0;
            font-size: 0.95rem;
            line-height: 1.6;
            margin-bottom: 18px;
        }}
        .bank-popup-highlight {{
            color: #ffd700;
            font-weight: bold;
        }}
        </style>

        <div class="bank-popup-container">
            <div class="bank-popup-icon">🏦</div>
            <div class="bank-popup-title">탕진잼! 코인이 부족합니다</div>
            <div class="bank-popup-desc">
                게임 참여에 최소 <span class="bank-popup-highlight">{min_required:,} C</span>가 필요하지만<br>
                현재 보유 코인은 <span style="color:#ff9999; font-weight:bold;">{current_coins:,} C</span> 입니다.<br><br>
                💡 <b>은행</b>에 들러 대출이나 충전을 진행하시겠습니까?
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏛️ 은행으로 가기", use_container_width=True, type="primary"):
            change_page('bank')
            st.rerun()

    with col2:
        if st.button("⬅️ 메인으로", use_container_width=True):
            change_page('main')
            st.rerun()


def check_user_coins_or_pop_bank(min_required=1000):
    """
    유저의 코인을 검사하고, 부족하면 은행 유도 팝업을 띄운 뒤 False를 반환합니다.
    코인이 충분하면 True를 반환합니다.
    
    사용 예시:
    if not check_user_coins_or_pop_bank(1000):
        return
    """
    current_coins = int(st.session_state.current_user_data.get('코인', 0)) if st.session_state.get('current_user_data') else 0

    if current_coins < min_required:
        _no_money_modal(min_required, current_coins)
        return False
    return True

def _adjust_bet_amount(step, min_val, max_val):
    """슬라이더 및 버튼 튀김 현상 방지용 콜백 함수"""
    current_val = st.session_state.get("bet_slider_val", min_val)
    st.session_state["bet_slider_val"] = max(min_val, min(max_val, current_val + step))


def render_betting_ui(current_coins, users_data=None, current_sid="", min_bet=100, bg_image_url=None):
    """
    공통 카지노 테마 베팅 UI 컴포넌트
    
    :param current_coins: 유저 보유 코인 (int)
    :param users_data: 랭킹 시뮬레이션용 유저 리스트 (list)
    :param current_sid: 현재 유저 학번/ID (str)
    :param min_bet: 최소 베팅 금액 (기본값 100)
    :param bg_image_url: (선택) 배경 이미지 URL 또는 이미지 경로 (str)
    :return: 베팅 확정 시 베팅 금액(int) 반환, 확정 전에는 None 반환
    """
    max_bet = max(min_bet, current_coins)

    # 슬라이더 세션 상태 초기화 및 범위 보정
    if "bet_slider_val" not in st.session_state:
        st.session_state["bet_slider_val"] = min(500, max_bet)
    else:
        st.session_state["bet_slider_val"] = max(min_bet, min(max_bet, st.session_state["bet_slider_val"]))

    # 배경 이미지 적용 처리 (URL 지정 시 은은한 어둠 overlay와 함께 적용)
    if bg_image_url:
        bg_style = f"background: linear-gradient(rgba(18, 2, 36, 0.75), rgba(6, 0, 13, 0.9)), url('{bg_image_url}'); background-size: cover; background-position: center;"
    else:
        bg_style = "background: radial-gradient(circle at 50% 20%, #2e0854 0%, #120224 55%, #06000d 100%);"

    # UI 스타일링 CSS
    st.markdown(
        f"""
        <style>
        .casino-app-frame {{
            {bg_style}
            border-radius: 28px;
            padding: 20px 16px;
            color: #ffffff;
            box-shadow: 0 0 35px rgba(138, 43, 226, 0.4);
            margin-bottom: 16px;
            border: 1.5px solid rgba(168, 85, 247, 0.4);
        }}
        .top-nav-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }}
        .coin-pill {{
            background: rgba(15, 5, 30, 0.7);
            border: 1.5px solid rgba(255, 215, 0, 0.6);
            border-radius: 20px;
            padding: 4px 12px;
            font-weight: 900;
            font-size: 0.95rem;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 6px;
            box-shadow: 0 0 10px rgba(255, 215, 0, 0.2);
        }}
        .bet-tag {{
            color: #c084fc;
            font-size: 0.75rem;
            letter-spacing: 3px;
            text-align: center;
            font-weight: 900;
            margin-top: 4px;
        }}
        .main-title {{
            text-align: center;
            font-size: 1.65rem;
            font-weight: 900;
            color: #ffffff;
            margin: 4px 0 2px 0;
            text-shadow: 0 0 15px rgba(255, 255, 255, 0.6);
        }}
        .sub-title {{
            text-align: center;
            font-size: 0.85rem;
            color: #b39ddb;
            margin-bottom: 15px;
        }}
        .stage-wrapper {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            margin: 15px 0 20px 0;
            position: relative;
        }}
        .news-card-3d {{
            width: 210px;
            height: 115px;
            background: linear-gradient(135deg, rgba(168, 85, 247, 0.35) 0%, rgba(88, 28, 135, 0.5) 100%);
            border: 2px solid #c084fc;
            border-radius: 18px;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 0 25px rgba(168, 85, 247, 0.5), inset 0 0 15px rgba(255, 255, 255, 0.2);
            backdrop-filter: blur(8px);
            transform: perspective(500px) rotateX(15deg);
            margin-bottom: -25px;
            z-index: 2;
        }}
        .question-mark {{
            font-size: 3rem;
            font-weight: 900;
            color: #f5d0fe;
            text-shadow: 0 0 20px #e879f9;
        }}
        .pedestal-3d {{
            width: 190px;
            height: 65px;
            background: radial-gradient(ellipse at top, #7e22ce 0%, #3b0764 70%, #1e0338 100%);
            border-radius: 50%;
            border: 3px solid #a855f7;
            box-shadow: 0 10px 30px rgba(0,0,0,0.9), 0 0 20px rgba(168, 85, 247, 0.6);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1;
        }}
        .bet-amount-title {{
            text-align: center;
            font-size: 1.8rem;
            font-weight: 900;
            color: #ffffff;
            margin-bottom: 6px;
            text-shadow: 0 0 10px rgba(255, 255, 255, 0.8);
        }}
        .stat-card-item {{
            background: rgba(22, 8, 44, 0.75);
            border: 1.5px solid #7e22ce;
            border-radius: 18px;
            padding: 12px 14px;
            min-height: 95px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            box-shadow: inset 0 0 12px rgba(168, 85, 247, 0.15);
        }}
        .stat-card-title {{
            font-size: 0.75rem;
            color: #c084fc;
            font-weight: 700;
        }}
        .stat-card-value {{
            font-size: 1.45rem;
            font-weight: 900;
            color: #ffffff;
        }}
        .multiplier-tag {{
            background: rgba(168, 85, 247, 0.25);
            border: 1px solid #c084fc;
            border-radius: 10px;
            padding: 2px 8px;
            font-size: 0.7rem;
            color: #e9d5ff;
            width: fit-content;
        }}
        .rank-up-badge-green {{
            color: #4ade80;
            font-weight: 900;
            font-size: 0.88rem;
            float: right;
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

    # 1. 메인 헤더 & 무대 비주얼
    st.markdown(
        f"""
        <div class="casino-app-frame">
            <div class="top-nav-bar">
                <span style="font-size: 1.2rem; cursor: pointer;">❮</span>
                <div class="coin-pill">
                    <span style="color:#ffd700;">🪙</span>
                    <span>{current_coins:,}</span>
                    <span style="color:#a855f7; margin-left:2px;">+</span>
                </div>
            </div>
            <div class="bet-tag">👑 BET</div>
            <div class="main-title">얼마를 걸까요?</div>
            <div class="sub-title">베팅하면 뉴스가 공개됩니다</div>
            
            <div class="stage-wrapper">
                <div class="news-card-3d">
                    <div class="question-mark">?</div>
                </div>
                <div class="pedestal-3d">
                    <div style="font-size: 2.2rem; filter: drop-shadow(0 0 10px #ffd700);">🪙🪙🪙</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # 2. 베팅 금액 표시
    bet_val = st.session_state["bet_slider_val"]
    st.markdown(f'<div class="bet-amount-title">🪙 {bet_val:,}</div>', unsafe_allow_html=True)

    # 3. 매끄러운 슬라이더 & (- / +) 콜백 버튼
    col_m, col_s, col_p = st.columns([1, 4, 1])
    with col_m:
        st.button("➖", use_container_width=True, key="btn_bet_minus", 
                  on_click=_adjust_bet_amount, args=(-50, min_bet, max_bet))

    with col_s:
        st.slider(
            "베팅 금액 선택",
            min_value=min_bet,
            max_value=max_bet,
            step=50,
            key="bet_slider_val",
            label_visibility="collapsed"
        )

    with col_p:
        st.button("➕", use_container_width=True, key="btn_bet_plus", 
                  on_click=_adjust_bet_amount, args=(50, min_bet, max_bet))

    st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

    # 4. 실시간 예상 당첨액 및 랭킹 산출
    expected_payout = bet_val * 2
    simulated_total_coins = current_coins + expected_payout

    rank_climb = 0
    curr_rank = 1
    sim_rank = 1

    if users_data:
        processed_users = []
        for u in users_data:
            try:
                c_val = int(u.get('코인', 0))
            except Exception:
                c_val = 0
            processed_users.append({
                'id': str(u.get('학번', '')).strip().replace('.0', ''),
                'nickname': str(u.get('아이디', '익명')).strip(),
                'coins': c_val
            })

        curr_sorted = sorted(processed_users, key=lambda x: x['coins'], reverse=True)
        curr_rank = next((i + 1 for i, u in enumerate(curr_sorted) if u['id'] == current_sid), len(curr_sorted) + 1)

        sim_list = []
        for u in processed_users:
            is_me = (u['id'] == current_sid)
            sim_list.append({
                'coins': simulated_total_coins if is_me else u['coins'],
                'is_me': is_me
            })
        sim_sorted = sorted(sim_list, key=lambda x: x['coins'], reverse=True)
        sim_rank = next((i + 1 for i, u in enumerate(sim_sorted) if u['is_me']), curr_rank)
        rank_climb = max(0, curr_rank - sim_rank)

    # 5. 통계 카드 출력
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown(
            f"""
            <div class="stat-card-item">
                <div class="stat-card-title">예상 당첨액 ⓘ</div>
                <div class="stat-card-value" style="color:#facc15;">+ {expected_payout:,}</div>
                <div class="multiplier-tag">배율 2.0x</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    with col_c2:
        rank_up_str = f"▲ {rank_climb}" if rank_climb > 0 else "-"
        st.markdown(
            f"""
            <div class="stat-card-item">
                <div class="stat-card-title">예상 랭킹 변동 ⓘ <span class="rank-up-badge-green">{rank_up_str}</span></div>
                <div class="stat-card-value" style="font-size:1.15rem; margin-top:4px;">
                    {curr_rank}위 ➔ <span style="color:#c084fc;">{sim_rank}위</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("<div style='margin-bottom: 16px;'></div>", unsafe_allow_html=True)

    # 6. 베팅 확정 버튼 클릭 시 확정된 금액 반환
    if st.button(f"⚡ {bet_val:,} 베팅하기", use_container_width=True, type="primary"):
        return bet_val

    return None
