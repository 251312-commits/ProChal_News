import streamlit as st
from modules.news_ai import summary, similarity_check
from modules.db_handler import init_gspread, init_news_sheet
from modules.ui_components import change_page
from games.common import get_game_news_selection, check_user_coins_or_pop_bank

ws = init_gspread()
ws_news = init_news_sheet()

# 정의된 함수: show_game_1

def show_game_1():
    st.title("🎮 게임 1: 뉴스 유사도 예측 게임")

    # [1단계] 베팅 금액 선택 (이미지 레퍼런스 UI 완전 동기화)
    if "game_1_bet" not in st.session_state:
        current_coins = int(st.session_state.current_user_data.get('코인', 1250))
        current_sid = str(st.session_state.get('current_user', '')).strip().replace('.0', '')
        min_bet = 100
        max_bet = max(min_bet, current_coins)
        
        # 코인 부족 예외 처리
        if current_coins < min_bet:
            st.error(f"⚠️ 베팅을 위한 코인이 부족합니다! (최소 베팅금: {min_bet:,} C / 보유: {current_coins:,} C)")
            if st.button("⬅️ 메인으로 돌아가기", use_container_width=True):
                change_page('main')
            return

        # 랭킹 데이터 캐싱
        if "ranking_users_cache" not in st.session_state:
            try:
                st.session_state.ranking_users_cache = ws.get_all_records()
            except Exception:
                st.session_state.ranking_users_cache = []
        users_data = st.session_state.ranking_users_cache

        # 세션 슬라이더 기본값 세팅 (보유 코인의 절반)
        if "bet_amount_state" not in st.session_state:
            st.session_state.bet_amount_state = min(500, max_bet)

        # 이미지 디자인 반영 CSS (퍼플 글래스모피즘 & 3D 카지노 테마)
        st.markdown(
            """
            <style>
            .casino-app-frame {
                background: radial-gradient(circle at 50% 20%, #2e0854 0%, #120224 55%, #06000d 100%);
                border-radius: 28px;
                padding: 20px 16px;
                color: #ffffff;
                box-shadow: 0 0 35px rgba(138, 43, 226, 0.4);
                margin-bottom: 20px;
            }
            .top-nav-bar {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
            }
            .back-arrow {
                font-size: 1.2rem;
                color: #ffffff;
                cursor: pointer;
            }
            .coin-pill {
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
            }
            .bet-tag {
                color: #c084fc;
                font-size: 0.75rem;
                letter-spacing: 3px;
                text-align: center;
                font-weight: 900;
                margin-top: 4px;
            }
            .main-title {
                text-align: center;
                font-size: 1.65rem;
                font-weight: 900;
                color: #ffffff;
                margin: 4px 0 2px 0;
                text-shadow: 0 0 15px rgba(255, 255, 255, 0.6);
            }
            .sub-title {
                text-align: center;
                font-size: 0.85rem;
                color: #b39ddb;
                margin-bottom: 15px;
            }
            
            /* 중앙 3D 뉴스 카드 & 동전 단상 visual */
            .stage-wrapper {
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                margin: 15px 0 20px 0;
                position: relative;
            }
            .news-card-3d {
                width: 220px;
                height: 120px;
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
            }
            .question-mark {
                font-size: 3rem;
                font-weight: 900;
                color: #f5d0fe;
                text-shadow: 0 0 20px #e879f9;
            }
            .pedestal-3d {
                width: 200px;
                height: 70px;
                background: radial-gradient(ellipse at top, #7e22ce 0%, #3b0764 70%, #1e0338 100%);
                border-radius: 50%;
                border: 3px solid #a855f7;
                box-shadow: 0 10px 30px rgba(0,0,0,0.9), 0 0 20px rgba(168, 85, 247, 0.6);
                display: flex;
                align-items: center;
                justify-content: center;
                z-index: 1;
            }

            /* 슬라이더 제어 박스 */
            .slider-card-box {
                background: rgba(18, 6, 36, 0.75);
                border: 1.5px solid #a855f7;
                border-radius: 22px;
                padding: 14px 16px 8px 16px;
                box-shadow: 0 0 20px rgba(168, 85, 247, 0.3);
                margin-bottom: 12px;
            }
            .bet-amount-title {
                text-align: center;
                font-size: 1.8rem;
                font-weight: 900;
                color: #ffffff;
                margin-bottom: 6px;
                text-shadow: 0 0 10px rgba(255, 255, 255, 0.8);
            }

            /* 하단 통계 카드 2분할 */
            .stat-card-item {
                background: rgba(22, 8, 44, 0.75);
                border: 1.5px solid #7e22ce;
                border-radius: 18px;
                padding: 12px 14px;
                min-height: 95px;
                display: flex;
                flex-direction: column;
                justify-content: space-between;
                box-shadow: inset 0 0 12px rgba(168, 85, 247, 0.15);
            }
            .stat-card-title {
                font-size: 0.75rem;
                color: #c084fc;
                font-weight: 700;
            }
            .stat-card-value {
                font-size: 1.45rem;
                font-weight: 900;
                color: #ffffff;
            }
            .multiplier-tag {
                background: rgba(168, 85, 247, 0.25);
                border: 1px solid #c084fc;
                border-radius: 10px;
                padding: 2px 8px;
                font-size: 0.7rem;
                color: #e9d5ff;
                width: fit-content;
            }
            .rank-up-badge-green {
                color: #4ade80;
                font-weight: 900;
                font-size: 0.88rem;
                float: right;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        # 1. 상단 바 & 제목
        st.markdown(
            f"""
            <div class="casino-app-frame">
                <div class="top-nav-bar">
                    <span class="back-arrow">❮</span>
                    <div class="coin-pill">
                        <span style="color:#ffd700;">🪙</span>
                        <span>{current_coins:,}</span>
                        <span style="color:#a855f7; margin-left:2px;">+</span>
                    </div>
                </div>
                <div class="bet-tag">👑 BET</div>
                <div class="main-title">얼마를 걸까요?</div>
                <div class="sub-title">베팅하면 뉴스가 공개됩니다</div>
                
                <!-- 2. 중앙 3D 카드 & 동전 단상 무대 -->
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

        # 3. 슬라이더 & (- / +) 버튼 구역
        bet_val = st.session_state.bet_amount_state

        st.markdown(f'<div class="bet-amount-title">🪙 {bet_val:,}</div>', unsafe_allow_html=True)
        
        col_m, col_s, col_p = st.columns([1, 4, 1])
        with col_m:
            if st.button("➖", use_container_width=True, key="btn_minus"):
                st.session_state.bet_amount_state = max(min_bet, bet_val - 50)
                st.rerun()

        with col_s:
            st.session_state.bet_amount_state = st.slider(
                "베팅 금액 선택",
                min_value=min_bet,
                max_value=max_bet,
                step=50,
                value=st.session_state.bet_amount_state,
                label_visibility="collapsed",
                key="main_bet_slider"
            )

        with col_p:
            if st.button("➕", use_container_width=True, key="btn_plus"):
                st.session_state.bet_amount_state = min(max_bet, bet_val + 50)
                st.rerun()

        st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)

        # 4. 실시간 예상 당첨액 및 랭킹 계산
        expected_payout = bet_val * 2  # 정답 오차 0점 기준 (2배~100배 가변 설정 가능)
        simulated_total_coins = current_coins + expected_payout

        # 랭킹 시뮬레이션 연산
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
        curr_rank = next((i + 1 for i, u in enumerate(curr_sorted) if u['id'] == current_sid or u['nickname'] == st.session_state.current_user_data.get('아이디', '')), len(curr_sorted) + 1)

        sim_list = []
        for u in processed_users:
            is_me = (u['id'] == current_sid or u['nickname'] == st.session_state.current_user_data.get('아이디', ''))
            sim_list.append({
                'coins': simulated_total_coins if is_me else u['coins'],
                'is_me': is_me
            })
        sim_sorted = sorted(sim_list, key=lambda x: x['coins'], reverse=True)
        sim_rank = next((i + 1 for i, u in enumerate(sim_sorted) if u['is_me']), curr_rank)
        rank_climb = max(0, curr_rank - sim_rank)

        # 5. 하단 2분할 통계 카드 출력
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

        # 6. 최하단 번개 퍼플 글로우 베팅하기 버튼
        if st.button(f"⚡ {bet_val:,} 베팅하기", use_container_width=True, type="primary"):
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
