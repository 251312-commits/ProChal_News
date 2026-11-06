import streamlit as st
import base64
from html import escape
from pathlib import Path
from games.game1_article_ui import render_game1_article
from games.news_roulette import render_news_slot
from games.betting_math import calculate_expected_gain, format_payout_multiplier, project_rank_change
import streamlit.components.v1 as components
from modules.news_ai import bring_article, pick_3_lowest_count_news
from modules.db_handler import init_news_sheet
from modules.ui_components import change_page, load_local_image_as_base64

ws_news = init_news_sheet()

MIN_BET = 1_000
_ASSET_ROOT = Path(__file__).resolve().parents[1] / "assets"
_REPO_ROOT = _ASSET_ROOT.parent


def _get_news_candidates(candidates_key):
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
            return []

        st.session_state[candidates_key] = pick_3_lowest_count_news(news_data)

    return st.session_state[candidates_key]


def _open_chosen_article(item, news_key, candidates_key, *, keep_candidates=False):
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
    if keep_candidates:
        item['count'] = new_count
    else:
        del st.session_state[candidates_key]
    st.rerun()


def get_game_news_selection(game_id: str, *, win_multiplier=None):
    news_key = f"selected_news_{game_id}"
    candidates_key = f"candidates_{game_id}"
    read_done_key = f"read_done_{game_id}"

    if st.session_state.get(read_done_key, False):
        chosen = st.session_state[news_key]
        return chosen['title'], chosen['text'], chosen['url']

    if game_id == "game_1":
        chosen = st.session_state.get(news_key)
        if not chosen:
            candidates = _get_news_candidates(candidates_key)
            if candidates:
                index = render_news_slot(candidates)
                if index is not None:
                    _open_chosen_article(candidates[index], news_key, candidates_key, keep_candidates=True)
            return None, None, None

        reward = None
        if win_multiplier is not None:
            reward = calculate_expected_gain(st.session_state["game_1_bet"], win_multiplier)
        action = render_game1_article(chosen, reward=reward)
        if action == "predict":
            st.session_state[read_done_key] = True
            st.session_state.pop(candidates_key, None)
            st.rerun()
        elif action == "back":
            del st.session_state[news_key]
            st.rerun()
        elif action == "bank":
            change_page("bank")
        return None, None, None

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

        candidates = _get_news_candidates(candidates_key)
        if not candidates:
            return None, None, None

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
                    _open_chosen_article(item, news_key, candidates_key)

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


@st.dialog("잔액 부족", dismissible=False)
def _no_money_modal(min_required, current_coins):
    # This artwork includes the 1,000C minimum in its lettering.
    use_art = min_required == 1_000
    if use_art:
        st.html(Path(__file__).with_name("low_balance.css"))
    with st.container(key="low_balance_panel" if use_art else None):
        if use_art:
            art = load_local_image_as_base64(str(_ASSET_ROOT / "low_balance.webp"))
            st.html(f"""
                <div class="low-balance-art">
                    <img src="{art}" alt="잔액 부족. 베팅하려면 {min_required:,}C가 필요합니다.">
                    <output aria-label="현재 보유액">{current_coins:,}C</output>
                </div>
            """)
        else:
            st.write(f"최소 베팅액은 {min_required:,}C이며, 현재 보유액은 {current_coins:,}C입니다.")

        if st.button("은행으로 가기", key="low_balance_bank", width="stretch"):
            change_page("bank")
        if st.button("메인으로", key="low_balance_main", width="stretch"):
            change_page("main")


