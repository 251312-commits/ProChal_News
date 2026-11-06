# 업다운 (하) ½

import asyncio
import random
import streamlit as st
from modules.news_ai import summary, similarity_check
from modules.db_handler import init_gspread
from modules.ui_components import change_page
from games.shared.result import show_summary_before_score
from games.shared.news_flow import get_game_news_selection
from games.shared.loading import similarity_analysis_loading
from games.shared.betting import render_betting_ui
from games.shared.betting import check_user_coins_or_pop_bank
from views.ranking import fetch_ranking_data

ws = init_gspread()

def show_game_2():
    # [0단계] 튜토리얼 화면 (최초 1회 노출)
    if "game_2_tutorial_done" not in st.session_state:
        st.markdown(
            """
            <style>
            .tutorial-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px 5px 20px 5px;
            }
            .tutorial-nav-btn {
                color: #aaaaaa;
                font-size: 0.9rem;
                cursor: pointer;
                text-decoration: none;
            }
            .tutorial-title-section {
                text-align: center;
                margin-bottom: 25px;
            }
            .tutorial-game-badge {
                font-family: 'Press Start 2P', monospace;
                font-size: 0.85rem;
                color: #00e5ff;
                letter-spacing: 1px;
            }
            .tutorial-main-title {
                font-size: 1.8rem;
                font-weight: 900;
                color: #ffffff;
                margin-top: 4px;
            }
            .tutorial-sub-title {
                font-size: 0.95rem;
                color: #a0a0a0;
                margin-top: 2px;
            }
            
            .tutorial-grid {
                display: flex;
                flex-direction: column;
                gap: 20px;
                max-width: 500px;
                margin: 0 auto 30px auto;
                position: relative;
            }
            .tutorial-step-card {
                background: rgba(15, 23, 42, 0.75);
                border: 1px solid rgba(0, 229, 255, 0.3);
                border-radius: 16px;
                padding: 18px;
                text-align: center;
                position: relative;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
            }
            .step-num {
                font-family: 'Press Start 2P', monospace;
                font-size: 0.9rem;
                color: #00e5ff;
                font-style: italic;
                margin-bottom: 4px;
            }
            .step-title {
                font-size: 1.25rem;
                font-weight: 800;
                color: #ffffff;
                margin-bottom: 8px;
            }
            .step-icon {
                font-size: 2.8rem;
                margin: 8px 0;
            }
            .step-desc {
                font-size: 0.88rem;
                color: #cccccc;
                line-height: 1.4;
            }
            .arrow-down {
                text-align: center;
                font-size: 1.5rem;
                color: #00e5ff;
                margin: -10px 0;
                text-shadow: 0 0 8px #00e5ff;
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        col_nav1, col_nav2 = st.columns([1, 1])
        with col_nav1:
            if st.button("⬅️ 메인으로", key="tut_nav_main"):
                change_page('main')
                return
        with col_nav2:
            if st.button("건너뛰기 ➔", key="tut_nav_skip"):
                st.session_state.game_2_tutorial_done = True
                st.rerun()

        st.markdown(
            """
            <div class="tutorial-title-section">
                <div class="tutorial-game-badge">GAME 02</div>
                <div class="tutorial-main-title">뉴스 유사도 HIGH / LOW</div>
                <div class="tutorial-sub-title">기사 실제 유사도 점수는 기준 점수보다 높을까 낮을까?</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(
            """
            <div class="tutorial-grid">
                <div class="tutorial-step-card">
                    <div class="step-num">01</div>
                    <div class="step-title">코인 베팅</div>
                    <div class="step-icon">🪙</div>
                    <div class="step-desc">금액을 정해 베팅한다.<br><b>최소 1,000 C</b></div>
                </div>
                <div class="arrow-down">⤵</div>
                <div class="tutorial-step-card">
                    <div class="step-num">02</div>
                    <div class="step-title">기사 확인</div>
                    <div class="step-icon">🎰</div>
                    <div class="step-desc">뉴스 슬롯 룰렛으로 기사를 뽑는다.</div>
                </div>
                <div class="arrow-down">↩</div>
                <div class="tutorial-step-card">
                    <div class="step-num">03</div>
                    <div class="step-title">HIGH / LOW 선택</div>
                    <div class="step-icon">🎲</div>
                    <div class="step-desc">랜덤 생성된 <b>기준 점수(0~100점)</b>보다<br>실제 점수가 높은지(HIGH) 낮은지(LOW) 선택</div>
                </div>
                <div class="arrow-down">⤵</div>
                <div class="tutorial-step-card">
                    <div class="step-num">04</div>
                    <div class="step-title">결과 확인</div>
                    <div class="step-icon">🏅</div>
                    <div class="step-desc">적중 <b>+베팅액의 2배수 (실익 1배)</b><br>실패 <b>-베팅액</b></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button("베팅하러 가기", use_container_width=True, type="primary"):
            st.session_state.game_2_tutorial_done = True
            st.rerun()

        return

    st.title("🎮 게임 2: 뉴스 유사도 HIGH / LOW 게임")
    
    # [1단계] Shared wager screen: game 2 awards +1x net gain.
    if "game_2_bet" not in st.session_state:
        if not check_user_coins_or_pop_bank():
            return
        user = st.session_state.get("current_user_data") or {}
        try:
            users_data = fetch_ranking_data()
        except Exception:
            users_data = None
        confirmed_bet = render_betting_ui(
            current_coins=int(user.get("코인", 0)),
            users_data=users_data,
            current_sid=str(st.session_state.get("current_user", "")),
            current_nickname=str(user.get("아이디", "")),
            payout_multiplier=1.0,
            title="게임 2: 뉴스 유사도 HIGH / LOW",
            state_key="game_2",
        )
        if confirmed_bet is not None:
            st.session_state.game_2_bet = confirmed_bet
            st.rerun()
        return

    # Game 2's target-number card is intentionally game-specific.
    st.markdown("""
        <style>
        .target-num-card {
            background:linear-gradient(135deg,#0d1b2a,#1b263b);
            border:3px solid #00e5ff;border-radius:16px;padding:20px;
            text-align:center;box-shadow:0 0 20px rgba(0,229,255,.5);margin:20px 0;
        }
        .target-digit {
            font-family:'Press Start 2P',monospace,sans-serif;
            font-size:4rem;font-weight:900;color:#00ff88;
            text-shadow:0 0 15px #00ff88,0 0 25px #00e5ff;
        }
        </style>
    """, unsafe_allow_html=True)

    # [2단계] Reuse the roulette -> article reader flow, without a second slot.
    title, article_text, url = get_game_news_selection(
        "game_2", win_multiplier=1.0, immersive_reader=True
    )
    if not title:
        return

    # [3단계] HIGH / LOW 예측 선택
    if "game_2_target_num" not in st.session_state:
        st.session_state.game_2_target_num = random.randint(0, 100)

    target_num = st.session_state.game_2_target_num

    if "game_2_user_choice" not in st.session_state:
        st.markdown("---")
        st.markdown("### 🎯 HIGH / LOW 예측 선택")
        st.info(f"📌 선택된 기사 제목: **{title}**")

        with st.expander("📄 선택한 뉴스 본문 보기", expanded=False):
            st.write(article_text if article_text else title)

        st.markdown(
            f"""
            <div class="target-num-card">
                <div style="color:#ffffff; font-weight:bold; font-size:1.1rem; margin-bottom:8px;">🎲 뽑힌 기준 점수</div>
                <div class="target-digit">{target_num}점</div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.write("소수 둘째 자리까지 표시한 유사도 점수가 기준 점수 이상일까요, 미만일까요?")

        col_high, col_low = st.columns(2)
        with col_high:
            if st.button(f"⬆️ HIGH (이상: ≥ {target_num}점)", use_container_width=True):
                st.session_state.game_2_user_choice = "HIGH"
                st.rerun()

        with col_low:
            if st.button(f"⬇️ LOW (미만: < {target_num}점)", use_container_width=True):
                st.session_state.game_2_user_choice = "LOW"
                st.rerun()

        return

    # [4단계] AI 판단 및 결과 계산
    bet_coin = st.session_state.game_2_bet
    user_choice = st.session_state.game_2_user_choice

    if "game_2_result" not in st.session_state:
        with similarity_analysis_loading():
            text_for_summary = article_text if (article_text and article_text.strip()) else title
            summary_text = asyncio.run(summary(text_for_summary))
            
            if not summary_text:
                summary_text = title

            score_details = similarity_check(summary_text, title)
            actual_score = score_details["score"]

            if user_choice == "HIGH":
                is_win = (actual_score >= target_num)
            else:
                is_win = (actual_score < target_num)

            if is_win:
                reward = bet_coin
                result_msg = f"🎉 예측 성공! (실제 유사도: {actual_score:.2f}점)"
            else:
                reward = -bet_coin
                result_msg = f"💥 예측 실패! (실제 유사도: {actual_score:.2f}점)"

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

            st.session_state.game_2_result = {
                "title": title,
                "summary": summary_text,
                "actual_score": actual_score,
                "score_details": score_details,
                "target_num": target_num,
                "reward": reward,
                "is_win": is_win,
                "msg": result_msg,
                "new_coins": new_coins,
                "new_streak": new_streak
            }

    # [5단계] 최종 결과 화면
    res = st.session_state.game_2_result
    show_summary_before_score(
        res.get("summary", ""), "game_2_summary_revealed",
        title=res.get("title", title), score=res["actual_score"],
        details=res.get("score_details"),
    )
    st.markdown("---")
    st.markdown("### 🏆 최종 결과")

    if res["is_win"]:
        st.balloons()
        st.success(f"{res['msg']} | 획득 코인: +{res['reward']:,} C")
    else:
        st.error(f"{res['msg']} | 차감 코인: -{abs(res['reward']):,} C")

    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1: st.metric("기준 점수", f"{res['target_num']}점")
    with col_r2: st.metric("내 선택", "이상 (≥)" if user_choice == "HIGH" else "미만 (<)")
    score_format = ".2f" if "score_hundredths" in (res.get("score_details") or {}) else ".0f"
    with col_r3: st.metric("AI 실제 유사도", f"{res['actual_score']:{score_format}}점")

    st.markdown(
        f"""
        <div style="background:#001122; border:2px solid #00e5ff; padding:15px; border-radius:10px; text-align:center; margin:15px 0;">
            <p style="color:#ffffff; margin:0; font-weight:bold;">현재 보유 코인: <span style="color:#00ff88;">{res['new_coins']:,} C</span></p>
            <p style="color:#ffffff; margin:0; font-weight:bold;">현재 연승 기록: <span style="color:#00e5ff;">{res['new_streak']} 연승</span></p>
        </div>
        """,
        unsafe_allow_html=True
    )

    def reset_game_2_state():
        keys_to_clear = [
            "game_2_bet", "selected_news_game_2", "candidates_game_2", 
            "game_2_target_num", "game_2_user_choice", "game_2_result",
            "game_2_summary_revealed", "game_2_slot_round",
            "read_done_game_2", "game_2_reader_round", "game_2_direct_url_error"
        ]
        for k in keys_to_clear:
            if k in st.session_state:
                del st.session_state[k]

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔄 다시 도전하기", use_container_width=True):
            reset_game_2_state()
            st.rerun()

    with col_btn2:
        if st.button("⬅️ 메인으로 돌아가기", use_container_width=True):
            reset_game_2_state()
            change_page('main')
