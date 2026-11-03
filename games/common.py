import streamlit as st
import base64
import streamlit.components.v1 as components
from modules.news_ai import bring_article, pick_3_lowest_count_news
from modules.db_handler import init_news_sheet
from modules.ui_components import change_page, load_local_image_as_base64

ws_news = init_news_sheet()

# 정의된 함수: get_game_news_selection, check_user_coins_or_pop_bank(min_required=1000), render_betting_ui

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

def _adjust_bet_amount(step, min_val, max_val):
    """슬라이더 및 버튼 반응속도 최적화용 콜백 함수"""
    current_val = st.session_state.get("bet_slider_val", min_val)
    st.session_state["bet_slider_val"] = max(min_val, min(max_val, current_val + step))


def render_betting_ui(current_coins, users_data=None, current_sid="", current_nickname="", min_bet=100, bg_image_path=None):
    """모바일 대응 프리미엄 네온 베팅 화면. 기존 게임/코인 로직은 유지한다."""
    if current_coins < min_bet:
        st.error(f"최소 베팅 금액 {min_bet:,} C에 필요한 코인이 부족합니다.")
        return None

    max_bet = max(min_bet, current_coins)
    if "bet_slider_val" not in st.session_state:
        st.session_state["bet_slider_val"] = max(min_bet, min(500, max_bet))
    else:
        st.session_state["bet_slider_val"] = max(min_bet, min(max_bet, st.session_state["bet_slider_val"]))
    bet_val = st.session_state["bet_slider_val"]

    # 배경 이미지가 제공된 경우 기존 게임의 배경을 함께 사용한다.
    bg_style = "radial-gradient(ellipse at 50% 9%, rgba(107, 28, 178, .55), transparent 55%), linear-gradient(180deg, #10051e, #080411 80%)"
    if bg_image_path:
        try:
            encoded_bg = load_local_image_as_base64(bg_image_path)
        except (OSError, ValueError):
            encoded_bg = None
        if encoded_bg:
            bg_style = f"linear-gradient(180deg, rgba(13, 3, 28, .80), rgba(8, 3, 18, .92)), url('{encoded_bg}')"

    st.markdown(
        """
        <style>
        /* 모든 규칙은 게임 1 베팅 화면에만 적용한다. */
        .st-key-casino_betting_shell {
            position: relative; isolation: isolate; overflow: hidden;
            max-width: 660px; margin: 0 auto 1.2rem;
            padding: clamp(12px, 3.2vw, 24px) !important;
            border-radius: 28px; border: 1px solid rgba(180, 78, 255, .42);
            box-shadow: 0 15px 60px rgba(4, 0, 10, .8), inset 0 0 55px rgba(89, 0, 158, .15);
            color: #fff;
        }
        .st-key-casino_betting_shell::before {
            content: ''; position: absolute; pointer-events: none;
            inset: 0; z-index: -1;
            background: radial-gradient(circle at 16% 26%, rgba(176, 63, 252, .17), transparent 12%),
                        radial-gradient(circle at 90% 14%, rgba(218, 111, 255, .15), transparent 14%),
                        radial-gradient(circle at 7% 75%, rgba(233, 136, 33, .14), transparent 12%);
        }
        .st-key-casino_betting_shell [data-testid="stVerticalBlock"] {gap: .55rem;}
        .st-key-casino_betting_shell [data-testid="stHorizontalBlock"] {align-items: center;}
        .st-key-casino_betting_shell button {font-family: inherit !important;}

        /* 상단 뒤로가기 / 잔액 / 충전 */
        .st-key-bet_nav_back button, .st-key-bet_nav_bank button {
            min-height: 42px !important; height: 42px !important;
            width: 42px !important; padding: 0 !important;
            border-radius: 50% !important; border: 1px solid rgba(176, 85, 249, .7) !important;
            background: rgba(25, 12, 40, .87) !important;
            box-shadow: inset 0 1px 5px rgba(255,255,255,.08), 0 0 12px rgba(144, 38, 221, .2) !important;
            color: #fff !important; font-size: 1.6rem !important;
        }
        .st-key-bet_nav_bank button {border-color: #ac34ff !important; color: #e9c7ff !important;}
        .cb-balance {
            display:flex; align-items:center; justify-content:flex-end; gap:9px;
            min-height:42px; font-size: clamp(1rem, 4.4vw, 1.4rem);
            font-weight:900; letter-spacing:.02em; white-space:nowrap;
            text-shadow:0 1px 4px #07010d;
        }
        .cb-gold-token, .cb-mini-token {
            display:inline-flex; align-items:center; justify-content:center;
            border-radius:50%; border:2px solid #ffd46c;
            background: radial-gradient(circle at 30% 25%, #ffeeb3 0%, #ffcf36 24%, #ee8f0c 65%, #ad5307 90%);
            color:#b46c11; font-weight:950;
            box-shadow:inset 0 0 0 3px rgba(255,241,155,.34), 0 2px 8px rgba(255,153,0,.6);
            text-shadow:0 1px 1px #ffdd73;
        }
        .cb-gold-token {width:36px; height:36px; font-size:22px;}
        .cb-mini-token {width:28px; height:28px; font-size:17px; vertical-align:middle;}

        /* 보라색 왕관 / 제목 / 카드 무대 */
        .cb-hero {position:relative; padding-top:14px; text-align:center;}
        .cb-insignia {position:relative; margin:0 auto 10px; width:150px; padding-top:11px;
            border-top:1px solid rgba(217, 146, 255, .8); border-radius:85px 85px 0 0;
            color:#ffc57d; text-shadow:0 0 12px rgba(246,126,255,.65);}
        .cb-insignia::after {content:''; position:absolute; height:1px; top:43px; left:-43px; right:-43px;
            background:linear-gradient(90deg, transparent, #a537f5, #ffbf74, #a537f5, transparent); opacity:.7;}
        .cb-crown {display:block; font-size:34px; line-height:1; filter:drop-shadow(0 0 9px #ae3cff);}
        .cb-bet-tag {display:block; font-family:Georgia,serif; font-weight:700; letter-spacing:7px; font-size:22px;}
        .cb-hero-title {font-size:clamp(1.65rem, 6.8vw, 2.5rem); font-weight:950;
            letter-spacing:-.045em; line-height:1.25; margin:3px 0 5px;
            color:#fbf6ff; text-shadow:0 0 15px rgba(176,90,248,.4);}
        .cb-hero-subtitle {font-size:clamp(.84rem, 3.3vw, 1.04rem); color:#c3b5d4; margin:0;}
        .cb-scene {position:relative; height:330px; max-width:570px; margin:8px auto 0; perspective:850px;}
        .cb-scene::before {content:''; position:absolute; inset:16% 4% 20%;
            border-radius:50%; background:radial-gradient(ellipse, rgba(176,59,255,.27), transparent 67%);
            filter:blur(18px);}
        .cb-card {position:absolute; left:6%; right:6%; top:14px; height:214px;
            background:linear-gradient(140deg, rgba(60,23,91,.93), #1c102c 46%, #270b43 100%);
            border:1.5px solid #bc55ff; border-radius:26px;
            box-shadow:0 0 25px rgba(169,50,255,.6), inset 0 0 40px rgba(145,53,231,.26);
            transform:perspective(800px) rotateX(8deg);}
        .cb-card-back-left {left:3%; right:11%; top:27px; transform:rotate(-7deg); opacity:.6;}
        .cb-card-back-right {left:11%; right:3%; top:26px; transform:rotate(7deg); opacity:.6;}
        .cb-card-front {z-index:2; overflow:hidden;
            background:linear-gradient(126deg, rgba(93,30,130,.82), rgba(24,11,42,.97) 54%,rgba(54,14,86,.87));}
        .cb-card-front::before {content:''; position:absolute; left:12%; right:12%; top:0;
            height:2px; background:linear-gradient(90deg,transparent,#ffcdca,#bf41ff,transparent);
            box-shadow:0 0 20px 7px rgba(209,53,255,.42);}
        .cb-news-paper {position:absolute; inset:28% 25%; opacity:.25; border-radius:8px;
            transform:skewX(-3deg); background:linear-gradient(#704683,#704683) 19% 25%/40% 8px no-repeat,
            repeating-linear-gradient(0deg,#7f5995 0 6px,transparent 6px 16px);
            border:10px solid rgba(114,78,145,.35);}
        .cb-question {position:absolute; inset:0; display:grid; place-items:center;
            color:#efc3ff; font-size:clamp(5rem,17vw,8rem); font-weight:950;
            text-shadow:0 0 12px #c066fb, 0 0 35px rgba(220,124,255,.86);}
        .cb-platform {position:absolute; z-index:3; bottom:1px; left:7%; right:7%; height:88px;
            border-radius:50% / 45%; border:3px solid rgba(182,66,255,.8);
            background:radial-gradient(ellipse at 50% 35%, #4b1a75 0%, #1b0b33 60%, #0c041b 100%);
            box-shadow:0 17px 4px #0c0613, 0 25px 30px #020106, 0 0 26px #982cff,
                       inset 0 5px 12px rgba(217,131,255,.4);}
        .cb-platform::before {content:'';position:absolute;inset:12px 5%; border-radius:50%;
            border:1px solid rgba(223,126,255,.6);}
        .cb-coins {position:absolute;z-index:4;left:50%;bottom:52px; width:270px;height:123px;
            transform:translateX(-50%);pointer-events:none;}
        .cb-stack {position:absolute;bottom:0;width:62px;border:1px solid #b85d0c;border-radius:5px 5px 8px 8px;
            background:repeating-linear-gradient(to bottom,#ffdb60 0px,#fff0a3 3px,#c9770b 5px,#a64c04 10px,#f6a927 13px);
            box-shadow:inset 5px 0 9px #ffdb75,inset -7px 0 9px #b65a07, 2px 5px 7px #1a0924;}
        .cb-stack::before {content:'';position:absolute;left:-1px;right:-1px;top:-11px;height:19px;
            border-radius:50%;background:radial-gradient(ellipse at 50% 45%,#fff4ad,#ffbf31 60%,#ba6307 90%);
            border:2px solid #f5c44e;box-shadow:0 2px 3px #854007;}
        .cb-stack-one {left:16px;height:37px;}.cb-stack-two {left:64px;height:80px;}
        .cb-stack-three {left:113px;height:55px;}.cb-stack-four {left:169px;height:78px;}
        .cb-stack-five {left:217px;width:40px;height:31px;}
        .cb-medal {position:absolute;z-index:5; left:50%; bottom:40px; transform:translateX(-50%);
            width:92px;height:92px;display:grid;place-items:center;
            border:5px solid #ffe1a0;border-radius:50%;font-size:49px;color:#dc7f0c;
            background:radial-gradient(circle at 33% 21%,#fff2a1,#ffbe1e 63%,#b96305);
            text-shadow:0 2px 1px rgba(255,251,187,.8);
            box-shadow:inset 0 0 0 5px rgba(222,135,16,.72),0 0 12px #ffc55c,0 7px 14px #15061f;}

        /* 금액 컨트롤러 */
        .st-key-casino_bet_controls {border:1px solid rgba(174,55,255,.65);
            border-radius:28px;padding:16px 15px 12px !important;
            background:linear-gradient(160deg,rgba(48,16,69,.96),rgba(19,8,37,.96));
            box-shadow:inset 0 3px 12px rgba(217,133,255,.16),0 0 20px rgba(126,17,203,.2);}
        .cb-amount {display:flex;align-items:center;justify-content:center;gap:12px;
            font-size:clamp(1.75rem,7.5vw,2.5rem);font-weight:950;line-height:1.25;
            letter-spacing:.005em;text-shadow:0 0 12px rgba(239,196,255,.3);}
        .cb-range-ends {display:flex;justify-content:space-between;color:#9c8aaf;
            padding:0 48px;font-size:.79rem;font-weight:700;}
        .st-key-casino_bet_controls .stSlider {margin:0 !important;}
        .st-key-casino_bet_controls [data-baseweb="slider"] [role="slider"] {
            background:#f5d7ff !important; border:3px solid #fff7ff !important;
            box-shadow:0 0 8px 3px #d553ff !important; width:29px !important;height:29px !important;}
        .st-key-bet_btn_minus button, .st-key-bet_btn_plus button {
            width:45px !important; height:45px !important; min-height:45px !important;
            padding:0 !important; border-radius:50% !important;
            background:#210c39 !important;border:1.5px solid #b829ff !important;
            box-shadow:0 0 15px rgba(169,40,255,.5),inset 0 0 10px rgba(132,38,223,.2) !important;
            color:#fff !important; font-size:1.45rem !important;font-weight:900 !important;}

        /* 예상 결과 */
        .cb-prediction {display:grid;grid-template-columns:1fr 1fr;gap:0;margin:9px 0 7px;
            border:1px solid #a82cec;border-radius:24px;overflow:hidden;
            background:linear-gradient(150deg, rgba(64,15,92,.92), rgba(20,7,38,.96));
            box-shadow:inset 0 0 25px rgba(137,31,228,.28),0 0 18px rgba(129,33,204,.3);}
        .cb-stat {position:relative;min-width:0;min-height:113px; padding:15px 12px 14px;}
        .cb-stat + .cb-stat {border-left:1px solid rgba(192,105,241,.28);}
        .cb-stat-label {font-size:clamp(.71rem,2.9vw,.86rem); color:#efdfef;font-weight:750;
            white-space:nowrap;letter-spacing:-.04em;}
        .cb-stat-number {font-size:clamp(1.34rem,6.4vw,2.2rem);font-weight:950;line-height:1.25;
            white-space:nowrap;letter-spacing:-.04em; margin-top:6px;}
        .cb-stat-number.is-gold {color:#ffcf52;text-shadow:0 0 14px rgba(255,188,40,.25);}
        .cb-stat-pill {display:inline-block;margin-top:4px;border:1px solid rgba(206,97,255,.65);
            color:#d69aff;background:#1d0a32;border-radius:14px;padding:2px 12px;font-size:.7rem;}
        .cb-stat-sub {font-size:clamp(.84rem,3vw,1.05rem);font-weight:900;white-space:nowrap;margin-top:7px;}
        .cb-stat-sub b {color:#c265ff;font-size:1.18em;}
        .cb-rank-delta {position:absolute;right:12px;top:15px;color:#37e9bd;font-weight:900;font-size:.8rem;}
        .cb-stat-art {font-size:1.05rem;filter:drop-shadow(0 0 7px #b843fd);margin-right:4px;}

        /* 베팅 확정 버튼 */
        .st-key-bet_confirm_cta button {
            min-height:79px !important;border-radius:999px !important;width:100% !important;
            background:linear-gradient(180deg,#bb42ff 0%,#7d12f4 43%,#4a0bdd 100%) !important;
            border:2px solid #e879ff !important; color:#fff !important;
            font-size:clamp(1.2rem,5.8vw,1.75rem) !important;font-weight:950 !important;
            box-shadow:inset 0 4px 10px rgba(255,255,255,.4),inset 0 -8px 18px rgba(54,4,144,.72),
                0 5px 22px rgba(211,57,255,.6) !important;
            text-shadow:0 1px 10px rgba(255,255,255,.4);}
        .st-key-bet_confirm_cta button:hover {filter:brightness(1.13);transform:translateY(-1px);}
        .cb-betting-note {text-align:center;color:#9c88ac;font-size:.7rem;margin:3px 0 0;}
        @media (max-width:480px) {
            .st-key-casino_betting_shell {padding:12px !important;border-radius:21px;}
            .st-key-casino_betting_shell [data-testid="stHorizontalBlock"] {gap:.3rem; flex-wrap:nowrap !important;}
            .st-key-casino_betting_shell [data-testid="column"] {min-width:0 !important; padding:0 !important;}
            .cb-hero {padding-top:4px;}
            .cb-scene {height:278px;}
            .cb-card {height:184px;top:11px;border-radius:20px;}
            .cb-card-back-left,.cb-card-back-right {top:22px;}
            .cb-platform {height:68px;bottom:2px;}
            .cb-coins {transform:translateX(-50%) scale(.78);transform-origin:bottom center;bottom:45px;}
            .cb-medal {transform:translateX(-50%) scale(.8);transform-origin:bottom center;bottom:31px;}
            .cb-stat {min-height:102px;padding:12px 9px;}
            .cb-rank-delta {top:11px;right:8px;}
            .cb-range-ends {padding:0 34px;}
            .st-key-casino_bet_controls {padding:13px 9px 9px !important;}
            .st-key-bet_btn_minus button,.st-key-bet_btn_plus button {width:38px !important;height:38px !important;min-height:38px !important;}
            .st-key-bet_confirm_cta button {min-height:64px !important;}
        }
        @media (prefers-reduced-motion: no-preference) {
            .cb-card-front {animation:cb-hover 4s ease-in-out infinite;}
            @keyframes cb-hover {0%,100% {translate:0 0;}50% {translate:0 -5px;}}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # 승리/정산 로직 자체는 건드리지 않고 기존 2.0배 예측 모델을 유지한다.
    expected_payout = bet_val * 2
    simulated_total_coins = current_coins + expected_payout
    curr_rank, sim_rank = 1, 1
    rank_climb = 0
    if users_data:
        clean_sid = str(current_sid).strip().replace('.0', '')
        clean_nick = str(current_nickname).strip()
        processed_users = []
        for u in users_data:
            try:
                coins = int(u.get('코인', 0))
            except (ValueError, TypeError):
                coins = 0
            u_id = str(u.get('학번', u.get('id', ''))).strip().replace('.0', '')
            u_nick = str(u.get('아이디', u.get('nickname', ''))).strip()
            is_me = (clean_sid and u_id == clean_sid) or (clean_nick and u_nick == clean_nick)
            processed_users.append({'coins': coins, 'is_me': bool(is_me)})
        current_order = sorted(processed_users, key=lambda u: u['coins'], reverse=True)
        curr_rank = next((i + 1 for i, u in enumerate(current_order) if u['is_me']), len(current_order) + 1)
        simulated = sorted([
            {'coins': simulated_total_coins if u['is_me'] else u['coins'], 'is_me': u['is_me']}
            for u in processed_users
        ], key=lambda u: u['coins'], reverse=True)
        sim_rank = next((i + 1 for i, u in enumerate(simulated) if u['is_me']), curr_rank)
        rank_climb = max(0, curr_rank - sim_rank)

    st.markdown(f"<style>.st-key-casino_betting_shell {{ background: {bg_style}; background-size:cover; background-position:center; }}</style>", unsafe_allow_html=True)
    with st.container(key="casino_betting_shell"):
        back_col, space_col, balance_col, bank_col = st.columns([.7, .9, 2.8, .75], gap="small")
        with back_col:
            if st.button("❮", key="bet_nav_back", help="메인 화면으로 돌아가기"):
                change_page("main")
        with balance_col:
            st.markdown(f'<div class="cb-balance"><span class="cb-gold-token">$</span>{current_coins:,}</div>', unsafe_allow_html=True)
        with bank_col:
            if st.button("+", key="bet_nav_bank", help="은행으로 이동"):
                change_page("bank")

        st.markdown(
            """
            <section class="cb-hero" aria-label="베팅 화면">
                <div class="cb-insignia"><span class="cb-crown">♛</span><span class="cb-bet-tag">BET</span></div>
                <div class="cb-hero-title">얼마를 걸까요?</div>
                <p class="cb-hero-subtitle">베팅하면 뉴스가 공개됩니다</p>
                <div class="cb-scene" aria-hidden="true">
                    <div class="cb-card cb-card-back-left"></div>
                    <div class="cb-card cb-card-back-right"></div>
                    <div class="cb-card cb-card-front"><div class="cb-news-paper"></div><div class="cb-question">?</div></div>
                    <div class="cb-platform"></div>
                    <div class="cb-coins"><div class="cb-stack cb-stack-one"></div><div class="cb-stack cb-stack-two"></div>
                    <div class="cb-stack cb-stack-three"></div><div class="cb-stack cb-stack-four"></div><div class="cb-stack cb-stack-five"></div></div>
                    <div class="cb-medal">♛</div>
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )

        with st.container(key="casino_bet_controls"):
            st.markdown(f'<div class="cb-amount"><span class="cb-gold-token">$</span>{bet_val:,}</div>', unsafe_allow_html=True)
            minus_col, range_col, plus_col = st.columns([1, 5, 1], gap="small")
            with minus_col:
                st.button("−", use_container_width=True, key="bet_btn_minus",
                          on_click=_adjust_bet_amount, args=(-50, min_bet, max_bet))
            with range_col:
                st.slider("베팅 금액 선택", min_value=min_bet, max_value=max_bet, step=50,
                          key="bet_slider_val", label_visibility="collapsed")
            with plus_col:
                st.button("+", use_container_width=True, key="bet_btn_plus",
                          on_click=_adjust_bet_amount, args=(50, min_bet, max_bet))
            st.markdown(f'<div class="cb-range-ends"><span>{min_bet:,}</span><span>{max_bet:,}</span></div>', unsafe_allow_html=True)

        rise_label = f"▲ {rank_climb}" if rank_climb else "—"
        st.markdown(
            f"""
            <div class="cb-prediction">
              <div class="cb-stat">
                <div class="cb-stat-label"><span class="cb-stat-art">🪙</span>예상 당첨액 ⓘ</div>
                <div class="cb-stat-number is-gold">+ {expected_payout:,}</div>
                <div class="cb-stat-pill">배율 2.0x</div>
              </div>
              <div class="cb-stat">
                <div class="cb-stat-label"><span class="cb-stat-art">🏆</span>예상 랭킹 변동 ⓘ</div>
                <div class="cb-rank-delta">{rise_label}</div>
                <div class="cb-stat-sub">{curr_rank}위 → <b>{sim_rank}위</b></div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button(f"⚡ {bet_val:,} 베팅하기", key="bet_confirm_cta", use_container_width=True, type="primary"):
            return bet_val
        st.markdown('<div class="cb-betting-note">베팅 금액에 따라 예상 수익과 순위가 달라집니다.</div>', unsafe_allow_html=True)

    return None