def check_user_coins_or_pop_bank(min_required=MIN_BET):
    """
    유저의 코인을 검사하고, 부족하면 은행 유도 팝업을 띄운 뒤 False를 반환합니다.
    코인이 충분하면 True를 반환합니다.
    
    사용 예시:
    if not check_user_coins_or_pop_bank():
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


def render_betting_ui(current_coins, users_data=None, current_sid="", current_nickname="", min_bet=MIN_BET, bg_image_path=None, *, payout_multiplier, title="title"):
    """Responsive betting screen with configurable net-win multiplier and title.

    payout_multiplier is the factor *added* to the existing coin balance on a win.
    Return value stays unchanged: None before confirmation, wager on click.
    """
    current_coins = int(current_coins)
    min_bet = max(MIN_BET, int(min_bet))
    if current_coins < min_bet:
        _no_money_modal(min_bet, current_coins)
        return None

    step = 50
    max_bet = min_bet + ((current_coins - min_bet) // step) * step
    stored_bet = int(st.session_state.get("bet_slider_val", min_bet))
    stored_bet = min_bet + ((stored_bet - min_bet) // step) * step
    st.session_state["bet_slider_val"] = max(min_bet, min(max_bet, stored_bet))
    bet_val = st.session_state["bet_slider_val"]

    def asset(filename):
        try:
            return load_local_image_as_base64(str(_ASSET_ROOT / filename))
        except (OSError, ValueError):
            return None

    crown_img = asset("bet_crown.png")
    news_img = asset("bet_news_cards.png")
    podium_img = asset("bet_podium.png")
    coin_img = asset("bet_coin_stack.png")
    background_img = asset("bet_background.jpg")
    if not background_img and bg_image_path:
        try:
            # Keep optional paths relative to the repository, not the process cwd.
            background_path = Path(bg_image_path)
            if not background_path.is_absolute():
                background_path = _REPO_ROOT / background_path
            background_img = load_local_image_as_base64(str(background_path))
        except (OSError, ValueError):
            pass

    # The UI must use the same *net win* multiplier as the game's settlement.
    expected_payout = calculate_expected_gain(bet_val, payout_multiplier)
    multiplier_label = format_payout_multiplier(payout_multiplier)
    curr_rank, sim_rank = project_rank_change(
        users_data, current_coins, current_sid, current_nickname, expected_payout
    )
    safe_title = escape(str(title))

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
            background:linear-gradient(170deg,rgba(23,6,43,.53),rgba(8,3,22,.65));
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
        .cb-game-title {
            margin:5px auto 6px !important; padding:0 8px;
            color:#ffe4a8; font-weight:800; letter-spacing:.07em;
            font-size:clamp(.94rem,3.8vw,1.25rem);
            line-height:1.4; overflow-wrap:anywhere;
            text-shadow:0 0 14px rgba(160,74,241,.6);
        }
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
            margin-top:clamp(8px,1.8vw,16px);
            filter:drop-shadow(0 8px 14px rgba(8,0,18,.65));}
        .cb-art-fallback {width:90%;margin:auto;border:1px solid #ae41e6;
            border-radius:18px;background:#291244;color:#e7a9ff;font-size:3.7rem;text-align:center;padding:30px;}
        .st-key-casino_bet_controls {min-width:0 !important;width:100% !important;
            border:1px solid #9c34d3;border-radius:22px;
            padding:clamp(12px,2.4vw,17px) !important;
            background:linear-gradient(145deg,rgba(43,12,67,.79),rgba(15,5,30,.82));
            box-shadow:inset 0 2px 12px rgba(197,87,255,.19),0 0 15px rgba(137,26,209,.2);}
        .cb-amount {display:flex;align-items:center;justify-content:center;gap:10px;
            font-size:clamp(1.75rem,7vw,2.45rem);font-weight:950;
            line-height:1.1;font-variant-numeric:tabular-nums;}
        /* Use a three-cell amount row. The full-width slider lives BELOW it,
           never inside a narrow Streamlit column (the previous overflow cause). */
        .st-key-casino_bet_amount_row {
            width:100% !important;min-width:0 !important;
        }
        .st-key-casino_bet_amount_row [data-testid="stHorizontalBlock"] {
            width:100% !important;min-width:0 !important;
            display:grid !important;
            grid-template-columns:clamp(36px,9vw,47px) minmax(0,1fr) clamp(36px,9vw,47px) !important;
            align-items:center !important;gap:clamp(5px,1.5vw,11px) !important;
        }
        .st-key-casino_bet_amount_row [data-testid="stHorizontalBlock"] > [data-testid="column"] {
            width:100% !important;min-width:0 !important;
            flex:initial !important;
        }
        .st-key-casino_bet_amount_row [data-testid="stHorizontalBlock"] > [data-testid="column"] > div {
            min-width:0 !important;max-width:100% !important;
        }
        .cb-amount {
            display:flex; align-items:center; justify-content:center; gap:6px;
            min-width:0; max-width:100%; text-align:center;
            font-size:clamp(1.35rem,6.2vw,2.45rem);
            font-weight:950;line-height:1.1;font-variant-numeric:tabular-nums;
            white-space:nowrap;
        }
        .cb-amount .cb-coin-symbol {
            width:clamp(24px,6vw,34px); height:clamp(24px,6vw,34px);
            font-size:clamp(.85rem,3.5vw,1.12rem);
        }
        .st-key-bet_btn_minus button,.st-key-bet_btn_plus button {
            width:100% !important;height:clamp(36px,9vw,47px) !important;
            min-height:0 !important;padding:0 !important;border-radius:50% !important;
            border:1.5px solid #b72cff !important;background:#210a38 !important;
            color:white !important;font-size:1.5rem !important;
            box-shadow:0 0 11px rgba(161,39,244,.55) !important;
        }
        .st-key-bet_btn_minus button:disabled,.st-key-bet_btn_plus button:disabled {
            opacity:.37 !important;cursor:default !important;
        }
        /* Slider occupies the entire container width, inset by its thumb radius. */
        .st-key-casino_bet_controls [data-testid="stSlider"] {
            min-width:0 !important;width:100% !important;
            max-width:100% !important;box-sizing:border-box !important;
            padding:0 14px !important;margin:0 !important;
        }
        .st-key-casino_bet_controls [data-baseweb="slider"] {
            width:100% !important;min-width:0 !important;
            max-width:100% !important;
        }
        .st-key-casino_bet_controls [data-baseweb="slider"] [role="slider"] {
            width:24px !important;height:24px !important;
            background:#f3c8ff !important;border:3px solid #fff5ff !important;
            box-shadow:0 0 9px 2px #c64aff !important;touch-action:pan-y;
        }
        .st-key-casino_bet_controls [data-testid="stTickBar"] {display:none !important;}
        .cb-ends {display:flex;justify-content:space-between;
            padding:0 clamp(39px,10vw,53px);font-size:.78rem;color:#ac9bbe;font-variant-numeric:tabular-nums;}
        .cb-fixed-track {position:relative;width:100%;height:7px;margin:14px 0;
            border-radius:8px;background:linear-gradient(90deg,#ad38f4,#7420a9);}
        .cb-fixed-track::after {content:'';position:absolute;top:50%;left:50%;
            transform:translate(-50%,-50%);width:24px;height:24px;
            border:3px solid #fff;border-radius:50%;background:#e7b3ff;box-shadow:0 0 8px #af31e7;}
        .cb-stats {display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);
            border:1px solid #9631e1;border-radius:21px;overflow:hidden;
            background:linear-gradient(130deg,rgba(54,13,80,.77),rgba(18,6,36,.83));
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
        .cb-rank-unavailable {color:#b2a1c4;font-size:.78rem;white-space:normal;}
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
        /* Mobile-specific compact layout. Background remains visible; only
           the large decorative scene shrinks on short devices. */
        @media(max-width:600px) {
            .stApp:has(.st-key-casino_betting_shell) header[data-testid="stHeader"] {
                height:0 !important;min-height:0 !important;visibility:hidden !important;
            }
            .block-container:has(.st-key-casino_betting_shell) {
                width:100% !important;max-width:100% !important;
                min-width:0 !important;box-sizing:border-box !important;
                padding:4px 8px max(8px,env(safe-area-inset-bottom)) !important;
            }
            .st-key-casino_betting_shell {
                width:100% !important;max-width:100% !important;
                min-width:0 !important; margin:0 auto !important;
                padding:8px 10px !important; border-radius:17px !important;
            }
            .st-key-casino_betting_shell [data-testid="stVerticalBlock"] {
                gap:3px !important;
            }
            .st-key-casino_betting_shell [data-testid="stHorizontalBlock"] {
                flex-flow:row nowrap !important;min-width:0 !important;
            }
            .st-key-casino_betting_shell .cb-logo {
                display:block;width:auto !important;height:clamp(39px,8dvh,67px) !important;
                max-width:min(82%,245px) !important;object-fit:contain;
                margin:0 auto 1px !important;
            }
            .st-key-casino_betting_shell .cb-game-title {
                font-size:clamp(.75rem,3.3vw,.98rem) !important;
                line-height:1.12 !important; margin:0 auto 2px !important;
            }
            .st-key-casino_betting_shell .cb-heading {
                font-size:clamp(1.22rem,5.4vw,1.65rem) !important;
                line-height:1.13 !important;
            }
            .st-key-casino_betting_shell .cb-description {
                font-size:clamp(.68rem,2.8vw,.86rem) !important;
                margin:1px 0 !important;
                line-height:1.25 !important;
            }
            /* Separate rows ensure the podium never covers the mystery card.
               The scene is only slightly taller than before, avoiding extra scroll. */
            .st-key-casino_betting_shell .cb-scene {
                width:100% !important;height:clamp(180px,29dvh,252px) !important;
                margin:0 auto !important;position:relative !important;
                display:grid !important;
                grid-template-rows:minmax(0,1fr) minmax(0,1fr) !important;
                justify-items:center !important;align-items:center !important;
                row-gap:3px !important;overflow:visible;
            }
            .st-key-casino_betting_shell .cb-news-image {
                position:static !important;top:auto !important;left:auto !important;
                transform:none !important;
                width:100% !important;max-width:100% !important;
                height:100% !important;min-height:0 !important;
                object-fit:contain !important;align-self:center;
            }
            .st-key-casino_betting_shell .cb-podium-image {
                position:static !important;left:auto !important;bottom:auto !important;
                transform:none !important;margin:0 !important;
                width:90% !important;max-width:90% !important;
                height:100% !important;min-height:0 !important;
                object-fit:contain !important;align-self:center;
            }
            .st-key-casino_betting_shell .cb-art-fallback {
                position:relative;padding:15px !important;font-size:2rem !important;
            }
            .st-key-casino_bet_controls {
                padding:8px 10px !important;border-radius:17px !important;
            }
            .st-key-casino_bet_amount_row [data-testid="stHorizontalBlock"] {
                display:grid !important;grid-template-columns:36px minmax(0,1fr) 36px !important;
                gap:5px !important;
            }
            .st-key-bet_btn_minus button,.st-key-bet_btn_plus button {
                width:36px !important;height:36px !important;font-size:1.25rem !important;
            }
            .st-key-casino_bet_controls [data-testid="stSlider"] {
                padding:0 15px !important;
            }
            .st-key-casino_betting_shell .cb-ends {
                padding:0 15px !important;font-size:.69rem !important;
                line-height:1.1 !important;
            }
            .st-key-casino_betting_shell .cb-stats {
                border-radius:15px !important;
            }
            .st-key-casino_betting_shell .cb-stat {
                padding:7px 9px !important;
            }
            .st-key-casino_betting_shell .cb-small-coin {
                width:26px !important;height:23px !important;
            }
            .st-key-casino_betting_shell .cb-stat-label {
                font-size:clamp(.64rem,2.7vw,.8rem) !important;
                line-height:1.2 !important;
            }
            .st-key-casino_betting_shell .cb-stat-value {
                font-size:clamp(1.12rem,4.8vw,1.55rem) !important;
                line-height:1.1 !important;margin-top:3px !important;
            }
            .st-key-casino_betting_shell .cb-pill {
                margin-top:2px !important;padding:1px 7px !important;
            }
            .st-key-casino_betting_shell .cb-rank {
                margin-top:3px !important;
                font-size:clamp(.83rem,3.5vw,1rem) !important;
            }
            .st-key-casino_betting_shell .cb-up {
                margin-top:1px !important;font-size:.7rem !important;
            }
            .st-key-bet_confirm_cta button {
                min-height:48px !important;
                font-size:clamp(1.05rem,4.6vw,1.3rem) !important;
            }
            .st-key-casino_betting_shell .cb-footnote {display:none !important;}
        }
        @media(max-width:600px) and (max-height:720px) {
            .st-key-casino_betting_shell .cb-logo {
                height:clamp(34px,7dvh,48px) !important;
            }
            .st-key-casino_betting_shell .cb-scene {
                height:clamp(145px,25dvh,178px) !important;
            }
            .st-key-casino_betting_shell .cb-hero {margin:0 !important;}
            .st-key-casino_betting_shell .cb-stat {padding:5px 8px !important;}
            .st-key-casino_bet_controls {padding:6px 8px !important;}
            .st-key-bet_confirm_cta button {min-height:44px !important;}
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
            f'background-image:linear-gradient(180deg,rgba(8,1,20,.15),rgba(9,2,20,.39)),url("{background_img}") !important;'
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
              <p class="cb-game-title">{safe_title}</p>
              <h2 class="cb-heading">얼마를 걸까요?</h2>
              <p class="cb-description">베팅하면 뉴스가 공개됩니다</p>
              <div class="cb-scene">{news_html}{podium_html}</div>
            </section>
            ''', unsafe_allow_html=True,
        )

        with st.container(key="casino_bet_controls"):
            # Buttons sit beside the amount; slider gets a separate full-width row.
            # Avoids native Streamlit slider minimum-width pushing the minus button off-screen.
            with st.container(key="casino_bet_amount_row"):
                minus, amount_col, plus = st.columns([1, 4, 1], gap="small")
                with minus:
                    st.button("−", key="bet_btn_minus", use_container_width=True,
                              disabled=(bet_val <= min_bet),
                              on_click=_adjust_bet_amount, args=(-step, min_bet, max_bet))
                with amount_col:
                    st.markdown(
                        f'<div class="cb-amount"><span class="cb-coin-symbol">$</span>{bet_val:,}</div>',
                        unsafe_allow_html=True,
                    )
                with plus:
                    st.button("+", key="bet_btn_plus", use_container_width=True,
                              disabled=(bet_val >= max_bet),
                              on_click=_adjust_bet_amount, args=(step, min_bet, max_bet))
            if max_bet > min_bet:
                st.slider("베팅 금액", min_value=min_bet, max_value=max_bet,
                          step=step, key="bet_slider_val", label_visibility="collapsed")
            else:
                st.markdown('<div class="cb-fixed-track"></div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="cb-ends"><span>{min_bet:,}</span><span>{max_bet:,}</span></div>',
                unsafe_allow_html=True,
            )

        if curr_rank is None:
            up_display = "조회 불가"
            rank_display = '<span class="cb-rank-unavailable">랭킹 데이터 없음</span>'
        else:
            change = curr_rank - sim_rank
            up_display = f'▲ {change}' if change > 0 else (f'▼ {abs(change)}' if change < 0 else '—')
            rank_display = f'{curr_rank}위 → <b>{sim_rank}위</b>'
        st.markdown(
            f'''
            <div class="cb-stats">
              <div class="cb-stat">
                <div class="cb-stat-label">{coin_html}<span>예상 당첨액 ⓘ</span></div>
                <div class="cb-stat-value">+ {expected_payout:,}</div>
                <div class="cb-pill">배율 {multiplier_label}</div>
              </div>
              <div class="cb-stat">
                <div class="cb-stat-label"><span aria-hidden="true">🏆</span><span>예상 랭킹 변동 ⓘ</span></div>
                <div class="cb-up">{up_display}</div>
                <div class="cb-rank">{rank_display}</div>
              </div>
            </div>
            ''', unsafe_allow_html=True,
        )
        if st.button(f"⚡ {bet_val:,} 베팅하기", type="primary", key="bet_confirm_cta", use_container_width=True):
            return bet_val
        st.markdown('<p class="cb-footnote">베팅 금액에 따라 예상 수익과 순위가 달라집니다.</p>', unsafe_allow_html=True)

    return None
