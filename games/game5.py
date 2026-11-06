"""제시된 일치율 구간에 해당하는 뉴스를 고르는 게임."""

import asyncio
from decimal import Decimal, ROUND_HALF_UP
import html
import math
import random
from pathlib import Path

import streamlit as st

from games.shared.betting import check_user_coins_or_pop_bank
from games.shared.betting import render_betting_ui
from games.shared.loading import similarity_analysis_loading
from modules.db_handler import init_gspread, init_news_sheet
from modules.news_ai import bring_article, pick_5_lowest_count_news, similarity_check, summary
from modules.ui_components import change_page
from views.ranking import fetch_ranking_data


GAME_5_WIN_MULTIPLIER = 5.0
GAME_5_MIN_BET = 1000
GAME_5_SCORE_MAX = 99.99
GAME_5_TARGET_RANGE_WIDTH = 2.0

ws = init_gspread()
ws_news = init_news_sheet()


def _reset_game_5_state() -> None:
    for key in (
        "game_5_bet",
        "game_5_target_range",
        "game_5_answer_index",
        "game_5_candidates",
        "game_5_selected_index",
        "game_5_result",
        "game_5_article_index",
        "bet_slider_val",
    ):
        st.session_state.pop(key, None)


def _load_candidates(excluded_urls: set[str] | None = None) -> list[dict]:
    excluded_urls = excluded_urls or set()
    records = ws_news.get_all_records()
    news_list = []
    for row_index, item in enumerate(records, start=2):
        url = str(item.get("URL", "")).strip()
        title = str(item.get("Title", "")).strip()
        if not url or not title or url in excluded_urls:
            continue
        try:
            count = int(float(item.get("Count", 0) or 0))
        except (TypeError, ValueError):
            count = 0
        news_list.append({"url": url, "title": title, "count": count, "row_idx": row_index})

    candidates = pick_5_lowest_count_news(news_list)
    if len(candidates) < 5:
        raise ValueError("게임 5에 필요한 뉴스 후보가 5개 미만입니다.")

    return [{**item, "text": ""} for item in candidates]


@st.cache_data(ttl=3600, show_spinner=False)
def _extract_article(url: str) -> tuple[str, str]:
    return bring_article(url)


@st.cache_data(ttl=3600, show_spinner=False)
def _calculate_score_cached(article_text: str, title: str) -> float:
    summary_text = asyncio.run(summary(article_text))
    if not summary_text:
        raise ValueError("뉴스 본문 요약 결과가 비어 있습니다.")
    score_details = similarity_check(summary_text, title)
    score = score_details.get("score")
    if (
        not isinstance(score, (int, float))
        or isinstance(score, bool)
        or not math.isfinite(float(score))
    ):
        raise ValueError("뉴스 일치율 결과가 올바른 숫자가 아닙니다.")
    normalized_score = Decimal(str(score)).quantize(
        Decimal("0.01"),
        rounding=ROUND_HALF_UP,
    )
    return max(0.0, min(float(normalized_score), GAME_5_SCORE_MAX))


def _load_article(article: dict) -> None:
    try:
        title, text = _extract_article(article["url"])
    except Exception as exc:
        raise RuntimeError(f"뉴스 본문을 불러오지 못했습니다: {exc}") from exc
    if not title or not text:
        raise ValueError("제목 또는 본문이 비어 있는 뉴스가 후보에 포함되어 있습니다.")
    article["title"] = title
    article["text"] = text


def _calculate_score(article: dict) -> float:
    return _calculate_score_cached(article["text"], article["title"])


def _replace_candidate(candidates: list[dict], index: int) -> None:
    excluded_urls = {candidate["url"] for candidate in candidates}
    replacements = _load_candidates(excluded_urls)
    if not replacements:
        raise ValueError("교체할 수 있는 뉴스 후보가 없습니다.")
    candidates[index] = replacements[0]


