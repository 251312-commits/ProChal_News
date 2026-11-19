"""뉴스 제목과 본문의 일치율 구간을 맞히는 게임."""

import asyncio
from html import escape
from pathlib import Path
from decimal import Decimal, ROUND_HALF_UP
import math
import random

import streamlit as st

from games.shared.betting import check_user_coins_or_pop_bank
from games.shared.news_flow import get_game_news_selection
from games.shared.betting import render_betting_ui
from games.shared.loading import similarity_analysis_loading
from games.shared.interest import apply_end_of_turn_interest
from modules.transactions import BalanceChanged, TransactionError, settle_game_round, update_session_balances
from modules.news_ai import similarity_check, summary
from modules.ui_components import change_page, load_local_image_url
from views.ranking import fetch_ranking_data


GAME_4_WIN_MULTIPLIER = 3.0
GAME_4_MIN_BET = 1_000
GAME_4_SCORE_MAX = 99.99
GAME_4_RANGE_WIDTH = 2.0
GAME_4_RANGE_COUNT = 3


def _reset_game_4_state() -> None:
    for key in (
        "game_4_bet",
        "game_4_round_id",
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
    """Build three sorted 2pp ranges with a randomized correct numeric position."""
    # Use hundredths to keep the displayed boundaries identical to scoring.
    width_units = int(Decimal(str(GAME_4_RANGE_WIDTH)) * 100)
    max_score_units = int(Decimal(str(GAME_4_SCORE_MAX)) * 100)
    score_units = int(Decimal(str(_normalize_score(score))) * 100)
    score_bin = score_units // width_units

    # Only complete, nonnegative bins are shown. Near 0% or 99.99%
    # not every numeric position is possible without invalid ranges.
    max_start_bin = (
        max_score_units + 1 - width_units * GAME_4_RANGE_COUNT
    ) // width_units
    valid_positions = [
        index
        for index in range(GAME_4_RANGE_COUNT)
        if 0 <= score_bin - index <= max_start_bin
    ]
    if not valid_positions:
        raise ValueError("일치율에 맞는 구간을 생성할 수 없습니다.")

    answer_index = random.choice(valid_positions)
    first_bin = score_bin - answer_index
    ranges = [
        _format_range(
            (first_bin + index) * width_units / 100,
            ((first_bin + index + 1) * width_units - 1) / 100,
        )
        for index in range(GAME_4_RANGE_COUNT)
    ]
    return ranges, answer_index


def _render_game_4_range_picker(ranges: list[str], balance: int) -> int | None:
    """Mobile-first range picker using native, keyboard-accessible Streamlit radio."""
    asset_root = Path(__file__).resolve().parents[1] / "assets"
    bg = escape(load_local_image_url(str(asset_root / "bet_background.jpg")), quote=True)
    crown = escape(load_local_image_url(str(asset_root / "bet_crown.png")), quote=True)
    laurel_left = escape(
        load_local_image_url(str(asset_root / "game1_article" / "icons" / "laurel-left.png")),
        quote=True,
    )
    laurel_right = escape(
        load_local_image_url(str(asset_root / "game1_article" / "icons" / "laurel-right.png")),
        quote=True,
    )

    st.html(Path(__file__).with_name("game4_picker.css"))
    st.html(
        '<style>.st-key-game4_picker_shell {'
        f'background-image: radial-gradient(circle at 50% 40%, rgba(104,22,164,.33), transparent 68%),'
        f'linear-gradient(180deg, rgba(17,5,38,.88), rgba(15,3,38,.94)),'
        f'url("{bg}") !important;'
        'background-size: cover !important; background-position: center !important;'
        '}</style>'
    )

    high = escape(ranges[-1].split("~", 1)[-1])
    low = escape(ranges[0].split("~", 1)[0] + "%")
    range_labels = {2: "상위 구간", 1: "중간 구간", 0: "하위 구간"}

    with st.container(key="game4_picker_shell"):
        back_col, balance_col, bank_col = st.columns(
            [0.8, 3.2, 0.8], gap="small", vertical_alignment="center"
        )
        with back_col:
            if st.button("❮", key="game4_picker_back", help="메인으로"):
                change_page("main")
                return None
        with balance_col:
            st.html(
                '<div class="cb-balance" aria-label="현재 보유 코인">'
                '<span class="cb-coin-symbol" aria-hidden="true">$</span>'
                f'{balance:,}</div>'
            )
        with bank_col:
            if st.button("+", key="game4_picker_bank", help="은행으로"):
                change_page("bank")
                return None

        st.html(
            '<header class="g4-heading cb-hero">'
            f'<img src="{crown}" class="cb-logo g4-bet-logo" alt="BET 로고" loading="eager">'
            '<p class="cb-game-title">게임 4 · 일치율 구간 예측</p>'
            '<div class="g4-title-row">'
            f'<img src="{laurel_left}" alt="" class="g4-laurel">'
            '<h1>구간 맞히기</h1>'
            f'<img src="{laurel_right}" alt="" class="g4-laurel">'
            '</div>'
            '<p class="cb-description">숨겨진 일치율이 어느 구간에 있을까?</p>'
            '</header>'
        )

        with st.container(key="game4_picker_board"):
            hidden_col, scale_col = st.columns(
                [0.78, 1.35], gap="small", vertical_alignment="center"
            )
            with hidden_col:
                st.html(
                    '<div class="g4-mystery" aria-label="실제 일치율은 숨겨져 있습니다">'
                    '<div class="g4-mystery-label">숨겨진 일치율</div>'
                    '<strong>??</strong>'
                    '<span class="g4-mystery-unit">%</span>'
                    '</div>'
                )
            with scale_col:
                with st.container(key="game4_picker_axis"):
                    st.html(
                        f'<div class="g4-axis-cap g4-axis-cap-top">{high}</div>'
                    )
                    # Descending display order matches the vertical scale.
                    # Returned values remain original list indexes for scoring.
                    selected = st.radio(
                        "예상 일치율 구간 선택",
                        options=[2, 1, 0],
                        format_func=lambda idx: (
                            f"**{range_labels[idx]}**  \n({ranges[idx]})"
                        ),
                        key="game_4_range_picker",
                        index=1,
                        label_visibility="collapsed",
                    )
                    st.html(
                        f'<div class="g4-axis-cap g4-axis-cap-bottom">{low}</div>'
                    )

        if st.button(
            "✓  선택하기",
            key="game4_picker_submit",
            use_container_width=True,
            type="primary",
        ):
            return selected
    return None


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

    settled = settle_game_round("game_4", int(bet_coin), is_win)
    reward = settled["reward"]
    new_coins = settled["new_coins"]
    new_streak = settled["new_streak"]

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
    if not apply_end_of_turn_interest("game_4"):
        return

    # The score is already settled. CSS animates the mystery card before
    # revealing it; no timer or rerun can duplicate the ledger transaction.
    st.html(Path(__file__).with_name("game4_picker.css"))
    score_text = f"{result['actual_score']:.2f}%"
    with st.container(key="game4_result_shell"):
        st.html(
            '<section class="g4-result-scene" aria-label="실제 뉴스 일치율 공개">'
            '<div class="g4-result-heading">숨겨진 일치율 공개</div>'
            '<div class="g4-reel-window" role="img" '
            f'aria-label="실제 일치율 {escape(score_text, quote=True)}">'
            '<span class="g4-reel-mystery" aria-hidden="true">??</span>'
            f'<strong class="g4-reel-value" aria-hidden="true">{escape(score_text)}</strong>'
            '</div>'
            '<p class="g4-reel-caption">AI 일치율 분석 결과</p>'
            '</section>'
        )
        with st.container(key="game4_result_details"):
            if result["is_win"]:
                st.success(f"정답입니다! +{result['reward']:,} C")
            else:
                st.error(f"틀렸습니다! {result['reward']:,} C")
            st.write(f"선택한 구간: **{result['selected_range']}**")
            st.info(f"정답 구간: **{result['target_range']}**")
            st.write(f"현재 보유 코인: **{result['new_coins']:,} C**")
            st.write(f"현재 연승 기록: **{result['new_streak']} 연승**")

            col_retry, col_main = st.columns(2)
            with col_retry:
                if st.button("다시 도전하기", key="game4_result_retry", use_container_width=True):
                    _reset_game_4_state()
                    st.rerun()
            with col_main:
                if st.button("메인으로", key="game4_result_main", use_container_width=True):
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
            state_key="game_4",
        )
        if confirmed_bet is not None:
            st.session_state.game_4_bet = confirmed_bet
            st.rerun()
        return

    title, article_text, _ = get_game_news_selection(
        "game_4", win_multiplier=GAME_4_WIN_MULTIPLIER, immersive_reader=True
    )
    if not title:
        return

    if "game_4_score" not in st.session_state:
        with similarity_analysis_loading():
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
        selected_range = _render_game_4_range_picker(
            st.session_state.game_4_ranges,
            int(st.session_state.get("current_user_data", {}).get("코인", 0)),
        )
        if selected_range is not None:
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
        except BalanceChanged as changed:
            update_session_balances(changed.balances)
            st.error(str(changed))
            return
        except (TransactionError, RuntimeError, ValueError, TypeError, KeyError) as exc:
            st.error(f"게임 결과를 처리하지 못했습니다: {exc}")
            return
        st.session_state.game_4_result = result

    _show_game_4_result()
