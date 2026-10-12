import streamlit as st
from modules.news_ai import summary, similarity_check
from modules.db_handler import init_gspread, init_news_sheet
from modules.ui_components import change_page
from games.common import get_game_news_selection

ws = init_gspread()
ws_news = init_news_sheet()

# 정의된 함수: show_game_1

def show_game_1():
    st.title("🎮 게임 1: 뉴스 유사도 예측 게임")

    # [1단계] 베팅 금액 선택 (네온 UI, 올인 심장소리 & 글로우 효과, 피라미드 코인 탑)
    if "game_1_bet" not in st.session_state:
        current_coins = int(st.session_state.current_user_data.get('코인', 0))
        current_sid = str(st.session_state.get('current_user', '')).strip().replace('.0', '')
        min_bet = 1000
        
        # 코인이 최소 베팅 금액보다 적을 경우 예외 처리
        if current_coins < min_bet:
            st.error(f"⚠️ 베팅을 위한 코인이 부족합니다! (최소 베팅금: {min_bet:,} C / 보유: {current_coins:,} C)")
            if st.button("⬅️ 메인으로 돌아가기", use_container_width=True):
                change_page('main')
            return

        # [초고속 연산] 유저 랭킹 캐싱
        if "ranking_users_cache" not in st.session_state:
            try:
                st.session_state.ranking_users_cache = ws.get_all_records()
            except Exception:
                st.session_state.ranking_users_cache = []

        users_data = st.session_state.ranking_users_cache

        # 처음 창에 들어왔을 때 기본 베팅 금액 = 보유 코인의 절반 (50 C 단위 내림)
        default_bet = max(min_bet, ((current_coins // 2) // 50) * 50)
        if "bet_slider_key" not in st.session_state:
            st.session_state["bet_slider_key"] = default_bet

        # 베팅 화면 네온 & 올인 펄스 & 애니메이션 CSS
        st.markdown(
            """
            <style>
            .bet-card-container {
                background: linear-gradient(135deg, #110022 0%, #1a0933 50%, #0d001a 100%);
                border: 2px solid #00ffcc;
                border-radius: 20px;
                padding: 20px;
                text-align: center;
                box-shadow: 0 0 20px rgba(0, 255, 204, 0.4);
                margin-bottom: 15px;
                transition: all 0.3s ease;
                animation: pulseGlow 3s infinite alternate;
            }
            @keyframes pulseGlow {
                0% { border-color: #00ffcc; box-shadow: 0 0 15px rgba(0, 255, 204, 0.4); }
                50% { border-color: #ff00ff; box-shadow: 0 0 25px rgba(255, 0, 255, 0.6); }
                100% { border-color: #00ffcc; box-shadow: 0 0 15px rgba(0, 255, 204, 0.4); }
            }
            .bet-header-title {
                font-family: 'Press Start 2P', monospace;
                font-size: 1.1rem;
                color: #fffb00;
                text-shadow: 0 0 8px #ff00ff, 0 0 15px #00ffff;
                margin-bottom: 8px;
            }
            .coin-pile-wrapper {
                display: flex;
                justify-content: center;
                align-items: flex-end;
                gap: 12px;
                min-height: 150px;
                padding: 22px 10px 15px 10px;
                background: radial-gradient(ellipse at bottom, rgba(255, 215, 0, 0.25) 0%, rgba(10, 0, 20, 0.85) 75%);
                border-radius: 16px;
                border: 1.5px dashed rgba(255, 215, 0, 0.5);
                box-shadow: inset 0 0 25px rgba(0, 0, 0, 0.9);
                margin: 15px 0;
                transition: all 0.3s ease;
            }
            .coin-stack-col {
                display: flex;
                flex-direction: column-reverse;
                align-items: center;
            }
            .gold-coin-item {
                width: 46px;
                height: 12px;
                border-radius: 50%;
                background: linear-gradient(180deg, #FFE57F 0%, #FFC107 40%, #FF8F00 70%, #A76D00 100%);
                border: 1px solid #FFF59D;
                box-shadow: 0 3px 0 #5D4037, inset 0 1px 2px rgba(255, 255, 255, 0.9);
                margin-top: -6px;
                animation: popIn 0.15s ease-out;
            }
            .gold-coin-item.top {
                background: radial-gradient(ellipse at 35% 35%, #FFFFFF 0%, #FFEE58 40%, #FFA000 85%);
                border: 1.5px solid #FFFFFF;
                box-shadow: 0 3px 0 #5D4037, 0 0 12px rgba(255, 215, 0, 0.9);
            }
            @keyframes popIn {
                0% { transform: scale(0.7); opacity: 0.5; }
                100% { transform: scale(1); opacity: 1; }
            }
            .payout-card {
                background: linear-gradient(90deg, rgba(255,0,255,0.2) 0%, rgba(0,255,204,0.2) 100%);
                border: 2px solid #ff00ff;
                border-radius: 14px;
                padding: 12px;
                text-align: center;
                box-shadow: 0 0 15px rgba(255, 0, 255, 0.4);
                height: 100%;
                display: flex;
                flex-direction: column;
                justify-content: center;
                transition: all 0.3s ease;
            }
            .payout-amount {
                font-size: 1.6rem;
                font-weight: 900;
                color: #00ffcc;
                text-shadow: 0 0 12px #00ffcc;
            }
            .rank-sim-card {
                background: linear-gradient(135deg, rgba(20, 10, 40, 0.9) 0%, rgba(35, 15, 60, 0.9) 100%);
                border: 2px solid #ffd700;
                border-radius: 14px;
                padding: 12px 14px;
                box-shadow: 0 0 15px rgba(255, 215, 0, 0.3);
                height: 100%;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                transition: all 0.3s ease;
            }
            .rank-up-badge {
                color: #00ffcc;
                font-size: 1.05rem;
                font-weight: 900;
                text-shadow: 0 0 8px #00ffcc;
            }
            .rival-row {
                font-size: 0.82rem;
                color: #ffffff;
                background: rgba(0, 0, 0, 0.4);
                padding: 4px 8px;
                border-radius: 8px;
                margin-top: 4px;
                border-left: 3px solid #ff00ff;
            }

            /* 올인 버튼 펄스 & 무지개 네온 */
            div[data-testid="column"]:first-child button {
                background: linear-gradient(45deg, #ff0055, #ff00ff, #ffcc00, #ff0055) !important;
                background-size: 300% 300% !important;
                animation: allInPulse 1.8s ease-in-out infinite !important;
                border: 2px solid #ffff00 !important;
                color: #ffffff !important;
                font-weight: 900 !important;
                font-size: 1.05rem !important;
                text-shadow: 0 0 8px #ff0000, 0 0 12px #ffff00 !important;
                box-shadow: 0 0 20px rgba(255, 0, 85, 0.8), 0 0 30px rgba(255, 255, 0, 0.6) !important;
            }
            @keyframes allInPulse {
                0% { background-position: 0% 50%; transform: scale(1); box-shadow: 0 0 15px #ff0055; }
                50% { background-position: 100% 50%; transform: scale(1.04); box-shadow: 0 0 30px #ffcc00, 0 0 45px #ff0055; }
                100% { background-position: 0% 50%; transform: scale(1); box-shadow: 0 0 15px #ff0055; }
            }

            /* 🔥 ALL-IN 상태일 때 넓어지는 글로우 & 다이내믹 빠른 색상 전환 */
            .allin-rapid-glow {
                animation: rapidGlowCycle 0.5s infinite alternate !important;
            }
            @keyframes rapidGlowCycle {
                0% {
                    box-shadow: 0 0 35px #ff0055, 0 0 60px rgba(255, 0, 85, 0.85);
                    border-color: #ff0055 !important;
                }
                50% {
                    box-shadow: 0 0 50px #ffcc00, 0 0 80px rgba(255, 204, 0, 0.95);
                    border-color: #ffcc00 !important;
                }
                100% {
                    box-shadow: 0 0 40px #00ffcc, 0 0 70px rgba(0, 255, 204, 0.85);
                    border-color: #00ffcc !important;
                }
            }

            /* 코인 창 심장박동(Heartbeat) 펄스 연출 */
            .allin-coin-pulse {
                animation: heartbeatWrapper 0.85s infinite ease-in-out !important;
                border-color: #ff0055 !important;
            }
            @keyframes heartbeatWrapper {
                0% { transform: scale(1); box-shadow: inset 0 0 30px rgba(255,0,85,0.7), 0 0 25px #ff0055; }
                15% { transform: scale(1.03); box-shadow: inset 0 0 45px rgba(255,0,85,0.9), 0 0 40px #ff00ff; }
                30% { transform: scale(1); box-shadow: inset 0 0 30px rgba(255,0,85,0.7), 0 0 25px #ff0055; }
                45% { transform: scale(1.04); box-shadow: inset 0 0 50px rgba(255,215,0,1), 0 0 45px #ffcc00; }
                70% { transform: scale(1); box-shadow: inset 0 0 30px rgba(255,0,85,0.7), 0 0 25px #ff0055; }
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        # 슬라이더 (기본값: 전재산의 반)
        bet_val = st.slider(
            "💰 베팅할 금액을 선택하세요",
            min_value=min_bet,
            max_value=current_coins,
            step=50,
            key="bet_slider_key"
        )

        is_all_in = (bet_val == current_coins)
        card_glow_class = "allin-rapid-glow" if is_all_in else ""
        coin_pulse_class = "allin-coin-pulse" if is_all_in else ""

        # 🔥 ALL-IN 달성 시 배경 심장소리 효과음(Web Audio API) 재생
        if is_all_in:
            st.markdown(
                """
                <script>
                (function() {
                    if (window.heartbeatAudioCtx) return;
                    try {
                        const ctx = new (window.AudioContext || window.webkitAudioContext)();
                        window.heartbeatAudioCtx = ctx;
                        
                        function playBeat() {
                            if (ctx.state === 'suspended') ctx.resume();
                            const now = ctx.currentTime;
                            
                            // 첫 번째 쿵 (Thump 1)
                            const osc1 = ctx.createOscillator();
                            const gain1 = ctx.createGain();
                            osc1.type = 'sine';
                            osc1.frequency.setValueAtTime(110, now);
                            osc1.frequency.exponentialRampToValueAtTime(25, now + 0.16);
                            gain1.gain.setValueAtTime(0.85, now);
                            gain1.gain.exponentialRampToValueAtTime(0.001, now + 0.16);
                            osc1.connect(gain1);
                            gain1.connect(ctx.destination);
                            osc1.start(now);
                            osc1.stop(now + 0.16);

                            // 두 번째 쿵 (Thump 2)
                            const osc2 = ctx.createOscillator();
                            const gain2 = ctx.createGain();
                            osc2.type = 'sine';
                            osc2.frequency.setValueAtTime(85, now + 0.22);
                            osc2.frequency.exponentialRampToValueAtTime(20, now + 0.40);
                            gain2.gain.setValueAtTime(0.65, now + 0.22);
                            gain2.gain.exponentialRampToValueAtTime(0.001, now + 0.40);
                            osc2.connect(gain2);
                            gain2.connect(ctx.destination);
                            osc2.start(now + 0.22);
                            osc2.stop(now + 0.40);
                        }
                        
                        window.heartbeatInterval = setInterval(playBeat, 850);
                        playBeat();
                    } catch(e) {}
                })();
                </script>
                """,
                unsafe_allow_html=True
            )

        # 상단 헤더 카드
        st.markdown(
            f"""
            <div class="bet-card-container {card_glow_class}">
                <div class="bet-header-title">🎰 STEP 1: BETTING PLACE</div>
                <div style="font-size: 1rem; color: #ffffff; font-weight: bold;">
                    현재 보유 코인: <span style="color:#ffd700;">🪙 {current_coins:,} C</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # 동적 골드 동전 피라미드 (중앙이 제일 높고 양 끝으로 갈수록 낮아지는 산 الشكل 탑)
        bet_ratio = (bet_val - min_bet) / max(1, (current_coins - min_bet)) if current_coins > min_bet else 1.0
        total_coins = int(4 + bet_ratio * 36)
        num_cols = min(5, max(1, (total_coins + 7) // 8))

        # 기둥(Column) 개수에 맞춘 산 형태 가중치 배열
        if num_cols == 1:
            weights = [1.0]
        elif num_cols == 2:
            weights = [1.0, 1.0]
        elif num_cols == 3:
            weights = [1.0, 2.2, 1.0]
        elif num_cols == 4:
            weights = [1.0, 2.2, 2.2, 1.0]
        else: # 5 cols
            weights = [1.0, 2.0, 3.5, 2.0, 1.0]

        sum_w = sum(weights)
        raw_heights = [int(round(total_coins * (w / sum_w))) for w in weights]
        diff = total_coins - sum(raw_heights)
        
        # 잔여 동전을 중앙 중심부터 분배하여 대칭 유지
        center_idx = num_cols // 2
        indices_order = sorted(range(num_cols), key=lambda x: abs(x - center_idx))
        for i in range(abs(diff)):
            idx = indices_order[i % num_cols]
            if diff > 0:
                raw_heights[idx] += 1
            elif diff < 0 and raw_heights[idx] > 1:
                raw_heights[idx] -= 1

        cols_html = ""
        for c, col_h in enumerate(raw_heights):
            coins_in_col_html = ""
            for h in range(col_h):
                is_top = (h == col_h - 1)
                coin_class = "gold-coin-item top" if is_top else "gold-coin-item"
                coins_in_col_html += f'<div class="{coin_class}"></div>'
            cols_html += f'<div class="coin-stack-col">{coins_in_col_html}</div>'

        # 코인 탑 출력 (올인 시 펄스 연출)
        st.markdown(
            f"""
            <div class="coin-pile-wrapper {coin_pulse_class}">
                {cols_html}
            </div>
            <div style="text-align:center; color:#ffd700; font-size:0.95rem; font-weight:800; margin-top:-5px; margin-bottom:15px;">
                현재 선택 칩: {bet_val:,} C {"(🚨 ALL-IN)" if is_all_in else ""}
            </div>
            """,
            unsafe_allow_html=True
        )

        # 정답(오차 0점) 달성 시 획득 최고 금액 (100배)
        max_reward = bet_val * 100
        simulated_total_coins = current_coins + max_reward

        # 실시간 랭킹 연산
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
        curr_rank = None
        for idx, u in enumerate(curr_sorted):
            if u['id'] == current_sid or u['nickname'] == st.session_state.current_user_data.get('아이디', ''):
                curr_rank = idx + 1
                break
        if not curr_rank:
            curr_rank = len(curr_sorted) + 1

        sim_list = []
        for u in processed_users:
            is_me = (u['id'] == current_sid or u['nickname'] == st.session_state.current_user_data.get('아이디', ''))
            sim_list.append({
                'id': u['id'],
                'nickname': u['nickname'],
                'coins': simulated_total_coins if is_me else u['coins'],
                'is_me': is_me
            })

        sim_sorted = sorted(sim_list, key=lambda x: x['coins'], reverse=True)
        
        sim_rank = None
        sim_me_idx = None
        for idx, u in enumerate(sim_sorted):
            if u['is_me']:
                sim_rank = idx + 1
                sim_me_idx = idx
                break

        rank_climb = curr_rank - sim_rank if curr_rank else 0
        above_user = sim_sorted[sim_me_idx - 1] if sim_me_idx > 0 else None
        below_user = sim_sorted[sim_me_idx + 1] if sim_me_idx < len(sim_sorted) - 1 else None

        if above_user:
            diff_above = above_user['coins'] - simulated_total_coins
            above_str = f"🔺 <b>위:</b> {above_user['nickname']} <span style='color:#ff9999;'>({diff_above:,} C 부족)</span>"
        else:
            above_str = "👑 <b>예상 랭킹 1위 달성!</b> (최상위)"

        if below_user:
            diff_below = simulated_total_coins - below_user['coins']
            below_str = f"🔻 <b>아래:</b> {below_user['nickname']} <span style='color:#00ffcc;'>({diff_below:,} C 제침)</span>"
        else:
            below_str = "🛡️ <b>최하위 라이벌 없음</b>"

        # 당첨금 & 랭킹 카드 (올인 시 넓은 글로우 + 빠른 색상전환)
        col_card1, col_card2 = st.columns(2)

        with col_card1:
            st.markdown(
                f"""
                <div class="payout-card {card_glow_class}">
                    <div style="font-size:0.8rem; color:#ffffff; font-weight:bold;">✨ 정답(오차 0점) 적중 시</div>
                    <div class="payout-amount">+{max_reward:,} C</div>
                    <div style="font-size:0.75rem; color:#ffd700; margin-top:4px;">(최대 100배 당첨)</div>
                </div>
                """,
                unsafe_allow_html=True
            )

        with col_card2:
            rank_climb_text = f"▲ {rank_climb}등 상승!" if rank_climb > 0 else "순위 유지"
            st.markdown(
                f"""
                <div class="rank-sim-card {card_glow_class}">
                    <div>
                        <div style="font-size:0.78rem; color:#aaa; font-weight:bold;">🏆 승리 시 예상 랭킹</div>
                        <div style="font-size:1.1rem; font-weight:900; color:#fff;">
                            {curr_rank}위 ➔ <span style="color:#ffd700;">{sim_rank}위</span>
                            <span class="rank-up-badge">({rank_climb_text})</span>
                        </div>
                    </div>
                    <div style="margin-top:6px;">
                        <div class="rival-row">{above_str}</div>
                        <div class="rival-row">{below_str}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)

        # 하단 버튼부 (올인 버튼 & 확정 버튼)
        col_b1, col_b2 = st.columns([1, 2])
        with col_b1:
            if st.button("💥 ALL-IN (올인)", use_container_width=True):
                st.session_state["bet_slider_key"] = current_coins
                st.rerun()

        with col_b2:
            if st.button("🎲 베팅 확정 & 게임 시작", use_container_width=True):
                st.session_state.game_1_bet = bet_val
                st.rerun()

        return


    # [2단계 & 3단계] 기사 선택
    title, article_text, url = get_game_news_selection("game_1")
    if not title:
        return

    # [4단계] 점수 예측 UI
    if "game_1_predicted_score" not in st.session_state:
        st.markdown("---")
        st.markdown("### 🎯 4단계: AI 유사도 점수 예측")
        st.caption("AI가 제목과 본문을 분석해 산출할 유사도 점수(00~99점)를 예측해 보세요!")

        @st.fragment
        def render_neon_digit_picker():
            if "tens_val" not in st.session_state:
                st.session_state.tens_val = 5
            if "ones_val" not in st.session_state:
                st.session_state.ones_val = 0

            st.markdown(
                """
                <style>
                .digit-display-container { display: flex; justify-content: center; align-items: center; margin: 15px 0; }
                .large-digit {
                    font-family: 'Press Start 2P', monospace, sans-serif;
                    font-size: 4.2rem; font-weight: 900; color: #00ffcc;
                    text-shadow: 0 0 15px #00ffcc, 0 0 25px #ff00ff;
                    background: #110022; border: 3.5px solid #8A2BE2; border-radius: 12px;
                    padding: 10px 20px; min-width: 85px; text-align: center;
                    box-shadow: 0 0 15px rgba(138, 43, 226, 0.6);
                }
                </style>
                """,
                unsafe_allow_html=True
            )

            _, col_tens, col_ones, _ = st.columns([1, 1.2, 1.2, 1])

            with col_tens:
                st.markdown("<p style='text-align:center; font-weight:bold; color:#a382de; margin-bottom:5px;'>십의 자리</p>", unsafe_allow_html=True)
                if st.button("▲", key="btn_tens_up", use_container_width=True):
                    st.session_state.tens_val = (st.session_state.tens_val + 1) % 10
                    st.rerun(scope="fragment")
                st.markdown(f"<div class='digit-display-container'><div class='large-digit'>{st.session_state.tens_val}</div></div>", unsafe_allow_html=True)
                if st.button("▼", key="btn_tens_down", use_container_width=True):
                    st.session_state.tens_val = (st.session_state.tens_val - 1) % 10
                    st.rerun(scope="fragment")

            with col_ones:
                st.markdown("<p style='text-align:center; font-weight:bold; color:#a382de; margin-bottom:5px;'>일의 자리</p>", unsafe_allow_html=True)
                if st.button("▲", key="btn_ones_up", use_container_width=True):
                    st.session_state.ones_val = (st.session_state.ones_val + 1) % 10
                    st.rerun(scope="fragment")
                st.markdown(f"<div class='digit-display-container'><div class='large-digit'>{st.session_state.ones_val}</div></div>", unsafe_allow_html=True)
                if st.button("▼", key="btn_ones_down", use_container_width=True):
                    st.session_state.ones_val = (st.session_state.ones_val - 1) % 10
                    st.rerun(scope="fragment")

            pred_score = st.session_state.tens_val * 10 + st.session_state.ones_val
            st.markdown(f"<h3 style='text-align:center; color:#fffb00; margin-top:15px;'>내 예측 점수: {pred_score:02d}점</h3>", unsafe_allow_html=True)

            if st.button("✅ 선택 완료 (예측 점수 제출)", use_container_width=True):
                st.session_state.game_1_predicted_score = pred_score
                st.rerun()

        render_neon_digit_picker()
        return

    # [5단계 & 6단계] AI 점수 측정 및 정산
    pred_score = st.session_state.game_1_predicted_score
    bet_coin = st.session_state.game_1_bet

    if "game_1_result" not in st.session_state:
        with st.spinner("🤖 AI가 유사도를 분석 중입니다..."):
            summary_text = summary(article_text)
            actual_score = similarity_check(summary_text, title)
            
            # diff 변수 선언 추가
            diff = abs(pred_score - actual_score)

            if diff == 0:
                reward = int(bet_coin * 100.0)
                is_win = True
                result_msg = f"🎉 대박 성공! (오차 {diff}점)"
            else:
                reward = -bet_coin
                is_win = False
                result_msg = f"💥 실패 (오차 {diff}점)"

            current_sid = st.session_state.current_user
            users_data = ws.get_all_records()
            user_row_idx = None
            user_info = None

            for idx, u in enumerate(users_data):
                sid = str(u.get('학번', '')).strip().replace('.0', '')
                if sid == current_sid:
                    user_row_idx = idx + 2
                    user_info = u
                    break

            current_coins = int(user_info.get('코인', 0)) if user_info else 0
            current_streak = int(user_info.get('연승', 0)) if user_info else 0

            if is_win:
                new_coins = current_coins + reward
                new_streak = current_streak + 1
            else:
                new_coins = max(0, current_coins + reward)
                new_streak = 0

            if user_row_idx:
                ws.update_cell(user_row_idx, 3, new_coins)
                ws.update_cell(user_row_idx, 4, new_streak)
                st.session_state.current_user_data['코인'] = new_coins
                st.session_state.current_user_data['연승'] = new_streak

            st.session_state.game_1_result = {
                "actual_score": actual_score,
                "diff": diff,
                "reward": reward,
                "is_win": is_win,
                "msg": result_msg,
                "new_coins": new_coins,
                "new_streak": new_streak
            }

    # 최종 결과 출력
    res = st.session_state.game_1_result
    st.markdown("---")
    st.markdown("### 🏆 6단계: 최종 결과")

    if res["is_win"]:
        st.balloons()
        st.success(f"{res['msg']} | 획득 코인: +{res['reward']:,} C")
    else:
        st.error(f"{res['msg']} | 차감 코인: {res['reward']:,} C")

    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1: st.metric("내 예측 점수", f"{pred_score:02d}점")
    with col_r2: st.metric("AI 측정 점수", f"{res['actual_score']:02d}점")
    with col_r3: st.metric("점수 오차", f"{res['diff']}점")

    st.markdown(
        f"""
        <div style="background:#110022; border:2px solid #8A2BE2; padding:15px; border-radius:10px; text-align:center; margin:15px 0;">
            <p style="color:#ffffff; margin:0; font-weight:bold;">현재 보유 코인: <span style="color:#00ffcc;">{res['new_coins']:,} C</span></p>
            <p style="color:#ffffff; margin:0; font-weight:bold;">현재 연승 기록: <span style="color:#ff00ff;">{res['new_streak']} 연승</span></p>
        </div>
        """,
        unsafe_allow_html=True
    )

    def reset_game_1_state():
        keys_to_clear = [
            "game_1_bet", "selected_news_game_1", "candidates_game_1", 
            "read_done_game_1", "game_1_predicted_score", "game_1_result",
            "tens_val", "ones_val"
        ]
        for k in keys_to_clear:
            if k in st.session_state:
                del st.session_state[k]

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 다시 도전하기", use_container_width=True):
            reset_game_1_state()
            st.rerun()

    with col_btn2:
        if st.button("⬅️ 메인으로 돌아가기", use_container_width=True):
            reset_game_1_state()
            change_page('main')
