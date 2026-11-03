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
    """Keep the shared slider in valid 50-coin increments."""
    current = int(st.session_state.get("bet_slider_val", min_val))
    aligned = min_val + ((current - min_val) // 50) * 50
    st.session_state["bet_slider_val"] = max(min_val, min(max_val, aligned + step))


def render_betting_ui(current_coins, users_data=None, current_sid="", current_nickname="", min_bet=100, bg_image_path=None):
    """Responsive betting screen, using the supplied alpha PNG assets.

    Keep the return contract unchanged: None before confirmation, wager on click.
    """
    current_coins = int(current_coins)
    min_bet = int(min_bet)
    if current_coins < min_bet:
        st.error(f"최소 베팅 금액 {min_bet:,} C에 필요한 코인이 부족합니다.")
        return None

    step = 50
    max_bet = min_bet + ((current_coins - min_bet) // step) * step
    initial_bet = min_bet + ((min(500, max_bet) - min_bet) // step) * step
    stored_bet = int(st.session_state.get("bet_slider_val", initial_bet))
    stored_bet = min_bet + ((stored_bet - min_bet) // step) * step
    st.session_state["bet_slider_val"] = max(min_bet, min(max_bet, stored_bet))
    bet_val = st.session_state["bet_slider_val"]

    def asset(filename):
        try:
            return load_local_image_as_base64(f"assets/{filename}")
        except (OSError, ValueError):
            return None

    crown_img = asset("bet_crown.png")
    news_img = asset("bet_news_cards.png")
    podium_img = asset("bet_podium.png")
    coin_img = asset("bet_coin_stack.png")
    background_img = asset("bet_background.jpg")
    if not background_img and bg_image_path:
        try:
            background_img = load_local_image_as_base64(bg_image_path)
        except (OSError, ValueError):
            pass

    # Projection preserves the existing illustrative 2x multiplier and rank calculation.
    expected_payout = bet_val * 2
    simulated_total_coins = current_coins + expected_payout
    curr_rank, sim_rank, rank_climb = 1, 1, 0
    if users_data:
        clean_sid = str(current_sid).strip().replace(".0", "")
        clean_nick = str(current_nickname).strip()
        processed_users = []
        for user in users_data:
            try:
                amount = int(user.get("코인", 0))
            except (ValueError, TypeError):
                amount = 0
            user_sid = str(user.get("학번", user.get("id", ""))).strip().replace(".0", "")
            user_nick = str(user.get("아이디", user.get("nickname", ""))).strip()
            is_me = bool((clean_sid and user_sid == clean_sid) or (clean_nick and user_nick == clean_nick))
            processed_users.append({"coins": amount, "is_me": is_me})
        ranked = sorted(processed_users, key=lambda item: item["coins"], reverse=True)
        curr_rank = next((i + 1 for i, user in enumerate(ranked) if user["is_me"]), len(ranked) + 1)
        future_ranked = sorted(
            [{"coins": simulated_total_coins if user["is_me"] else user["coins"], "is_me": user["is_me"]}
             for user in processed_users],
            key=lambda item: item["coins"], reverse=True,
        )
        sim_rank = next((i + 1 for i, user in enumerate(future_ranked) if user["is_me"]), curr_rank)
        rank_climb = max(0, curr_rank - sim_rank)

    # Scoped, asset-proportion-based layout: never position 2D art using fixed heights.
    st.markdown(
        """
        <style>
        .block-container:has(.st-key-casino_betting_shell) {
            width:100% !important; max-width:690px !important;
            box-sizing:border-box !important;margin-inline:auto !important;
            padding: max(8px,env(safe-area-inset-top)) clamp(9px,2.8vw,22px)
                max(22px,env(safe-area-inset-bottom)) !important;
        }
        .st-key-casino_betting_shell, .st-key-casino_betting_shell * {box-sizing:border-box;}
        .st-key-casino_betting_shell {
            width:100%;max-width:650px;margin:0 auto 12px;
            min-width:0;overflow:hidden;padding:clamp(11px,2.7vw,23px);
            border:1px solid rgba(178,75,247,.52);border-radius:24px;
            color:#fdf7ff;
            background:linear-gradient(170deg,rgba(23,6,43,.87),rgba(8,3,22,.91));
            box-shadow:0 0 38px rgba(116,28,195,.25),inset 0 0 22px rgba(150,45,221,.17);
        }
        .st-key-casino_betting_shell [data-testid="stVerticalBlock"] {gap:clamp(6px,1.4vw,12px);}
        .st-key-casino_betting_shell [data-testid="stHorizontalBlock"] {
            display:flex !important; flex-flow:row nowrap !important;
            gap:clamp(3px,1.2vw,10px) !important;align-items:center !important;
        }
        .st-key-casino_betting_shell [data-testid="column"] {min-width:0 !important;padding:0 !important;}
        .st-key-casino_betting_shell button {font-family:inherit !important;}
        .st-key-bet_nav_back button,.st-key-bet_nav_bank button {
            display:block !important;width:clamp(34px,8vw,44px) !important;
            height:clamp(34px,8vw,44px) !important; min-height:0 !important;
            padding:0 !important;border-radius:50% !important;
            border:1.5px solid #aa39ec !important;background:rgba(20,7,39,.82) !important;
            box-shadow:0 0 10px rgba(161,42,239,.44) !important;
            color:#fff !important; font-size:clamp(1.3rem,5vw,1.65rem) !important;
        }
        .cb-balance {min-width:0;display:flex;align-items:center;justify-content:flex-end;
            gap:7px;font-weight:900;font-size:clamp(.87rem,3.8vw,1.38rem);
            font-variant-numeric:tabular-nums;white-space:nowrap;text-shadow:0 1px 7px #1d0031;}
        .cb-coin-symbol {flex:none;display:inline-grid;place-items:center;
            width:clamp(28px,7vw,37px);height:clamp(28px,7vw,37px);
            border:2px solid #ffd66b;border-radius:50%;font-size:clamp(1rem,4vw,1.3rem);
            color:#b86a00;background:radial-gradient(circle at 27% 22%,#fff4b6,#ffcd27 45%,#d17104 88%);
            box-shadow:inset 0 0 0 2px #ffdf72,0 0 13px rgba(243,157,36,.4);}
        .cb-hero {text-align:center;min-width:0;}
        .cb-logo {display:block;width:min(82%,365px);height:auto;margin:0 auto 3px;
            filter:drop-shadow(0 0 10px rgba(171,62,255,.35));}
        .cb-logo-fallback {font-size:1.5rem;color:#e6a9ff;font-weight:900;letter-spacing:4px;}
        .cb-heading {margin:0 !important;line-height:1.22;
            font-size:clamp(1.65rem,6.3vw,2.55rem);font-weight:950;letter-spacing:-.045em;
            color:#fff4ff;text-shadow:0 0 15px rgba(178,103,255,.32);}
        .cb-description {margin:3px 0 7px;color:#c9b6df;font-size:clamp(.78rem,3.2vw,1rem);}
        .cb-scene {width:100%;max-width:575px;margin:0 auto;display:flex;
            flex-direction:column;align-items:center;justify-content:flex-start;isolation:isolate;}
        .cb-news-image {display:block;position:relative;z-index:1;
            width:100%;height:auto;max-width:100%;object-fit:contain;
            filter:drop-shadow(0 0 13px rgba(170,41,234,.38));}
        .cb-podium-image {display:block;position:relative;z-index:2;
            width:89%;height:auto;max-width:89%;object-fit:contain;
            margin-top:clamp(-28px,-3.8vw,-10px);
            filter:drop-shadow(0 8px 14px rgba(8,0,18,.65));}
        .cb-art-fallback {width:90%;margin:auto;border:1px solid #ae41e6;
            border-radius:18px;background:#291244;color:#e7a9ff;font-size:3.7rem;text-align:center;padding:30px;}
        .st-key-casino_bet_controls {min-width:0 !important;width:100% !important;
            border:1px solid #9c34d3;border-radius:22px;
            padding:clamp(12px,2.4vw,17px) !important;
            background:linear-gradient(145deg,rgba(43,12,67,.96),rgba(15,5,30,.96));
            box-shadow:inset 0 2px 12px rgba(197,87,255,.19),0 0 15px rgba(137,26,209,.2);}
        .cb-amount {display:flex;align-items:center;justify-content:center;gap:10px;
            font-size:clamp(1.75rem,7vw,2.45rem);font-weight:950;
            line-height:1.1;font-variant-numeric:tabular-nums;}
        .st-key-casino_bet_row {width:100% !important;min-width:0 !important;}
        .st-key-casino_bet_row [data-testid="stHorizontalBlock"] {
            display:flex !important;flex-flow:row nowrap !important;align-items:center !important;
            gap:clamp(5px,1.4vw,10px) !important;min-width:0 !important;}
        .st-key-casino_bet_row [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child,
        .st-key-casino_bet_row [data-testid="stHorizontalBlock"] > [data-testid="column"]:last-child {
            flex:0 0 clamp(36px,9vw,47px) !important;width:clamp(36px,9vw,47px) !important;}
        .st-key-casino_bet_row [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2) {
            flex:1 1 0 !important;width:0 !important;min-width:0 !important;}
        .st-key-bet_btn_minus button,.st-key-bet_btn_plus button {
            width:clamp(36px,9vw,47px) !important;height:clamp(36px,9vw,47px) !important;
            min-height:0 !important;padding:0 !important;border-radius:50% !important;
            border:1.5px solid #b72cff !important;background:#210a38 !important;
            color:white !important;font-size:1.5rem !important;
            box-shadow:0 0 11px rgba(161,39,244,.55) !important;}
        .st-key-bet_btn_minus button:disabled,.st-key-bet_btn_plus button:disabled {
            opacity:.37 !important;cursor:default !important;}
        .st-key-casino_bet_row [data-testid="stSlider"],
        .st-key-casino_bet_row [data-baseweb="slider"] {min-width:0 !important;width:100% !important;}
        .st-key-casino_bet_row [data-baseweb="slider"] [role="slider"] {
            width:25px !important;height:25px !important;
            background:#f3c8ff !important;border:3px solid #fff5ff !important;
            box-shadow:0 0 11px 3px #c64aff !important;touch-action:pan-y;}
        .st-key-casino_bet_row [data-testid="stTickBar"] {display:none !important;}
        .cb-ends {display:flex;justify-content:space-between;
            padding:0 clamp(39px,10vw,53px);font-size:.78rem;color:#ac9bbe;font-variant-numeric:tabular-nums;}
        .cb-fixed-track {position:relative;width:100%;height:7px;margin:14px 0;
            border-radius:8px;background:linear-gradient(90deg,#ad38f4,#7420a9);}
        .cb-fixed-track::after {content:'';position:absolute;top:50%;left:50%;
            transform:translate(-50%,-50%);width:24px;height:24px;
            border:3px solid #fff;border-radius:50%;background:#e7b3ff;box-shadow:0 0 8px #af31e7;}
        .cb-stats {display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);
            border:1px solid #9631e1;border-radius:21px;overflow:hidden;
            background:linear-gradient(130deg,rgba(54,13,80,.95),rgba(18,6,36,.97));
            box-shadow:0 0 19px rgba(136,30,213,.26),inset 0 0 14px rgba(151,47,241,.18);}
        .cb-stat {min-width:0;padding:clamp(10px,2.8vw,16px);}
        .cb-stat + .cb-stat {border-left:1px solid rgba(185,87,238,.34);}
        .cb-stat-label {display:flex;align-items:center;gap:4px;
            font-size:clamp(.67rem,2.7vw,.86rem);color:#eee0f5;font-weight:750;
            line-height:1.35;word-break:keep-all;}
        .cb-small-coin {width:clamp(28px,6vw,42px);height:clamp(25px,5.8vw,39px);
            object-fit:contain;flex-shrink:0;margin:-3px 0;}
        .cb-stat-value {font-size:clamp(1.25rem,5.9vw,2.2rem);font-weight:900;
            color:#ffd46c;line-height:1.3;margin-top:6px;font-variant-numeric:tabular-nums;
            overflow-wrap:anywhere;}
        .cb-pill {display:inline-block;margin-top:4px;padding:2px 9px;
            border:1px solid #a356d2;background:#29083d;border-radius:12px;
            color:#d59dfa;font-size:clamp(.65rem,2.5vw,.74rem);}
        .cb-rank {font-size:clamp(.93rem,4vw,1.25rem);font-weight:850;margin-top:11px;
            font-variant-numeric:tabular-nums;white-space:nowrap;}
        .cb-rank b {color:#ca6bff;}
        .cb-up {color:#43e4bc;font-size:.8rem;font-weight:850;white-space:nowrap;margin-top:3px;}
        .st-key-bet_confirm_cta button {
            width:100% !important;min-height:clamp(62px,14vw,83px) !important;
            border-radius:999px !important;border:2px solid #ea8dff !important;
            background:linear-gradient(180deg,#c84bff,#850ef4 50%,#4b0bcb) !important;
            color:white !important;font-weight:950 !important;
            font-size:clamp(1.17rem,5.2vw,1.75rem) !important;
            box-shadow:inset 0 5px 9px rgba(255,255,255,.3),inset 0 -7px 10px rgba(52,7,130,.55),
                0 5px 21px rgba(183,33,238,.52) !important;}
        .cb-footnote {text-align:center;margin:0;color:#a995b9;font-size:.72rem;}
        @media(max-width:380px) {
            .st-key-casino_betting_shell {border-radius:17px;padding:10px;}
            .cb-logo {width:min(79%,270px);}
            .cb-description {margin-bottom:4px;}
            .cb-podium-image {width:92%;max-width:92%;}
            .st-key-casino_bet_controls {padding:12px 9px !important;border-radius:18px;}
            .cb-stat {padding:10px 8px;}
            .cb-stat-label {gap:3px;}
            .cb-rank {font-size:clamp(.83rem,3.8vw,1rem);}
            .cb-ends {font-size:.69rem;}
        }
        @media(prefers-reduced-motion:no-preference) {
            .cb-news-image {animation:cb-float 4.8s ease-in-out infinite;}
            @keyframes cb-float {0%,100% {translate:0 0;}50% {translate:0 -4px;}}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if background_img:
        st.markdown(
            f'<style>.stApp:has(.st-key-casino_betting_shell) {{'
            f'background-image:linear-gradient(180deg,rgba(8,1,20,.27),rgba(9,2,20,.62)),url("{background_img}") !important;'
            f'background-size:cover !important;background-position:center top !important;'
            f'background-attachment:scroll !important;background-color:#0b031b !important;'
            f'}}</style>',
            unsafe_allow_html=True,
        )

    logo_html = (f'<img class="cb-logo" src="{crown_img}" alt="BET 로고">'
                 if crown_img else '<div class="cb-logo-fallback">♛ BET</div>')
    news_html = (f'<img class="cb-news-image" src="{news_img}" alt="물음표 뉴스 카드">'
                 if news_img else '<div class="cb-art-fallback">?</div>')
    podium_html = (f'<img class="cb-podium-image" src="{podium_img}" alt="왕관 금화와 원형 받침대">'
                   if podium_img else '<div class="cb-art-fallback">♛</div>')
    coin_html = (f'<img class="cb-small-coin" src="{coin_img}" alt="">'
                 if coin_img else '<span aria-hidden="true">🪙</span>')

    with st.container(key="casino_betting_shell"):
        left, middle, right = st.columns([0.8, 3.2, 0.8], gap="small")
        with left:
            if st.button("❮", key="bet_nav_back", help="메인으로"):
                change_page("main")
        with middle:
            st.markdown(
                f'<div class="cb-balance"><span class="cb-coin-symbol">$</span>{current_coins:,}</div>',
                unsafe_allow_html=True,
            )
        with right:
            if st.button("+", key="bet_nav_bank", help="은행으로"):
                change_page("bank")

        st.markdown(
            f'''
            <section class="cb-hero" aria-label="베팅 금액 선택">
              {logo_html}
              <h2 class="cb-heading">얼마를 걸까요?</h2>
              <p class="cb-description">베팅하면 뉴스가 공개됩니다</p>
              <div class="cb-scene">{news_html}{podium_html}</div>
            </section>
            ''', unsafe_allow_html=True,
        )

        with st.container(key="casino_bet_controls"):
            st.markdown(
                f'<div class="cb-amount"><span class="cb-coin-symbol">$</span>{bet_val:,}</div>',
                unsafe_allow_html=True,
            )
            with st.container(key="casino_bet_row"):
                minus, slider_column, plus = st.columns([1, 5, 1], gap="small")
                with minus:
                    st.button("−", key="bet_btn_minus", use_container_width=True,
                              disabled=(bet_val <= min_bet),
                              on_click=_adjust_bet_amount, args=(-step, min_bet, max_bet))
                with slider_column:
                    if max_bet > min_bet:
                        st.slider("베팅 금액", min_value=min_bet, max_value=max_bet,
                                  step=step, key="bet_slider_val", label_visibility="collapsed")
                    else:
                        st.markdown('<div class="cb-fixed-track"></div>', unsafe_allow_html=True)
                with plus:
                    st.button("+", key="bet_btn_plus", use_container_width=True,
                              disabled=(bet_val >= max_bet),
                              on_click=_adjust_bet_amount, args=(step, min_bet, max_bet))
            st.markdown(
                f'<div class="cb-ends"><span>{min_bet:,}</span><span>{max_bet:,}</span></div>',
                unsafe_allow_html=True,
            )

        up_display = f'▲ {rank_climb}' if rank_climb else '—'
        st.markdown(
            f'''
            <div class="cb-stats">
              <div class="cb-stat">
                <div class="cb-stat-label">{coin_html}<span>예상 당첨액 ⓘ</span></div>
                <div class="cb-stat-value">+ {expected_payout:,}</div>
                <div class="cb-pill">배율 2.0x</div>
              </div>
              <div class="cb-stat">
                <div class="cb-stat-label"><span aria-hidden="true">🏆</span><span>예상 랭킹 변동 ⓘ</span></div>
                <div class="cb-up">{up_display}</div>
                <div class="cb-rank">{curr_rank}위 → <b>{sim_rank}위</b></div>
              </div>
            </div>
            ''', unsafe_allow_html=True,
        )
        if st.button(f"⚡ {bet_val:,} 베팅하기", type="primary", key="bet_confirm_cta", use_container_width=True):
            return bet_val
        st.markdown('<p class="cb-footnote">베팅 금액에 따라 예상 수익과 순위가 달라집니다.</p>', unsafe_allow_html=True)

    return None
