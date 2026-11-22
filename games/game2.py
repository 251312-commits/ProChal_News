# 업다운 (하) ½

import random
from html import escape
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



def _reset_game_2_state():
    """Clear only Game 2 round state; shared account and interest state stay intact."""
    keys_to_clear = (
        "game_2_bet",
        "selected_news_game_2",
        "candidates_game_2",
        "game_2_target_num",
        "game_2_user_choice",
        "game_2_result",
        "game_2_round_id",
        "game_2_summary_revealed",
        "game_2_analysis_checkpoint",
        "game_2_slot_round",
        "read_done_game_2",
        "game_2_reader_round",
        "game_2_direct_url_error",
        "game_2_tutorial_done",
    )
    for key in keys_to_clear:
        st.session_state.pop(key, None)


def _render_game_2_tutorial():
    """Compact tutorial styled to match the purple-and-gold casino UI."""
    st.html("""
        <style>
        [data-testid="stApp"]:has(.st-key-game2-tutorial) {
            background:
                radial-gradient(ellipse at 50% 0%, rgba(119, 38, 173, .30), transparent 48%),
                linear-gradient(160deg, #100719 0%, #1b0b2b 52%, #0c0713 100%) !important;
        }
        [data-testid="stApp"]:has(.st-key-game2-tutorial) [data-testid="stHeader"] {
            background: transparent;
        }
        .st-key-game2-tutorial {
            max-width: 820px;
            margin: 0 auto;
            color: #f7f0ff;
        }
        .st-key-game2-tutorial .g2-tutorial-nav {
            display:flex; justify-content:space-between; align-items:center;
            border-bottom:1px solid rgba(226,190,255,.18);
            padding: 2px 0 12px; margin-bottom: 24px;
            color:#d7c6e9; font-size:.9rem;
        }
        .st-key-game2-tutorial .g2-tutorial-kicker {
            color:#e7bd69; font-size:.75rem; font-weight:800;
            letter-spacing:.18em; text-transform:uppercase;
        }
        .st-key-game2-tutorial .g2-tutorial-title {
            margin:7px 0 6px; color:#fff7e8; font-size:clamp(2rem,5vw,3.2rem);
            font-weight:900; letter-spacing:-.045em; line-height:1.1;
        }
        .st-key-game2-tutorial .g2-tutorial-sub {
            color:#d8c8e8; font-size:1rem; line-height:1.6;
            margin:0 0 24px;
        }
        .st-key-game2-tutorial .g2-steps {
            display:grid; grid-template-columns:repeat(2,minmax(0,1fr));
            gap:14px; margin:0 0 22px;
        }
        .st-key-game2-tutorial .g2-step {
            min-height:150px; padding:18px;
            border:1px solid rgba(213,175,245,.22);
            border-radius:18px;
            background:linear-gradient(145deg,rgba(75,35,105,.50),rgba(26,14,39,.92));
            box-shadow:inset 0 1px 0 rgba(255,255,255,.06),0 10px 28px rgba(0,0,0,.18);
        }
        .st-key-game2-tutorial .g2-step-num {
            color:#e8bd69; font:800 .78rem/1 ui-monospace,monospace;
            letter-spacing:.12em;
        }
        .st-key-game2-tutorial .g2-step-icon { font-size:1.8rem; margin:12px 0 6px; }
        .st-key-game2-tutorial .g2-step-title {
            color:#fff4df; font-size:1.05rem; font-weight:800; margin-bottom:5px;
        }
        .st-key-game2-tutorial .g2-step-copy {
            color:#d9cde5; font-size:.9rem; line-height:1.55;
        }
        .st-key-game2-tutorial .g2-step-copy b { color:#f0c76e; }
        .st-key-game2-tutorial .stButton > button {
            min-height:44px;border-radius:12px !important;
            border:1px solid rgba(233,189,101,.55) !important;
            background:linear-gradient(145deg,#603583,#35184f) !important;
            color:#fff4df !important;font-weight:800 !important;
        }
        .st-key-game2-tutorial .stButton > button:hover {
            border-color:#f5d995 !important;
            background:linear-gradient(145deg,#7848a0,#49245f) !important;
        }
        .st-key-game2-tutorial .stButton button[kind="primary"] {
            background:linear-gradient(145deg,#eac16d,#a97931) !important;
            color:#24132f !important;border-color:#f3d48e !important;
        }
        .st-key-game2-tutorial-continue [data-testid="stButton"] {
            display:flex;
            justify-content:flex-end;
            width:100%;
        }
        .st-key-game2-tutorial-continue [data-testid="stButton"] > button {
            width:auto !important;
            min-width:190px;
            max-width:100%;
            padding-left:28px !important;
            padding-right:28px !important;
        }
        @media(max-width:600px) {
            .st-key-game2-tutorial-continue [data-testid="stButton"] > button {
                min-width:164px;
            }
        }
        @media(max-width:600px) {
            .st-key-game2-tutorial .g2-steps { gap:9px; }
            .st-key-game2-tutorial .g2-step { min-height:164px; padding:13px; }
            .st-key-game2-tutorial .g2-step-copy { font-size:.82rem; }
        }
        </style>
    """)
    with st.container(key="game2-tutorial"):
        left, right = st.columns([1, 1])
        with left:
            if st.button("‹ 메인으로", key="game2_tutorial_back"):
                change_page("main")
                return
        with right:
            if st.button("건너뛰기 ›", key="game2_tutorial_skip"):
                st.session_state.game_2_tutorial_done = True
                st.rerun()

        st.html("""
            <section aria-label="게임 진행 방법">
                <div class="g2-tutorial-kicker">HOW TO PLAY</div>
                <h1 class="g2-tutorial-title">하이 앤 로우</h1>
                <p class="g2-tutorial-sub">
                    뉴스 한 편을 읽고 AI가 분석한 유사도 점수를 바탕으로
                    <b>하이(High) 또는 로우(Low)</b>를 예측하는 게임입니다.
                </p>
                <div class="g2-steps">
                    <article class="g2-step">
                        <div class="g2-step-num">01 / BET</div>
                        <div class="g2-step-icon">🪙</div>
                        <div class="g2-step-title">코인 베팅</div>
                        <div class="g2-step-copy">원하는 금액을 정해 베팅합니다.<br>최소 <b>1,000 C</b></div>
                    </article>
                    <article class="g2-step">
                        <div class="g2-step-num">02 / NEWS</div>
                        <div class="g2-step-icon">🎰</div>
                        <div class="g2-step-title">기사 선택</div>
                        <div class="g2-step-copy">뉴스 룰렛에서 기사 한 편을 고르고 내용을 읽습니다.</div>
                    </article>
                    <article class="g2-step">
                        <div class="g2-step-num">03 / PICK</div>
                        <div class="g2-step-icon">🎯</div>
                        <div class="g2-step-title">HIGH 또는 LOW</div>
                        <div class="g2-step-copy">점수 <b>XX.YY</b>에서 정수 부분은 제외합니다. <b>YY</b>와 기준 숫자(00~99)를 비교합니다.</div>
                    </article>
                    <article class="g2-step">
                        <div class="g2-step-num">04 / RESULT</div>
                        <div class="g2-step-icon">🏆</div>
                        <div class="g2-step-title">결과 확인</div>
                        <div class="g2-step-copy">기준 이상이면 HIGH, 미만이면 LOW입니다. 적중 시 <b>베팅액의 2배</b>, 실패 시 베팅액이 차감됩니다.</div>
                    </article>
                </div>
            </section>
        """)
        with st.container(key="game2-tutorial-continue"):
            if st.button(
                "계속하기  ›",
                key="game2_tutorial_start",
                type="primary",
                use_container_width=False,
            ):
                st.session_state.game_2_tutorial_done = True
                st.rerun()