def _build_exclusive_range(candidates: list[dict], answer_index: int) -> tuple[float, float]:
    """Build a narrow score range containing only the selected score."""
    answer_score = candidates[answer_index]["score"]
    other_scores = {
        candidate["score"]
        for index, candidate in enumerate(candidates)
        if index != answer_index
    }
    if answer_score in other_scores:
        raise ValueError("후보 뉴스의 일치율이 같아 정답 구간을 분리할 수 없습니다.")

    nearest_gap = min(abs(answer_score - score) for score in other_scores)
    if nearest_gap <= 0:
        raise ValueError("후보 뉴스의 일치율로 정답 구간을 만들 수 없습니다.")

    # Keep a generous margin from the neighboring score without falling back
    # to the impractically wide 0~100% range at the ends of the scale.
    half_width = min(
        nearest_gap * (2 / 3),
        GAME_5_TARGET_RANGE_WIDTH / 2,
    )
    lower = max(0.0, answer_score - half_width)
    upper = min(GAME_5_SCORE_MAX, answer_score + half_width)
    quantizer = Decimal("0.01")
    lower = float(Decimal(str(lower)).quantize(quantizer, rounding=ROUND_HALF_UP))
    upper = float(Decimal(str(upper)).quantize(quantizer, rounding=ROUND_HALF_UP))
    lower_candidates = [
        lower,
        *(score + 0.01 for score in other_scores if score < answer_score),
    ]
    upper_candidates = [
        upper,
        *(score - 0.01 for score in other_scores if score > answer_score),
    ]
    lower = max(lower_candidates)
    upper = min(upper_candidates)
    upper = min(upper, lower + GAME_5_TARGET_RANGE_WIDTH)
    if lower > answer_score or answer_score > upper:
        raise ValueError("후보 뉴스의 일치율로 정답 구간을 만들 수 없습니다.")
    return lower, upper


def _build_target_range(answer_score: float) -> tuple[float, float]:
    """Build a small, score-centered range without calculating other candidates."""
    half_width = GAME_5_TARGET_RANGE_WIDTH / 2
    lower = max(0.0, answer_score - half_width)
    upper = min(GAME_5_SCORE_MAX, answer_score + half_width)
    if upper - lower < GAME_5_TARGET_RANGE_WIDTH:
        if lower == 0.0:
            upper = min(GAME_5_SCORE_MAX, GAME_5_TARGET_RANGE_WIDTH)
        elif upper == GAME_5_SCORE_MAX:
            lower = max(0.0, GAME_5_SCORE_MAX - GAME_5_TARGET_RANGE_WIDTH)
    quantizer = Decimal("0.01")
    return (
        float(Decimal(str(lower)).quantize(quantizer, rounding=ROUND_HALF_UP)),
        float(Decimal(str(upper)).quantize(quantizer, rounding=ROUND_HALF_UP)),
    )


def _format_score_range(score_range: tuple[float, float]) -> str:
    return f"{score_range[0]:.2f}~{score_range[1]:.2f}%"


def _show_article_detail() -> None:
    candidates = st.session_state.get("game_5_candidates", [])
    article_index = st.session_state.get("game_5_article_index")
    if not isinstance(article_index, int) or not 0 <= article_index < len(candidates):
        st.error("열람할 뉴스 정보를 찾을 수 없습니다.")
        if st.button("게임으로 돌아가기"):
            change_page("game_5")
        return

    article = candidates[article_index]
    if not article.get("text"):
        with st.spinner("뉴스 본문을 불러오는 중..."):
            try:
                _load_article(article)
            except (RuntimeError, ValueError) as exc:
                try:
                    _replace_candidate(candidates, article_index)
                except ValueError as replacement_exc:
                    st.error(f"뉴스 본문을 불러오지 못했고 교체할 후보도 없습니다: {replacement_exc}")
                    return
                st.warning(f"실패한 기사를 교체했습니다: {exc}")
                st.session_state.pop("game_5_article_index", None)
                st.rerun()
                return
    st.title(f"📰 후보 {article_index + 1} 본문")
    st.subheader(article["title"])
    st.markdown(article["text"])
    if st.button("⬅️ 후보 목록으로 돌아가기", use_container_width=True):
        change_page("game_5")


