# 업다운 (하) ½

import random
from decimal import Decimal, ROUND_HALF_UP
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


def get_decimal_digits(score):
    """유사도 점수의 정수 부분은 버리고, 소수점 이하 두 자리를 0~99 정수로 반환한다."""
    rounded_score = Decimal(str(score)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    fractional_part = rounded_score - int(rounded_score)
    return int(fractional_part * 100)


def show_game_2():
    # [0단계] 튜토리얼 화면 (최초 1회 노출)
    if "game_2_tutorial_done" not in st.session_state:
        # Game 1 튜토리얼 CSS의 레이아웃/반응형 규칙을 Game 2 전용 키로 적용
        st.markdown(
            """
            <style>
.stApp:has(.st-key-game2-guide) {
    background: #090a09 !important;
}
.stApp:has(.st-key-game2-guide) [data-testid="stHeader"] { display: none; }
.stApp:has(.st-key-game2-guide) .block-container {
    display: grid;
    align-content: center;
    min-height: 100svh;
    padding: max(6px, env(safe-area-inset-top)) max(14px, env(safe-area-inset-right))
             max(8px, env(safe-area-inset-bottom)) max(14px, env(safe-area-inset-left)) !important;
}
.stApp:has(.st-key-game2-guide) .block-container > [data-testid="stVerticalBlock"] { gap: 0; }
.st-key-game2-guide {
    --chalk: #f3f2e9;
    --sun: #ffda39;
    width: min(100%, 480px);
    margin-inline: auto;
    color: var(--chalk);
    font-family: system-ui, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
}
.st-key-game2-guide-nav {
    align-items: center;
    justify-content: space-between;
    flex-wrap: nowrap;
    border-bottom: 1px solid #ffffff29;
}
.st-key-game2-guide button {
    min-height: 44px;
    font-family: inherit;
    box-shadow: none !important;
}
.st-key-game2-guide-nav button {
    padding: 0 5px;
    border: 0 !important;
    background: transparent !important;
    color: #bcbdb6 !important;
}
.st-key-game2-guide-skip button { color: var(--chalk) !important; }
.st-key-game2-guide-skip button::after {
    content: '';
    width: 6px; height: 6px;
    border: solid var(--sun);
    border-width: 2px 2px 0 0;
    transform: rotate(45deg);
}
.st-key-game2-guide-start button {
    background: var(--sun) !important;
    border: 1px solid var(--sun) !important;
    border-radius: 12px;
    color: #19180f !important;
}
.st-key-game2-guide-start button:hover { background: #ffe674 !important; }
.st-key-game2-guide button:focus-visible { outline: 3px solid var(--chalk); outline-offset: 2px; }
.game2-guide-sheet { color: var(--chalk); }
.game2-guide-heading {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 2px 10px;
    padding: 12px 0 0;
}
.game2-guide-heading > span {
    color: var(--sun);
    font: 700 .68rem/1.35 ui-monospace, monospace;
    letter-spacing: .1em;
}
.game2-guide-heading h1, .game2-guide-sheet li h2 {
    margin: 0; padding: 0;
    text-align: left;
    color: var(--chalk) !important;
    text-shadow: none !important;
}
.game2-guide-heading h1 { font-size: clamp(20px, 5vw, 26px); line-height: 1.25; }
.game2-guide-heading p {
    flex-basis: 100%;
    margin: 0;
    font-size: 13px;
    line-height: 1.45;
    color: #c9cac3;
}
.game2-guide-sheet ol {
    position: relative;
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    grid-template-rows: repeat(5, minmax(0, 1fr));
    height: clamp(346px, calc(100svh - 166px - env(safe-area-inset-top) - env(safe-area-inset-bottom)), 610px);
    padding: 0;
    margin: 0 0 6px;
    list-style: none;
}
.game2-guide-sheet ol::before {
    content: '';
    position: absolute;
    inset: 0;
    pointer-events: none;
    background: center / 100% 100% no-repeat url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 400 500' preserveAspectRatio='none' fill='none' stroke='%23dbddd1' stroke-width='2.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M160 54 Q238 46 266 102 M252 97 L267 104 Q271 94 274 87 M245 228 Q205 223 158 264 M159 247 L155 267 L174 264 M186 354 Q211 385 253 377 M240 366 L257 376 L246 390'/%3E%3C/svg%3E");
}
.game2-guide-sheet li {
    z-index: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 3px;
    margin: 0; padding: 0;
    text-align: center;
}
.game2-guide-sheet li:nth-child(1) { grid-area: 1 / 1 / 3 / 2; }
.game2-guide-sheet li:nth-child(2) { grid-area: 2 / 2 / 4 / 3; }
.game2-guide-sheet li:nth-child(3) { grid-area: 3 / 1 / 5 / 2; }
.game2-guide-sheet li:nth-child(4) { grid-area: 4 / 2 / 6 / 3; }
.game2-guide-sheet li h2 {
    display: flex;
    align-items: baseline;
    gap: 6px;
    font-size: clamp(15px, 4.4vw, 21px);
    font-weight: 750;
    line-height: 1.2;
}
.game2-guide-sheet li h2 span {
    color: var(--sun);
    font: italic 700 .8em/1 Georgia, serif;
}
.game2-guide-sheet li img {
    display: block;
    width: 78%;
    height: clamp(47px, 12svh, 112px);
    object-fit: contain;
}
.game2-guide-sheet li p {
    margin: 0;
    color: #d9d9d1;
    font-size: clamp(12px, 3.25vw, 15px);
    line-height: 1.35;
    word-break: keep-all;
}
.game2-guide-sheet b { color: var(--sun); }

@media (orientation: landscape) and (max-height: 540px) {
    .st-key-game2-guide { width: min(100%, 760px); }
    .game2-guide-heading { gap: 6px 9px; padding-top: 5px; }
    .game2-guide-heading h1 { font-size: 19px; }
    .game2-guide-heading p { flex-basis: auto; font-size: 12px; }
    .game2-guide-sheet ol {
        height: clamp(156px, calc(100svh - 152px - env(safe-area-inset-top) - env(safe-area-inset-bottom)), 325px);
        margin-bottom: 4px;
    }
    .game2-guide-sheet li {
        display: grid;
        grid-template-columns: minmax(0, 28%) auto;
        grid-template-rows: auto auto;
        align-content: center;
        justify-content: center;
        gap: 1px 7px;
        text-align: left;
    }
    .game2-guide-sheet li img {
        grid-area: 1 / 1 / 3 / 2;
        width: 100%; height: clamp(42px, 15svh, 72px);
    }
    .game2-guide-sheet li h2 { grid-area: 1 / 2; font-size: 15px; }
    .game2-guide-sheet li p { grid-area: 2 / 2; font-size: 12px; }
}

            .game2-guide-sheet .game2-guide-icon {
                font-size: clamp(42px, 10svh, 76px);
                line-height: 1.1;
                margin: 3px 0 7px;
            }
            .game2-guide-sheet li p { max-width: 190px; }
            @media (orientation: landscape) and (max-height: 540px) {
                .game2-guide-sheet .game2-guide-icon {
                    font-size: clamp(34px, 11svh, 58px);
                    margin: 0;
                }
                .game2-guide-sheet li p { max-width: none; }
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        with st.container(key="game2-guide"):
            with st.container(key="game2-guide-nav"):
                nav_left, nav_right = st.columns([1, 1])
                with nav_left:
                    if st.button("메인으로", key="game2_tutorial_main"):
                        change_page("main")
                        return
                with nav_right:
                    with st.container(key="game2-guide-skip"):
                        if st.button("건너뛰기", key="game2_tutorial_skip"):
                            st.session_state.game_2_tutorial_done = True
                            st.rerun()

            st.markdown(
                """
                <section class="game2-guide-sheet">
                  <header class="game2-guide-heading">
                    <span>GAME 02</span>
                    <h1>소수점 HIGH / LOW</h1>
                    <p>AI 유사도의 정수 부분은 제외! 소수점 두 자리 숫자만 비교한다.</p>
                  </header>
                  <ol>
                    <li>
                      <h2><span>01</span> 코인 베팅</h2>
                      <div class="game2-guide-icon">🪙</div>
                      <p>플레이할 코인 금액을 정해 베팅한다.<br>최소 <b>1,000 C</b></p>
                    </li>
                    <li>
                      <h2><span>02</span> 기사 선택</h2>
                      <div class="game2-guide-icon">📰</div>
                      <p>룰렛을 돌려 기사를 선택한 뒤<br>뉴스 내용을 읽는다.</p>
                    </li>
                    <li>
                      <h2><span>03</span> 소수점 예측</h2>
                      <div class="game2-guide-icon">🎯</div>
                      <p>제시된 <b>0~99</b> 기준 숫자와<br>기사 유사도의 소수점 두 자리를 비교!<br><b>HIGH</b>(이상 ≥, 동점 포함) 또는 <b>LOW</b>(미만 &lt;)</p>
                    </li>
                    <li>
                      <h2><span>04</span> 결과 확인</h2>
                      <div class="game2-guide-icon">🏆</div>
                      <p>예: 87.04점이면 <b>04</b>만 비교한다.<br>적중 <b>+베팅액의 2배</b><br>실패 <b>−베팅액</b></p>
                    </li>
                  </ol>
                </section>
                """,
                unsafe_allow_html=True,
            )

            with st.container(key="game2-guide-start"):
                if st.button(
                    "베팅하러 가기",
                    use_container_width=True,
                    type="primary",
                    key="game_2_tutorial_start",
                ):
                    st.session_state.game_2_tutorial_done = True
                    st.rerun()

        return

    st.title("🎮 게임 2: 소수점 HIGH / LOW 게임")
    
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
            title="게임 2: 소수점 HIGH / LOW",
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
            border:3px solid #ffda39;border-radius:16px;padding:20px;
            text-align:center;box-shadow:0 0 20px rgba(255,218,57,.22);margin:20px 0;
        }
        .target-digit {
            font-family:ui-monospace,monospace;
            font-size:clamp(2.8rem,12vw,4rem);font-weight:900;color:#ffda39;
            letter-spacing:.08em;
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
    if (
        "game_2_target_num" not in st.session_state
        or not isinstance(st.session_state.game_2_target_num, int)
        or not 0 <= st.session_state.game_2_target_num <= 99
    ):
        st.session_state.game_2_target_num = random.randint(0, 99)

    target_num = st.session_state.game_2_target_num

    if "game_2_user_choice" not in st.session_state:
        st.markdown("---")
        st.markdown("### 🎯 소수점 두 자리 HIGH / LOW 예측")
        st.caption(f"선택한 기사 · {title}")
        st.info("AI 유사도 점수의 정수 부분은 무시하고, 소수점 이하 두 자리(YY)만 비교해! 기준 숫자와 같으면 HIGH로 판정해.")

        with st.expander("📄 선택한 뉴스 본문 보기", expanded=False):
            st.write(article_text if article_text else title)

        st.markdown(
            f"""
            <div class="target-num-card">
                <div style="color:#ffffff; font-weight:bold; font-size:1.1rem; margin-bottom:8px;">🎲 소수점 비교 기준 숫자</div>
                <div class="target-digit">{target_num:02d}</div>
                <div style="color:#d9d9d1; font-size:.95rem; margin-top:8px;">예: 87.04점 → 04만 비교</div>
            </div>
            """,
            unsafe_allow_html=True
        )


        col_high, col_low = st.columns(2)
        with col_high:
            if st.button(f"⬆️ HIGH (소수점 두 자리 ≥ {target_num:02d})", use_container_width=True):
                st.session_state.game_2_user_choice = "HIGH"
                st.rerun()

        with col_low:
            if st.button(f"⬇️ LOW (소수점 두 자리 < {target_num:02d})", use_container_width=True):
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
            actual_decimal_digits = get_decimal_digits(actual_score)

            # 정수 부분은 비교에서 제외한다. 동점은 기존 규칙대로 HIGH에 포함한다.
            if user_choice == "HIGH":
                is_win = (actual_decimal_digits >= target_num)
            else:
                is_win = (actual_decimal_digits < target_num)

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
                "actual_decimal_digits": actual_decimal_digits,
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
    with col_r1: st.metric("소수점 기준 숫자", f"{res['target_num']:02d}")
    with col_r2: st.metric("내 선택", "소수점 ≥ 기준" if user_choice == "HIGH" else "소수점 < 기준")
    with col_r3: st.metric("AI 소수점 결과", f"{res['actual_decimal_digits']:02d}")
    st.caption(
        f"AI 전체 유사도 {res['actual_score']:.2f}점 → "
        f"소수점 두 자리 {res['actual_decimal_digits']:02d}만 비교 "
        f"(기준 {res['target_num']:02d})"
    )

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