def _game_2_theme_css():
    """Purple casino theme shared by the wager, prediction and result stages."""
    st.html("""
        <style>
        [data-testid="stApp"]:has(.st-key-game2-main) {
            background:
                radial-gradient(ellipse at 50% -12%, rgba(132,48,194,.34), transparent 48%),
                radial-gradient(ellipse at 100% 45%, rgba(79,31,117,.18), transparent 38%),
                linear-gradient(155deg,#100719 0%,#170a25 48%,#0c0713 100%) !important;
            color:#f7f0ff;
        }
        [data-testid="stApp"]:has(.st-key-game2-main) [data-testid="stHeader"] {
            background:rgba(16,7,25,.76);
        }
        [data-testid="stApp"]:has(.st-key-game2-main) .block-container {
            max-width:920px; padding-top:1.4rem; padding-bottom:3rem;
        }
        .st-key-game2-main {
            --g2-gold:#e9bd65;
            --g2-gold-soft:#f5d995;
            --g2-ink:#180d24;
            --g2-panel:rgba(40,20,58,.82);
            --g2-line:rgba(215,174,245,.22);
            color:#f7f0ff;
        }
        .st-key-game2-main h1,.st-key-game2-main h2,.st-key-game2-main h3 {
            color:#fff7e8 !important; text-shadow:none !important;
            letter-spacing:-.035em;
        }
        .st-key-game2-main [data-testid="stMarkdownContainer"] p {
            color:#e0d4eb; line-height:1.62;
        }
        .st-key-game2-main [data-testid="stCaptionContainer"] {
            color:#c9b7dc; font-size:.88rem;
        }
        .st-key-game2-main [data-testid="stAlert"] {
            border:1px solid rgba(233,189,101,.34);
            border-radius:14px; background:rgba(57,35,67,.72);
            color:#fff3d9;
        }
        .st-key-game2-main [data-testid="stExpander"] {
            border:1px solid var(--g2-line); border-radius:14px;
            background:rgba(28,14,42,.62);
        }
        .st-key-game2-main [data-testid="stExpander"] summary {
            color:#f1e5ff;
        }
        .st-key-game2-main .g2-brand {
            display:flex; align-items:center; gap:16px;
            padding:8px 0 18px; margin-bottom:18px;
            border-bottom:1px solid rgba(233,189,101,.28);
        }
        .st-key-game2-main .g2-brand-emblem {
            width:66px;height:66px; flex:0 0 66px;
            display:grid;place-items:center;border-radius:19px;
            color:#f7d98e;font-size:2rem;
            background:linear-gradient(145deg,#583078,#251034);
            border:1px solid rgba(233,189,101,.66);
            box-shadow:inset 0 1px 0 rgba(255,255,255,.14),0 8px 22px rgba(0,0,0,.25);
        }
        .st-key-game2-main .g2-brand-kicker {
            color:#e9bd65;font-size:.72rem;font-weight:850;
            letter-spacing:.18em;margin-bottom:4px;
        }
        .st-key-game2-main .g2-brand-title {
            color:#fff7e8;font-size:clamp(1.8rem,5vw,2.7rem);
            font-weight:900;line-height:1.1;letter-spacing:-.045em;
        }
        .st-key-game2-main .g2-brand-sub {
            color:#d0bfdf;font-size:.91rem;margin-top:6px;
        }
        .st-key-game2-main .g2-section-label {
            color:#e9bd65;font-size:.74rem;font-weight:850;
            letter-spacing:.15em;text-transform:uppercase;margin:18px 0 7px;
        }
        .st-key-game2-main .g2-panel {
            border:1px solid var(--g2-line);border-radius:18px;
            padding:18px;background:linear-gradient(145deg,rgba(65,35,87,.72),rgba(25,12,38,.88));
            box-shadow:inset 0 1px 0 rgba(255,255,255,.05),0 12px 30px rgba(0,0,0,.18);
        }
        .st-key-game2-main .g2-target {
            position:relative;overflow:hidden;text-align:center;
            border:1px solid rgba(233,189,101,.55);border-radius:22px;
            padding:24px 16px 20px;margin:16px 0 18px;
            background:
                radial-gradient(ellipse at 50% 0%,rgba(133,71,169,.42),transparent 62%),
                linear-gradient(145deg,#29143b,#170c25 78%);
            box-shadow:inset 0 1px 0 rgba(255,255,255,.09),0 12px 30px rgba(0,0,0,.25);
        }
        .st-key-game2-main .g2-target-label {
            color:#e4d5ef;font-size:.82rem;font-weight:750;
            letter-spacing:.12em;text-transform:uppercase;
        }
        .st-key-game2-main .g2-target-number {
            color:#f4d58c;font:900 clamp(3.7rem,15vw,5.5rem)/1.05 ui-monospace,monospace;
            letter-spacing:.12em;margin:8px 0;
            text-shadow:0 2px 16px rgba(233,189,101,.18);
        }
        .st-key-game2-main .g2-target-explain {
            color:#d7c7e4;font-size:.9rem;line-height:1.5;
        }
        .st-key-game2-main .g2-number-demo {
            display:flex;justify-content:center;align-items:center;gap:5px;
            margin:16px auto 2px;
        }
        .st-key-game2-main .g2-number-demo span {
            padding:8px 10px;border-radius:9px;
            background:rgba(255,255,255,.06);color:#d6c8e2;
            font:750 1.1rem ui-monospace,monospace;
        }
        .st-key-game2-main .g2-number-demo span:last-child {
            color:#1d1029;background:linear-gradient(135deg,#f3d68e,#d8a94d);
        }
        .st-key-game2-main .g2-number-demo small {
            color:#c5b1d8;font-size:.72rem;margin:0 5px;
        }
        .st-key-game2-main .g2-choice-note {
            color:#cbb9dc;text-align:center;font-size:.86rem;margin:0 0 12px;
        }
        .st-key-game2-main .stButton > button {
            min-height:50px;border-radius:13px !important;
            border:1px solid rgba(233,189,101,.58) !important;
            background:linear-gradient(145deg,#63358a,#3a1b55) !important;
            color:#fff6e8 !important;font-weight:850 !important;
            box-shadow:inset 0 1px 0 rgba(255,255,255,.12),0 7px 18px rgba(0,0,0,.2) !important;
        }
        .st-key-game2-main .stButton > button:hover {
            border-color:#f5d995 !important;
            background:linear-gradient(145deg,#7848a0,#4a2568) !important;
        }
        .st-key-game2-choice-low .stButton > button {
            background:linear-gradient(145deg,#9a6a2d,#654018) !important;
            border-color:rgba(245,217,149,.7) !important;color:#fff6e8 !important;
        }
        .st-key-game2-choice-low .stButton > button:hover {
            background:linear-gradient(145deg,#b7833e,#795021) !important;
        }
        .st-key-game2-main [data-testid="stMetric"] {
            background:rgba(39,20,56,.84);border:1px solid var(--g2-line);
            border-radius:14px;padding:12px;
        }
        .st-key-game2-main [data-testid="stMetricLabel"] {color:#d2c0e1 !important;}
        .st-key-game2-main [data-testid="stMetricValue"] {color:#f5d995 !important;}
        .st-key-game2-main .g2-result-hero {
            border:1px solid rgba(233,189,101,.55);border-radius:20px;
            padding:22px 16px;text-align:center;margin:12px 0 18px;
            background:radial-gradient(ellipse at 50% 0%,rgba(126,65,161,.4),transparent 65%),#1b0d29;
        }
        .st-key-game2-main .g2-result-status {
            color:#e9bd65;font-size:.78rem;font-weight:850;letter-spacing:.16em;
        }
        .st-key-game2-main .g2-result-title {
            color:#fff4df;font-size:clamp(1.7rem,5vw,2.4rem);
            font-weight:900;margin:6px 0;
        }
        .st-key-game2-main .g2-result-score {
            color:#f5d995;font:900 clamp(2.7rem,10vw,4.2rem)/1.1 ui-monospace,monospace;
            letter-spacing:.06em;margin:10px 0 2px;
        }
        .st-key-game2-main .g2-result-caption {color:#d4c2e3;font-size:.9rem;}
        .st-key-game2-main .g2-result-compare {
            display:grid;grid-template-columns:1fr auto 1fr;gap:10px;
            align-items:center;margin:15px 0;
        }
        .st-key-game2-main .g2-compare-box {
            padding:13px 8px;border-radius:13px;
            background:rgba(255,255,255,.055);border:1px solid var(--g2-line);
        }
        .st-key-game2-main .g2-compare-label {
            color:#cbb9dc;font-size:.73rem;margin-bottom:5px;
        }
        .st-key-game2-main .g2-compare-value {
            color:#f5d995;font:850 1.7rem ui-monospace,monospace;
        }
        .st-key-game2-main .g2-compare-vs {color:#bca7ce;font-size:.75rem;font-weight:800;}
        .st-key-game2-main .g2-wallet {
            display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:14px 0;
        }
        .st-key-game2-main .g2-wallet-item {
            border:1px solid var(--g2-line);border-radius:13px;
            padding:13px;background:rgba(37,18,54,.8);text-align:center;
        }
        .st-key-game2-main .g2-wallet-label {color:#cbb9dc;font-size:.78rem;}
        .st-key-game2-main .g2-wallet-value {color:#f5d995;font-size:1.25rem;font-weight:900;margin-top:4px;}
        @media(max-width:600px) {
            [data-testid="stApp"]:has(.st-key-game2-main) .block-container {
                padding-left:1rem;padding-right:1rem;
            }
            .st-key-game2-main .g2-brand {gap:12px;}
            .st-key-game2-main .g2-brand-emblem {width:54px;height:54px;flex-basis:54px;border-radius:15px;font-size:1.65rem;}
            .st-key-game2-main .g2-brand-sub {font-size:.8rem;}
            .st-key-game2-main .g2-target {padding:20px 12px 17px;}
            .st-key-game2-main .g2-wallet {gap:7px;}
        }
        </style>
    """)