def _show_result() -> None:
    result = st.session_state.get("game_5_result")
    if not result:
        change_page("game_5")
        return

    st.title("🏆 게임 5 최종 결과")
    if result["is_win"]:
        st.balloons()
        st.success(f"🎉 정답입니다! +{result['reward']:,} C")
    else:
        st.error(f"❌ 틀렸습니다! {result['reward']:,} C")
    st.metric("선택한 뉴스의 실제 일치율", f"{result['actual_score']:.2f}%")
    st.info(f"정답 구간: {result['target_range']}")
    st.write(f"현재 보유 코인: **{result['new_coins']:,} C**")
    st.write(f"현재 연승 기록: **{result['new_streak']} 연승**")

    col_retry, col_main = st.columns(2)
    with col_retry:
        if st.button("🔄 다시 도전하기", use_container_width=True):
            _reset_game_5_state()
            change_page("game_5")
    with col_main:
        if st.button("⬅️ 메인으로 돌아가기", use_container_width=True):
            _reset_game_5_state()
            change_page("main")


def show_game_5():
    st.title("🎮 게임 5: 일치율 구간 뉴스 맞히기")
    if st.button(
        "📖 게임 5 튜토리얼 다시 보기",
        key="game_5_show_tutorial",
        help="게임 진행 방법을 다시 확인합니다.",
    ):
        change_page("game_5_tutorial")

    if "game_5_bet" not in st.session_state:
        if not check_user_coins_or_pop_bank(GAME_5_MIN_BET):
            return

        user_data = st.session_state.get("current_user_data", {})
        confirmed_bet = render_betting_ui(
            current_coins=int(user_data.get("코인", 0)),
            users_data=fetch_ranking_data(),
            current_sid=str(st.session_state.get("current_user", "")),
            current_nickname=str(user_data.get("아이디", "")),
            min_bet=GAME_5_MIN_BET,
            payout_multiplier=GAME_5_WIN_MULTIPLIER,
            title="게임 5: 일치율 구간 뉴스 맞히기",
            state_key="game_5",
        )
        if confirmed_bet is not None:
            st.session_state.game_5_bet = confirmed_bet
            st.rerun()
        return

    if "game_5_candidates" not in st.session_state:
        with similarity_analysis_loading():
            failed_urls = set()
            while True:
                round_candidates = None
                try:
                    round_candidates = _load_candidates(failed_urls)
                    answer_index = random.randrange(len(round_candidates))
                    _load_article(round_candidates[answer_index])
                    round_candidates[answer_index]["score"] = _calculate_score(
                        round_candidates[answer_index]
                    )
                    target_range = _build_target_range(round_candidates[answer_index]["score"])
                    break
                except (RuntimeError, ValueError, TypeError) as exc:
                    if not round_candidates:
                        st.error(f"뉴스 후보를 준비하지 못했습니다: {exc}")
                        return
                    failed_urls.add(round_candidates[answer_index]["url"])
                    if len(failed_urls) >= len(ws_news.get_all_records()):
                        st.error(f"뉴스 후보를 준비하지 못했습니다: {exc}")
                        return
            candidates = round_candidates
            st.session_state.game_5_candidates = candidates
        st.session_state.game_5_answer_index = answer_index
        st.session_state.game_5_target_range = target_range
        st.rerun()

    candidates = st.session_state.game_5_candidates
    target_range = st.session_state.game_5_target_range
    st.info("본문을 확인한 뒤, 이 구간에 해당하는 뉴스 하나를 선택하세요.")
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg, #260044, #110022);
                    border:3px solid #ff00ff; border-radius:14px;
                    box-shadow:0 0 18px rgba(255,0,255,.65);
                    padding:18px 16px; margin:12px 0 24px; text-align:center;">
            <div style="color:#ffd700; font-size:1.15rem; font-weight:800;">
                🎯 정답 일치율 구간
            </div>
            <div style="color:#ffffff; font-size:2.25rem; font-weight:900;
                        letter-spacing:1px; margin-top:4px;">
                {_format_score_range(target_range)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <style>
        .st-key-game5-candidates [data-testid="stHorizontalBlock"] {
            gap: 12px;
            align-items: stretch;
        }
        .st-key-game5-candidates [data-testid="stVerticalBlockBorderWrapper"] {
            height: 100%;
            min-height: 190px;
            border: 2px solid #a842c5;
            border-radius: 22px;
            background: linear-gradient(160deg, #351346, #17091f);
            box-shadow: 0 0 12px #a13dcc35, inset 0 0 18px #a13dcc22;
            padding: 14px 12px 12px;
        }
        .st-key-game5-candidates .st-key-game5-card-0 {
            transform: translateX(50%);
            position: relative;
            z-index: 1;
        }
        .st-key-game5-candidates .st-key-game5-card-1 {
            transform: translateX(-50%);
            position: relative;
            z-index: 1;
        }
        .st-key-game5-candidates [data-testid="stVerticalBlockBorderWrapper"]:hover {
            border-color: #e7a4ff;
            box-shadow: 0 0 14px #bf4ce366, inset 0 0 18px #a13dcc35;
        }
        .st-key-game5-candidates .game5-card-title {
            min-height: 70px;
            color: #fff3ff;
            font-size: clamp(14px, 3.8vw, 18px);
            font-weight: 800;
            line-height: 1.35;
            overflow-wrap: anywhere;
        }
        .st-key-game5-candidates .game5-card-number {
            display: grid;
            place-items: center;
            width: 34px;
            height: 34px;
            margin-bottom: 10px;
            border-radius: 12px;
            background: #ffda39;
            color: #25132f;
            font-weight: 900;
        }
        .st-key-game5-candidates [data-testid="stButton"] button {
            min-height: 40px;
            border-radius: 12px;
            font-size: 13px;
        }
        @media (max-width: 430px) {
            .st-key-game5-candidates [data-testid="stHorizontalBlock"] {
                gap: 8px;
            }
            .st-key-game5-candidates [data-testid="stVerticalBlockBorderWrapper"] {
                min-height: 178px;
                padding: 11px 9px 10px;
                border-radius: 18px;
            }
            .st-key-game5-candidates .game5-card-title {
                min-height: 76px;
                font-size: 13px;
            }
            .st-key-game5-candidates [data-testid="stButton"] button {
                padding-inline: 4px;
                font-size: 12px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    with st.container(key="game5-candidates"):
        rows = ((0, None, 1), (2, 3, 4))
        for row in rows:
            columns = st.columns(3)
            for column, index in zip(columns, row):
                if index is None:
                    continue
                article = candidates[index]
                with column:
                    with st.container(
                        key=f"game5-card-{index}",
                        border=True,
                    ):
                        st.markdown(
                            f'<div class="game5-card-number">{index + 1}</div>'
                            f'<div class="game5-card-title">'
                            f'{html.escape(article["title"])}</div>',
                            unsafe_allow_html=True,
                        )
                        read_col, select_col = st.columns(2)
                        with read_col:
                            if st.button(
                                "📖 본문",
                                key=f"game_5_article_{index}",
                                use_container_width=True,
                            ):
                                if not article.get("text"):
                                    with st.spinner("뉴스 본문을 불러오는 중..."):
                                        try:
                                            _load_article(article)
                                        except (RuntimeError, ValueError) as exc:
                                            try:
                                                _replace_candidate(candidates, index)
                                            except ValueError as replacement_exc:
                                                st.error(
                                                    "뉴스 본문을 불러오지 못했고 "
                                                    f"교체할 후보도 없습니다: {replacement_exc}"
                                                )
                                                continue
                                            st.warning(f"실패한 기사를 교체했습니다: {exc}")
                                            st.rerun()
                                            continue
                                st.session_state.game_5_article_index = index
                                change_page("game_5_article")
                        with select_col:
                            if st.button(
                                "✅ 선택",
                                key=f"game_5_select_{index}",
                                use_container_width=True,
                            ):
                                st.session_state.game_5_selected_index = index
                                st.rerun()

    if "game_5_selected_index" not in st.session_state:
        return

    if "game_5_result" not in st.session_state:
        selected_index = st.session_state.game_5_selected_index
        selected_article = candidates[selected_index]
        if "score" not in selected_article or not selected_article.get("text"):
            with similarity_analysis_loading():
                try:
                    _load_article(selected_article)
                    selected_article["score"] = _calculate_score(selected_article)
                except (RuntimeError, ValueError, TypeError) as exc:
                    try:
                        _replace_candidate(candidates, selected_index)
                    except ValueError as replacement_exc:
                        st.error(f"선택한 기사를 교체할 수 없습니다: {replacement_exc}")
                        return
                    st.session_state.pop("game_5_selected_index", None)
                    st.warning(f"실패한 기사를 교체했습니다. 다시 선택해 주세요: {exc}")
                    st.rerun()
                    return
        actual_score = selected_article["score"]

        is_win = target_range[0] <= actual_score <= target_range[1]
        bet_coin = int(st.session_state.game_5_bet)
        reward = int(bet_coin * GAME_5_WIN_MULTIPLIER) if is_win else -bet_coin

        current_sid = str(st.session_state.get("current_user", "")).strip().replace(".0", "")
        users_data = ws.get_all_records()
        user_row_idx = None
        user_info = None
        for index, user in enumerate(users_data):
            if str(user.get("학번", "")).strip().replace(".0", "") == current_sid:
                user_row_idx = index + 2
                user_info = user
                break
        if user_info is None or user_row_idx is None:
            st.error("사용자 정보를 찾을 수 없어 정산할 수 없습니다.")
            return

        current_coins = int(user_info.get("코인", 0))
        current_streak = int(user_info.get("연승", 0))
        new_coins = max(0, current_coins + reward)
        new_streak = current_streak + 1 if is_win else 0
        ws.update_cell(user_row_idx, 3, new_coins)
        ws.update_cell(user_row_idx, 4, new_streak)
        st.session_state.current_user_data["코인"] = new_coins
        st.session_state.current_user_data["연승"] = new_streak
        st.session_state.game_5_result = {
            "actual_score": actual_score,
            "target_range": _format_score_range(target_range),
            "reward": reward,
            "is_win": is_win,
            "new_coins": new_coins,
            "new_streak": new_streak,
        }
        change_page("game_5_result")


# Game 5-only tutorial and entry navigation.
GAME_5_TUTORIAL_SEEN_KEY = "game_5_tutorial_seen"


def _start_game_5() -> None:
    st.session_state[GAME_5_TUTORIAL_SEEN_KEY] = True
    change_page("game_5")


def show_game_5_tutorial():
    with st.container(key="game5-guide", gap=None):
        st.html(Path(__file__).with_name("game5_tutorial.css"))
        with st.container(key="game5-guide-nav", horizontal=True, gap=None):
            if st.button("메인으로", key="game5-guide-back"):
                change_page("main")
            if st.button("건너뛰기", key="game5-guide-skip"):
                _start_game_5()
        st.html(
            """
            <section class="game5-guide-sheet" aria-labelledby="game5-guide-title" lang="ko">
                <header class="game5-guide-heading">
                    <span>GAME 05</span><h1 id="game5-guide-title">일치율 구간 뉴스 맞히기</h1>
                    <p>제시된 구간에 들어갈 뉴스는 무엇일까?</p>
                </header>
                <ol aria-label="게임 진행 순서" role="list">
                    <li>
                        <h2><span>01</span>코인 베팅</h2>
                        <div class="game5-guide-icon">C</div>
                        <p>게임에 사용할 코인을<br><b>최소 1,000 C</b>부터 베팅한다.</p>
                    </li>
                    <li>
                        <h2><span>02</span>정답 구간 확인</h2>
                        <div class="game5-guide-icon">%</div>
                        <p>서로 다른 뉴스의 일치율을 가르는<br>정답 구간이 제시된다.</p>
                    </li>
                    <li>
                        <h2><span>03</span>뉴스 선택</h2>
                        <div class="game5-guide-icon">?</div>
                        <p>후보 뉴스 <b>5개</b>를 읽고<br>구간에 해당하는 한 편을 고른다.</p>
                    </li>
                    <li>
                        <h2><span>04</span>결과 확인</h2>
                        <div class="game5-guide-icon">5x</div>
                        <p>정답이면 <b>베팅액의 5배</b>를 받고,<br>틀리면 베팅액을 잃는다.</p>
                    </li>
                </ol>
            </section>
            """
        )
        if st.button("게임 시작", key="game5-guide-start", type="primary", width="stretch"):
            _start_game_5()
