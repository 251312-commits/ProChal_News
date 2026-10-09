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

    # [1단계] 베팅 금액 선택 (네온 UI, 코인 더미, 실시간 랭킹 변동 시뮬레이션)
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

        # [초고속 연산] 슬라이더 이동 시 반응속도를 위해 유저 리스트 메모리 캐싱
        if "ranking_users_cache" not in st.session_state:
            try:
                st.session_state.ranking_users_cache = ws.get_all_records()
            except Exception:
                st.session_state.ranking_users_cache = []

        users_data = st.session_state.ranking_users_cache

        # CSS 스타일 정의
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
                gap: 14px;
                min-height: 140px;
                padding: 20px 10px 15px 10px;
                background: radial-gradient(ellipse at bottom, rgba(255, 215, 0, 0.25) 0%, rgba(10, 0, 20, 0.85) 75%);
                border-radius: 16px;
                border: 1.5px dashed rgba(255, 215, 0, 0.5);
                box-shadow: inset 0 0 25px rgba(0, 0, 0, 0.9);
                margin: 15px 0;
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
            </style>
            """,
            unsafe_allow_html=True
        )

        # 상단 헤더 카드
        st.markdown(
            f"""
            <div class="bet-card-container">
                <div class="bet-header-title">🎰 STEP 1: BETTING PLACE</div>
                <div style="font-size: 1rem; color: #ffffff; font-weight: bold;">
                    현재 보유 코인: <span style="color:#ffd700;">🪙 {current_coins:,} C</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # 슬라이더로 베팅 금액 선택 (단위 50 C)
        bet_val = st.slider(
            "💰 베팅할 금액을 선택하세요",
            min_value=min_bet,
            max_value=current_coins,
            step=50,
            value=min(5000, current_coins)
        )

        # 동적 골드 동전 더미 비주얼 산출
        bet_ratio = (bet_val - min_bet) / max(1, (current_coins - min_bet)) if current_coins > min_bet else 1.0
        total_coins = int(3 + bet_ratio * 37)
        num_cols = min(5, max(1, (total_coins + 7) // 8))
        coins_per_col = total_coins // num_cols
        remainder = total_coins % num_cols

        cols_html = ""
        for c in range(num_cols):
            col_height = coins_per_col + (1 if c < remainder else 0)
            coins_in_col_html = ""
            for h in range(col_height):
                is_top = (h == col_height - 1)
                coin_class = "gold-coin-item top" if is_top else "gold-coin-item"
                coins_in_col_html += f'<div class="{coin_class}"></div>'
            cols_html += f'<div class="coin-stack-col">{coins_in_col_html}</div>'

        # 정답(오차 0점) 달성 시 획득 최고 금액 (100배)
        max_reward = bet_val * 100
        simulated_total_coins = current_coins + max_reward

        # ==================== [실시간 랭킹 연산 시작 (0.001초 미만 소요)] ====================
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

        # 1) 현재 순위 산출
        curr_sorted = sorted(processed_users, key=lambda x: x['coins'], reverse=True)
        curr_rank = None
        for idx, u in enumerate(curr_sorted):
            if u['id'] == current_sid or u['nickname'] == st.session_state.current_user_data.get('아이디', ''):
                curr_rank = idx + 1
                break
        if not curr_rank:
            curr_rank = len(curr_sorted) + 1

        # 2) 승리 시 예상 랭킹 산출
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

        # 순위 상승 수 계산
        rank_climb = curr_rank - sim_rank if curr_rank else 0

        # 바로 위 / 바로 아래 유저 정보 및 차이 계산
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
        # ==================== [실시간 랭킹 연산 끝] ====================

        # 코인 더미 시각화 출력
        st.markdown(
            f"""
            <div class="coin-pile-wrapper">
                {cols_html}
            </div>
            <div style="text-align:center; color:#ffd700; font-size:0.95rem; font-weight:800; margin-top:-5px; margin-bottom:15px;">
                현재 선택 칩: {bet_val:,} C
            </div>
            """,
            unsafe_allow_html=True
        )

        # 2컬럼 레이아웃: [당첨금 카드] | [랭킹 상승 시뮬레이션 카드]
        col_card1, col_card2 = st.columns(2)

        with col_card1:
            st.markdown(
                f"""
                <div class="payout-card">
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
                <div class="rank-sim-card">
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
                st.session_state.game_1_bet = current_coins
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
