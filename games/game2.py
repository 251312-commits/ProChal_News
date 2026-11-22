# 업다운 (하) ½

import random
import streamlit as st
from modules.news_ai import summary, similarity_check
from modules.ui_components import change_page
from games.shared.result import show_summary_before_score
from games.shared.news_flow import get_game_news_selection
from games.shared.loading import similarity_analysis_loading
from games.shared.round_analysis import analyze_round_once
from games.shared.interest import apply_end_of_turn_interest
from modules.transactions import BalanceChanged, TransactionError, settle_game_round, update_session_balances
from games.shared.betting import render_betting_ui
from games.shared.betting import check_user_coins_or_pop_bank
from views.ranking import fetch_ranking_data

GAME_2_WIN_MULTIPLIER = 2.0


def show_game_2():
    # [0단계] 튜토리얼 화면 (최초 1회 노출)
    if "game_2_tutorial_done" not in st.session_state:
        st.markdown(
            """
            <style>
            /* Game 2 tutorial: 참고 이미지처럼 검은 배경 + 노란색 포인트 */
            .g2-tutorial-wrap {
                max-width: 620px;
                margin: 0 auto;
                color: #f5f3eb;
                padding: 2px 4px 10px 4px;
            }
            .g2-tutorial-nav {
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 1px solid rgba(255,255,255,.18);
                padding: 2px 0 14px 0;
                margin-bottom: 18px;
                color: #bdbdb8;
                font-size: .92rem;
            }
            .g2-tutorial-heading { margin: 0 0 24px 0; }
            .g2-game-label {
                color: #ffda35;
                font-family: monospace;
                font-size: .82rem;
                font-weight: 900;
                letter-spacing: 1.5px;
                margin-bottom: 5px;
            }
            .g2-game-title {
                color: #f7f5ed;
                font-size: clamp(1.45rem, 4vw, 1.85rem);
                line-height: 1.25;
                font-weight: 900;
                letter-spacing: -.7px;
            }
            .g2-game-subtitle {
                color: #aaa9a3;
                font-size: .93rem;
                margin-top: 5px;
            }
            .g2-flow {
                display: grid;
                grid-template-columns: 1fr 1fr;
                grid-template-rows: auto auto auto auto;
                column-gap: 24px;
                row-gap: 8px;
                align-items: center;
                max-width: 560px;
                margin: 0 auto 28px auto;
            }
            .g2-step {
                min-width: 0;
                text-align: center;
                padding: 4px 2px;
            }
            .g2-step-1 { grid-column: 1; grid-row: 1; }
            .g2-step-2 { grid-column: 2; grid-row: 2; }
            .g2-step-3 { grid-column: 1; grid-row: 3; }
            .g2-step-4 { grid-column: 2; grid-row: 4; }
            .g2-step-heading {
                display: flex;
                justify-content: center;
                align-items: baseline;
                gap: 8px;
                margin-bottom: 7px;
                white-space: nowrap;
            }
            .g2-step-num {
                color: #ffda35;
                font-family: Georgia, serif;
                font-size: 1.15rem;
                font-weight: 900;
                font-style: italic;
            }
            .g2-step-title {
                color: #f5f3eb;
                font-size: 1.22rem;
                font-weight: 850;
            }
            .g2-step-icon {
                font-size: 3.7rem;
                line-height: 1.25;
                margin: 3px 0 7px 0;
                filter: saturate(1.08);
            }
            .g2-step-desc {
                color: #c3c1ba;
                font-size: .88rem;
                line-height: 1.55;
                word-break: keep-all;
            }
            .g2-step-desc strong { color: #ffda35; font-weight: 850; }
            .g2-arrow {
                color: #d9d9d1;
                font-size: 3rem;
                line-height: 1;
                text-align: center;
                opacity: .95;
                align-self: center;
            }
            .g2-arrow-12 { grid-column: 2; grid-row: 1; transform: rotate(18deg); }
            .g2-arrow-23 { grid-column: 1; grid-row: 2; transform: rotate(155deg); }
            .g2-arrow-34 { grid-column: 2; grid-row: 3; transform: rotate(18deg); }
            @media (max-width: 520px) {
                .g2-flow {
                    grid-template-columns: 1fr;
                    grid-template-rows: auto;
                    row-gap: 4px;
                    max-width: 340px;
                }
                .g2-step-1, .g2-step-2, .g2-step-3, .g2-step-4 {
                    grid-column: 1;
                    grid-row: auto;
                }
                .g2-arrow-12, .g2-arrow-23, .g2-arrow-34 {
                    grid-column: 1;
                    grid-row: auto;
                    transform: rotate(90deg);
                    font-size: 2rem;
                    margin: -2px 0;
                }
                .g2-step-icon { font-size: 3.2rem; }
            }
            </style>
            """,
            unsafe_allow_html=True
        )

        col_nav1, col_nav2 = st.columns([1, 1])
        with col_nav1:
            if st.button("메인으로", key="tut_nav_main"):
                change_page('main')
                return
        with col_nav2:
            if st.button("건너뛰기 ❯", key="tut_nav_skip"):
                st.session_state.game_2_tutorial_done = True
                st.rerun()

        st.markdown(
            """
            <div class="g2-tutorial-wrap">
              <div class="g2-tutorial-heading">
                <div class="g2-game-label">GAME 02</div>
                <div class="g2-game-title">뉴스 유사도 HIGH / LOW</div>
                <div class="g2-game-subtitle">AI가 분석한 뉴스 유사도, 기준 점수보다 높을까 낮을까?</div>
              </div>
              <div class="g2-flow">
                <div class="g2-step g2-step-1">
                  <div class="g2-step-heading"><span class="g2-step-num">01</span><span class="g2-step-title">코인 베팅</span></div>
                  <div class="g2-step-icon">🪙</div>
                  <div class="g2-step-desc">플레이할 코인 금액을 정한다.<br>최소 <strong>1,000 C</strong></div>
                </div>
                <div class="g2-arrow g2-arrow-12">⤵</div>
                <div class="g2-step g2-step-2">
                  <div class="g2-step-heading"><span class="g2-step-num">02</span><span class="g2-step-title">기사 선택</span></div>
                  <div class="g2-step-icon">📰</div>
                  <div class="g2-step-desc">룰렛을 돌려 기사를 선택하고<br>뉴스 내용을 읽는다.</div>
                </div>
                <div class="g2-arrow g2-arrow-23">⤵</div>
                <div class="g2-step g2-step-3">
                  <div class="g2-step-heading"><span class="g2-step-num">03</span><span class="g2-step-title">HIGH / LOW 예측</span></div>
                  <div class="g2-step-icon">🎯</div>
                  <div class="g2-step-desc">랜덤으로 정해진 기준 점수를 확인하고<br><strong>HIGH</strong> (기준 이상) 또는 <strong>LOW</strong> (기준 미만)를 선택한다.</div>
                </div>
                <div class="g2-arrow g2-arrow-34">⤵</div>
                <div class="g2-step g2-step-4">
                  <div class="g2-step-heading"><span class="g2-step-num">04</span><span class="g2-step-title">결과 확인</span></div>
                  <div class="g2-step-icon">🏆</div>
                  <div class="g2-step-desc">AI가 계산한 실제 유사도와 비교한다.<br>적중 <strong>+베팅액의 2배</strong><br>실패 <strong>−베팅액</strong></div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button("베팅하러 가기", use_container_width=True, type="primary", key="game_2_tutorial_start"):
            st.session_state.game_2_tutorial_done = True
            st.rerun()

        return

    st.title("🎮 게임 2: 뉴스 유사도 HIGH / LOW 게임")
    
    # [1단계] Shared wager screen: game 2 awards +2x net gain.
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
            payout_multiplier=GAME_2_WIN_MULTIPLIER,
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
        "game_2", win_multiplier=GAME_2_WIN_MULTIPLIER
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
        st.caption(f"선택한 기사 · {title}")

        with st.expander("📄 선택한 뉴스 본문 보기", expanded=False):
            st.write(article_text if article_text else title)

        st.markdown(
            f"""
            <div class="target-num-card">
                <div style="color:#ffffff; font-weight:bold; font-size:1.1rem; margin-bottom:8px;">🎲 기준 점수</div>
                <div class="target-digit">{target_num}점</div>
            </div>
            """,
            unsafe_allow_html=True
        )


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
            try:
                summary_text, score_details = analyze_round_once(
                    st.session_state, "game_2", title=title, article_text=text_for_summary,
                    summarize=summary, similarity=similarity_check,
                    fallback_to_title=True,
                )
            except (RuntimeError, ValueError, TypeError, KeyError) as exc:
                st.error(f"뉴스 유사도를 계산하지 못했습니다: {exc}")
                return
            actual_score = score_details["score"]

            if user_choice == "HIGH":
                is_win = (actual_score >= target_num)
            else:
                is_win = (actual_score < target_num)

            if is_win:
                reward = int(bet_coin * GAME_2_WIN_MULTIPLIER)
                result_msg = "예측 성공"
            else:
                reward = -bet_coin
                result_msg = "예측 실패"

            try:
                settled = settle_game_round(
                    "game_2", int(bet_coin), is_win,
                    badge_evidence={"choice": user_choice},
                )
            except BalanceChanged as changed:
                update_session_balances(changed.balances)
                st.error(str(changed))
                return
            except TransactionError as exc:
                st.error(str(exc))
                return
            reward = settled["reward"]
            new_coins = settled["new_coins"]
            new_streak = settled["new_streak"]

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

    # [5단계] 결과 공개 직전 턴 종료 이자 부과
    res = st.session_state.game_2_result
    if not apply_end_of_turn_interest("game_2"):
        return
    show_summary_before_score(
        res.get("summary", ""), "game_2_summary_revealed",
        title=res.get("title", title), score=res["actual_score"],
        details=res.get("score_details"),
    )
    st.markdown("---")
    st.markdown("### 🏆 최종 결과")

    if res["is_win"]:
        st.balloons()
        st.success(f"{res['msg']} · +{res['reward']:,} C")
    else:
        st.error(f"{res['msg']} · −{abs(res['reward']):,} C")

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
            "game_2_target_num", "game_2_user_choice", "game_2_result", "game_2_round_id",
            "game_2_summary_revealed", "game_2_analysis_checkpoint", "game_2_slot_round",
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
