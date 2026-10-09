import streamlit as st
import streamlit.components.v1 as components
from modules.news_ai import bring_article, pick_3_lowest_count_news
from modules.db_handler import init_gspread, init_news_sheet

ws = init_gspread()
ws_news = init_news_sheet()

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
