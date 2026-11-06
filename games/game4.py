"""뉴스 제목과 본문의 일치율 구간을 맞히는 게임."""

import asyncio
from decimal import Decimal, ROUND_HALF_UP
import math
import random

import streamlit as st

from games.common import (
    check_user_coins_or_pop_bank,
    get_game_news_selection,
    render_betting_ui,
)
from modules.db_handler import init_gspread
from modules.news_ai import similarity_check, summary
from modules.ui_components import change_page
from views.ranking import fetch_ranking_data


GAME_4_WIN_MULTIPLIER = 2.0
GAME_4_MIN_BET = 1_000
GAME_4_SCORE_MAX = 99.99
GAME_4_RANGE_WIDTH = 2.0
GAME_4_RANGE_COUNT = 3


def _reset_game_4_state() -> None:
    for key in (
        "game_4_bet",
        "selected_news_game_4",
        "candidates_game_4",
        "read_done_game_4",
        "game_4_range",
        "game_4_range_picker",
        "game_4_ranges",
        "game_4_score",
        "game_4_answer_index",
        "game_4_result",
        "bet_slider_val",
    ):
        st.session_state.pop(key, None)


def _normalize_score(score: object) -> float:
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
    return max(0.0, min(float(normalized_score), GAME_4_SCORE_MAX))


def _format_range(lower: float, upper: float) -> str:
    return f"{lower:.2f}~{upper:.2f}%"