def show_game_2():
    # Tutorial is shown once per round entry, before the wager screen.
    if not st.session_state.get("game_2_tutorial_done", False):
        _render_game_2_tutorial()
        return

    _game_2_theme_css()

    with st.container(key="game2-main"):
        # Persistent title strip, matching Game 4 / roulette casino styling.
        st.html("""
            <header class="g2-brand">
                <div class="g2-brand-emblem" aria-hidden="true">♛</div>
                <div>
                    <div class="g2-brand-kicker">NEWS ODDS · HIGH / LOW</div>
                    <div class="g2-brand-title">하이 앤 로우</div>
                    <div class="g2-brand-sub">뉴스를 읽고 AI 유사도 점수의 하이(High)와 로우(Low)를 예측하세요.</div>
                </div>
            </header>
        """)

        # 1. Wager stage — preserve the shared betting and loan/interest workflow.
        if "game_2_bet" not in st.session_state:
            if not check_user_coins_or_pop_bank(1_000):
                return

            user = st.session_state.get("current_user_data") or {}
            try:
                users_data = fetch_ranking_data()
            except Exception:
                users_data = None

            st.html("""
                <div class="g2-section-label">STEP 01 · YOUR WAGER</div>
                <div class="g2-panel">
                    <strong style="color:#f5d995;font-size:1.05rem">베팅 금액을 정하세요</strong>
                    <p style="margin:6px 0 0;color:#d4c2e3">
                        예측에 성공하면 베팅액의 2배를 획득하고, 실패하면 베팅액이 차감됩니다.
                    </p>
                </div>
            """)
            confirmed_bet = render_betting_ui(
                current_coins=int(user.get("코인", 0)),
                users_data=users_data,
                current_sid=str(st.session_state.get("current_user", "")),
                current_nickname=str(user.get("아이디", "")),
                min_bet=1_000,
                payout_multiplier=GAME_2_WIN_MULTIPLIER,
                title="하이 앤 로우",
                state_key="game_2",
            )
            if confirmed_bet is not None:
                st.session_state.game_2_bet = confirmed_bet
                st.rerun()
            return

        # 2. Roulette / news reader stage — keep the existing shared flow intact.
        title, article_text, url = get_game_news_selection(
            "game_2", win_multiplier=GAME_2_WIN_MULTIPLIER
        )
        if not title:
            return

        # 3. Prediction stage — only the two decimal digits (YY) are compared.
        if (
            "game_2_target_num" not in st.session_state
            or type(st.session_state.game_2_target_num) is not int
            or not 0 <= st.session_state.game_2_target_num <= 99
        ):
            st.session_state.game_2_target_num = random.randint(0, 99)

        target_num = st.session_state.game_2_target_num

        if "game_2_user_choice" not in st.session_state:
            st.html("""
                <div class="g2-section-label">STEP 02 · READ THE NEWS</div>
                <div class="g2-panel">
                    <div style="color:#f4e9ff;font-weight:850;font-size:1.05rem">
                        선택한 기사를 확인하세요
                    </div>
                    <div style="color:#cbb9dc;font-size:.86rem;margin-top:5px">
                        기사를 읽은 뒤 소수점 예측을 진행합니다.
                    </div>
                </div>
            """)
            st.caption(f"선택한 기사 · {title}")
            with st.expander("📰 선택한 뉴스 본문 보기", expanded=False):
                st.write(article_text if article_text else title)

            st.html(f"""
                <div class="g2-section-label">STEP 03 · MAKE YOUR CALL</div>
                <div class="g2-target">
                    <div class="g2-target-label">이번 라운드의 기준 숫자</div>
                    <div class="g2-target-number">{target_num:02d}</div>
                    <div class="g2-target-explain">
                        AI 유사도 <b>XX.YY</b> 중 정수 부분은 제외하고<br>
                        <b style="color:#f5d995">YY 두 자리만</b> 기준 숫자와 비교합니다.
                    </div>
                    <div class="g2-number-demo">
                        <span>87</span><small>정수 부분 제외</small>
                        <span>04</span>
                    </div>
                    <div class="g2-target-explain">예시: 87.04점 → 비교 대상은 04</div>
                </div>
                <p class="g2-choice-note">
                    기준 숫자 <b style="color:#f5d995">{target_num:02d}</b>와 같으면 HIGH에 포함됩니다.
                </p>
            """)

            high_col, low_col = st.columns(2, gap="small")
            with high_col:
                with st.container(key="game2-choice-high"):
                    if st.button(
                        f"⬆ HIGH · {target_num:02d} 이상",
                        key="game2_pick_high",
                        use_container_width=True,
                    ):
                        st.session_state.game_2_user_choice = "HIGH"
                        st.rerun()
            with low_col:
                with st.container(key="game2-choice-low"):
                    if st.button(
                        f"⬇ LOW · {target_num:02d} 미만",
                        key="game2_pick_low",
                        use_container_width=True,
                    ):
                        st.session_state.game_2_user_choice = "LOW"
                        st.rerun()
            return

        # 4. Calculate and settle exactly once; scoring rule is unchanged.
        bet_coin = int(st.session_state.game_2_bet)
        user_choice = st.session_state.game_2_user_choice

        if "game_2_result" not in st.session_state:
            with similarity_analysis_loading():
                text_for_summary = (
                    article_text if article_text and article_text.strip() else title
                )
                try:
                    summary_text, score_details = analyze_round_once(
                        st.session_state,
                        "game_2",
                        title=title,
                        article_text=text_for_summary,
                        summarize=summary,
                        similarity=similarity_check,
                        fallback_to_title=True,
                    )
                    actual_score = score_details["score"]
                    actual_decimal_digits = get_decimal_digits(actual_score)
                except (RuntimeError, ValueError, TypeError, KeyError) as exc:
                    st.error(f"뉴스 유사도를 계산하지 못했습니다: {exc}")
                    return

                is_win = (
                    actual_decimal_digits >= target_num
                    if user_choice == "HIGH"
                    else actual_decimal_digits < target_num
                )

                try:
                    settled = settle_game_round(
                        "game_2",
                        bet_coin,
                        is_win,
                        badge_evidence={"choice": user_choice},
                    )
                except BalanceChanged as changed:
                    update_session_balances(changed.balances)
                    st.error(str(changed))
                    return
                except TransactionError as exc:
                    st.error(str(exc))
                    return

                st.session_state.game_2_result = {
                    "title": title,
                    "summary": summary_text,
                    "actual_score": actual_score,
                    "actual_decimal_digits": actual_decimal_digits,
                    "score_details": score_details,
                    "target_num": target_num,
                    "user_choice": user_choice,
                    "reward": settled["reward"],
                    "is_win": is_win,
                    "new_coins": settled["new_coins"],
                    "new_streak": settled["new_streak"],
                }

        # 5. Preserve end-of-turn interest and the existing summary reveal.
        result = st.session_state.game_2_result
        if not apply_end_of_turn_interest("game_2"):
            return

        show_summary_before_score(
            result.get("summary", ""),
            "game_2_summary_revealed",
            title=result.get("title", title),
            score=result["actual_score"],
            details=result.get("score_details"),
        )

        # 6. Result stage — reveal the exact two digits used for settlement.
        actual_digits = int(result["actual_decimal_digits"])
        target_digits = int(result["target_num"])
        rounded_full_score = Decimal(str(result["actual_score"])).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        whole_part = int(rounded_full_score)
        is_win = bool(result["is_win"])
        choice_label = "HIGH" if result["user_choice"] == "HIGH" else "LOW"

        st.html(f"""
            <div class="g2-section-label">FINAL · ROUND RESULT</div>
            <section class="g2-result-hero">
                <div class="g2-result-status">{'CORRECT PREDICTION' if is_win else 'WRONG PREDICTION'}</div>
                <div class="g2-result-title">{'예측 성공!' if is_win else '아쉽게 빗나갔어요'}</div>
                <div class="g2-result-score">{whole_part}.{actual_digits:02d}</div>
                <div class="g2-result-caption">AI가 분석한 실제 유사도 점수</div>
                <div class="g2-result-compare">
                    <div class="g2-compare-box">
                        <div class="g2-compare-label">실제 소수점</div>
                        <div class="g2-compare-value">{actual_digits:02d}</div>
                    </div>
                    <div class="g2-compare-vs">VS</div>
                    <div class="g2-compare-box">
                        <div class="g2-compare-label">기준 숫자</div>
                        <div class="g2-compare-value">{target_digits:02d}</div>
                    </div>
                </div>
                <div class="g2-result-caption">
                    내 선택: <b style="color:#f5d995">{choice_label}</b>
                    · 비교 대상은 소수점 두 자리뿐입니다.
                </div>
            </section>
        """)

        if is_win:
            st.success(f"정답 · +{result['reward']:,} C")
            st.balloons()
        else:
            st.error(f"오답 · {result['reward']:,} C")

        st.html(f"""
            <div class="g2-wallet">
                <div class="g2-wallet-item">
                    <div class="g2-wallet-label">현재 보유 코인</div>
                    <div class="g2-wallet-value">{result['new_coins']:,} C</div>
                </div>
                <div class="g2-wallet-item">
                    <div class="g2-wallet-label">현재 연승 기록</div>
                    <div class="g2-wallet-value">{result['new_streak']} 연승</div>
                </div>
            </div>
        """)

        retry_col, main_col = st.columns(2, gap="small")
        with retry_col:
            if st.button("다시 도전하기", key="game2_result_retry", use_container_width=True):
                _reset_game_2_state()
                st.session_state.game_2_tutorial_done = True
                st.rerun()
        with main_col:
            if st.button("메인으로", key="game2_result_main", use_container_width=True):
                _reset_game_2_state()
                change_page("main")