def _build_dynamic_ranges(score: float) -> tuple[list[str], int]:
    """Create three narrow, adjacent ranges around the hidden score."""
    total_width = GAME_4_RANGE_WIDTH * GAME_4_RANGE_COUNT
    start = min(
        max(0.0, score - total_width),
        GAME_4_SCORE_MAX - total_width,
    )
    start = float(
        Decimal(str(start)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )

    ranges = []
    for index in range(GAME_4_RANGE_COUNT):
        lower = start + index * GAME_4_RANGE_WIDTH
        upper = min(
            GAME_4_SCORE_MAX,
            start + (index + 1) * GAME_4_RANGE_WIDTH - 0.01,
        )
        ranges.append(_format_range(lower, upper))

    answer_index = next(
        (
            index
            for index in range(GAME_4_RANGE_COUNT)
            if start + index * GAME_4_RANGE_WIDTH <= score
            <= start + (index + 1) * GAME_4_RANGE_WIDTH
        ),
        GAME_4_RANGE_COUNT - 1,
    )
    order = list(range(GAME_4_RANGE_COUNT))
    random.shuffle(order)
    shuffled_ranges = [ranges[index] for index in order]
    return shuffled_ranges, order.index(answer_index)


def _settle_game_4(
    *,
    actual_score: float,
    selected_range: int,
    ranges: list[str],
    answer_index: int,
    bet_coin: int,
) -> dict:
    is_win = selected_range == answer_index
    reward = int(bet_coin * GAME_4_WIN_MULTIPLIER) if is_win else -bet_coin

    ws = init_gspread()
    current_sid = str(st.session_state.get("current_user", "")).strip().replace(".0", "")
    user_row_idx = None
    user_info = None
    for index, user in enumerate(ws.get_all_records()):
        sid = str(user.get("학번", "")).strip().replace(".0", "")
        if sid == current_sid:
            user_row_idx = index + 2
            user_info = user
            break

    if user_info is None or user_row_idx is None:
        raise ValueError("사용자 정보를 찾을 수 없어 정산할 수 없습니다.")

    current_coins = int(user_info.get("코인", 0))
    current_streak = int(user_info.get("연승", 0))
    new_coins = max(0, current_coins + reward)
    new_streak = current_streak + 1 if is_win else 0
    ws.update_cell(user_row_idx, 3, new_coins)
    ws.update_cell(user_row_idx, 4, new_streak)
    st.session_state.current_user_data["코인"] = new_coins
    st.session_state.current_user_data["연승"] = new_streak

    return {
        "actual_score": actual_score,
        "selected_range": ranges[selected_range],
        "target_range": ranges[answer_index],
        "reward": reward,
        "is_win": is_win,
        "new_coins": new_coins,
        "new_streak": new_streak,
    }


def _show_game_4_result() -> None:
    result = st.session_state.game_4_result
    st.subheader("🏆 최종 결과")
    if result["is_win"]:
        st.balloons()
        st.success(f"🎉 정답입니다! +{result['reward']:,} C")
    else:
        st.error(f"❌ 틀렸습니다! {result['reward']:,} C")

    st.metric("실제 일치율", f"{result['actual_score']:.2f}%")
    st.write(f"선택한 구간: **{result['selected_range']}**")
    st.info(f"정답 구간: **{result['target_range']}**")
    st.write(f"현재 보유 코인: **{result['new_coins']:,} C**")
    st.write(f"현재 연승 기록: **{result['new_streak']} 연승**")

    col_retry, col_main = st.columns(2)
    with col_retry:
        if st.button("🔄 다시 도전하기", use_container_width=True):
            _reset_game_4_state()
            st.rerun()
    with col_main:
        if st.button("⬅️ 메인으로 돌아가기", use_container_width=True):
            _reset_game_4_state()
            change_page("main")


def show_game_4():
    if "game_4_bet" not in st.session_state:
        if not check_user_coins_or_pop_bank(GAME_4_MIN_BET):
            return

        user_data = st.session_state.get("current_user_data", {})
        confirmed_bet = render_betting_ui(
            current_coins=int(user_data.get("코인", 0)),
            users_data=fetch_ranking_data(),
            current_sid=str(st.session_state.get("current_user", "")),
            current_nickname=str(user_data.get("아이디", "")),
            min_bet=GAME_4_MIN_BET,
            payout_multiplier=GAME_4_WIN_MULTIPLIER,
            title="게임 4: 일치율 구간 뉴스 맞히기",
        )
        if confirmed_bet is not None:
            st.session_state.game_4_bet = confirmed_bet
            st.rerun()
        return

    title, article_text, _ = get_game_news_selection("game_4")
    if not title:
        return

    st.title("🎮 게임 4: 일치율 구간 뉴스 맞히기")
    st.caption("뉴스 제목과 본문의 일치율이 어느 구간에 속하는지 선택하세요.")

    if "game_4_score" not in st.session_state:
        with st.spinner("🤖 AI가 뉴스 일치율 구간을 준비 중입니다..."):
            try:
                summary_text = asyncio.run(summary(article_text))
                if not summary_text:
                    st.error("뉴스 본문 요약에 실패해 일치율 구간을 만들 수 없습니다.")
                    return
                score = _normalize_score(similarity_check(summary_text, title)["score"])
                ranges, answer_index = _build_dynamic_ranges(score)
            except (RuntimeError, ValueError, TypeError, KeyError) as exc:
                st.error(f"일치율 구간을 준비하지 못했습니다: {exc}")
                return
        st.session_state.game_4_score = score
        st.session_state.game_4_ranges = ranges
        st.session_state.game_4_answer_index = answer_index
        st.rerun()

    if "game_4_range" not in st.session_state:
        ranges = st.session_state.game_4_ranges
        st.subheader("🎯 예상 일치율 구간")
        selected_range = st.radio(
            "일치율 구간을 선택하세요.",
            options=range(len(ranges)),
            format_func=lambda value: f"{value + 1}번: {ranges[value]}",
            key="game_4_range_picker",
            horizontal=True,
        )
        if st.button("🎯 이 구간에 배팅하기", use_container_width=True):
            st.session_state.game_4_range = selected_range
            st.rerun()
        return

    if "game_4_result" not in st.session_state:
        try:
            result = _settle_game_4(
                actual_score=st.session_state.game_4_score,
                selected_range=st.session_state.game_4_range,
                ranges=st.session_state.game_4_ranges,
                answer_index=st.session_state.game_4_answer_index,
                bet_coin=int(st.session_state.game_4_bet),
            )
        except (RuntimeError, ValueError, TypeError, KeyError) as exc:
            st.error(f"게임 결과를 처리하지 못했습니다: {exc}")
            return
        st.session_state.game_4_result = result

    _show_game_4_result()
