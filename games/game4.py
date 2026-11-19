"""뉴스 제목과 본문의 일치율 구간을 맞히는 게임."""

import asyncio
from html import escape
from uuid import uuid4
import streamlit.components.v1 as components
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
from games.shared.result import _score_diagram
from modules.ui_components import change_page, load_local_image_url
from views.ranking import fetch_ranking_data


GAME_4_WIN_MULTIPLIER = 3.0
GAME_4_MIN_BET = 1_000
GAME_4_SCORE_MAX = 99.99
GAME_4_RANGE_WIDTH = 2.0
GAME_4_RANGE_COUNT = 3
_GAME4_PICKER_DIR = Path(__file__).with_name("game4_picker")
_game4_picker_component = components.declare_component(
    "game4_range_picker", path=str(_GAME4_PICKER_DIR)
)


def _reset_game_4_state() -> None:
    for key in (
        "game_4_bet",
        "game_4_round_id",
        "selected_news_game_4",
        "candidates_game_4",
        "read_done_game_4",
        "game_4_range",
        "game_4_range_picker",
        "game4_picker_round",
        "game4_reveal_done",
        "game_4_summary",
        "game_4_score_details",
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


def _render_game_4_range_picker(
    ranges: list[str], balance: int, *, selected_index: int | None = None,
    actual_score: float | None = None, answer_index: int | None = None,
) -> int | str | None:
    """Show the entire selection screen in one viewport-sized component.

    Native Streamlit columns/radio controls have minimum widths which are
    incompatible with this two-panel mobile layout. The standalone frontend
    owns all placement; only a confirmed, round-bound index reaches Python.
    """
    round_key = "game4_picker_round"
    if round_key not in st.session_state:
        st.session_state[round_key] = uuid4().hex
    round_id = st.session_state[round_key]
    asset_root = Path(__file__).resolve().parents[1] / "assets"
    artwork = {
        "background": load_local_image_url(str(asset_root / "bet_background.jpg")),
        "logo": load_local_image_url(str(asset_root / "bet_crown.png")),
        "laurel_left": load_local_image_url(
            str(asset_root / "game1_article/icons/laurel-left.png")
        ),
        "laurel_right": load_local_image_url(
            str(asset_root / "game1_article/icons/laurel-right.png")
        ),
    }

    revealing = (
        selected_index is not None and actual_score is not None
        and answer_index is not None
    )
    reveal_payload = {
        "score": f"{actual_score:.2f}",
        "answer_index": int(answer_index),
        "selected_index": int(selected_index),
    } if revealing else None

    with st.container(key="game4-picker-stage"):
        st.html("""
            <style>
            .st-key-game4-picker-stage {
                position: fixed; inset: 0; z-index: 1000;
                width: 100%; height: 100vh; height: 100dvh;
                overflow: hidden; background: #160622;
            }
            .st-key-game4-picker-stage iframe {
                display: block; border: 0; width: 100%;
                height: 100vh !important; height: 100dvh !important;
            }
            [data-testid="stApp"]:has(.st-key-game4-picker-stage)
            [data-testid="stHeader"] { display: none; }
            [data-testid="stMain"]:has(.st-key-game4-picker-stage) {
                overflow: hidden;
            }
            </style>
        """)
        event = _game4_picker_component(
            key=f"game4-picker-{round_id}",
            round_id=round_id,
            ranges=ranges,
            coins=int(balance),
            art=artwork,
            reveal=reveal_payload,
            default=None,
        )

    if not isinstance(event, dict) or event.get("round_id") != round_id:
        return None
    action = event.get("action")
    if action in ("back", "bank") and not revealing:
        st.session_state.pop(round_key, None)
        change_page("main" if action == "back" else "bank")
    elif action == "choose" and not revealing:
        index = event.get("index")
        if type(index) is int and 0 <= index < len(ranges):
            # Preserve the component instance across settlement and reveal.
            return index
    elif action == "reveal_complete" and revealing:
        return "reveal_complete"
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


@st.dialog("AI 판정 근거 · 점수 시각화")
def _show_game_4_evidence() -> None:
    """Inspect the saved input and score, not a newly generated model result."""
    result = st.session_state.get("game_4_result") or {}
    details = result.get("score_details") or {}
    st.markdown("**기사 제목**")
    st.write(result.get("title") or "기사 제목 정보 없음")
    st.markdown("**AI 요약문**")
    st.write(result.get("summary") or "저장된 AI 요약문이 없다.")
    st.metric("최종 일치율", f"{result.get('actual_score', 0):.2f}%")
    st.write(f"내가 선택한 구간: **{result.get('selected_range', '—')}**")
    st.write(f"정답 구간: **{result.get('target_range', '—')}**")
    if all(key in details for key in ("model_name", "token_count", "logit", "normalized")):
        st.caption(
            f"모델: {details['model_name']} · 입력 토큰 {details['token_count']}개"
        )
        st.write(
            f"관련성 원점수(logit): {details['logit']:.4f} · "
            f"시그모이드 변환값: {details['normalized']:.6f}"
        )
        st.html(
            '<style>.g4-evidence-chart{max-width:100%}'
            'img.score-diagram{width:100%;max-width:440px;height:auto;display:block;margin:auto}</style>'
        )
        st.html(_score_diagram(details, False))
    else:
        st.caption("이 라운드의 AI 세부 계산값은 저장되어 있지 않다.")
    st.caption(
        "이 자료는 입력 문장과 모델 점수의 산출 과정을 보여준다. "
        "개별 표현이 판단에 미친 인과적 이유를 증명하지는 않는다."
    )
    if st.button("결과로 돌아가기", key="game4_evidence_close", use_container_width=True):
        st.rerun()


def _show_game_4_result() -> None:
    result = st.session_state.game_4_result
    if not apply_end_of_turn_interest("game_4"):
        return

    # The animation already happened in the original three-range picker.
    # This is an immediate, non-animated outcome screen.
    st.html(Path(__file__).with_name("game4_picker.css"))
    score_text = f"{result['actual_score']:.2f}%"
    with st.container(key="game4_result_shell"):
        st.html(
            '<section class="g4-result-scene" aria-label="최종 일치율과 결과">'
            '<div class="g4-result-heading">최종 결과</div>'
            '<div class="g4-reel-window">'
            f'<strong class="g4-final-value">{escape(score_text)}</strong>'
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
            if st.button(
                "판정 근거 · 점수 그래프 보기",
                key="game4_result_evidence",
                use_container_width=True,
            ):
                _show_game_4_evidence()

            col_retry, col_main = st.columns(2)
            with col_retry:
                if st.button("다시 도전하기", key="game4_result_retry", use_container_width=True):
                    _reset_game_4_state()
                    st.rerun()
            with col_main:
                if st.button("메인으로", key="game4_result_main", use_container_width=True):
                    _reset_game_4_state()
                    change_page("main")


def show_game_4_tutorial() -> None:
    """Game 1-style illustrated guide, shown before a new Game 4 wager."""
    art_dir = Path(__file__).resolve().parents[1] / "assets" / "game4_guide"
    steps = (
        ("bet", "코인 베팅", "금액을 정하고 베팅한다.<br>최소 <b>1,000 C</b>"),
        ("news", "기사 선택", "룰렛에서 기사 한 편을 선택하고<br><b>30초</b> 동안 읽는다."),
        ("range", "구간 예측", "2%p 폭의 <b>세 구간</b> 중<br>일치율이 들어갈 곳을 고른다."),
        ("result", "결과 확인", "정답이면 베팅액의 <b>3배 추가</b><br>오답이면 <b>베팅액 차감</b>"),
    )
    cards = "".join(
        f'<li><h2><span>{number:02d}</span>{title}</h2>'
        f'<img src="{load_local_image_url(str(art_dir / (name + ".svg")))}" '
        f'alt="{title} 단계의 게임 화면을 표현한 그림">'
        f'<p>{caption}</p></li>'
        for number, (name, title, caption) in enumerate(steps, 1)
    )
    with st.container(key="game4-guide", gap=None):
        st.html(Path(__file__).with_name("game4_tutorial.css"))
        with st.container(key="game4-guide-nav", horizontal=True, gap=None):
            if st.button("메인으로", key="game4-guide-back"):
                change_page("main")
            if st.button("건너뛰기", key="game4-guide-skip"):
                change_page("game_4")
        st.html(f"""
            <section class="game4-guide-sheet" aria-labelledby="game4-guide-title" lang="ko">
                <header class="game4-guide-heading">
                    <span>GAME 04</span><h1 id="game4-guide-title">일치율 구간 맞히기</h1>
                    <p>기사 제목과 AI 요약문은 얼마나 비슷할까?<br>
                    예상 일치율 구간을 선택해 보자.</p>
                </header>
                <ol aria-label="게임 진행 순서" role="list">{cards}</ol>
            </section>
        """)
        if st.button(
            "베팅하러 가기", key="game4-guide-start", type="primary", width="stretch"
        ):
            change_page("game_4")


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
                score_details = similarity_check(summary_text, title)
                score = _normalize_score(score_details["score"])
                ranges, answer_index = _build_dynamic_ranges(score)
            except (RuntimeError, ValueError, TypeError, KeyError) as exc:
                st.error(f"일치율 구간을 준비하지 못했습니다: {exc}")
                return
        st.session_state.game_4_summary = summary_text
        st.session_state.game_4_score_details = score_details
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
        result["title"] = title
        result["summary"] = st.session_state.get("game_4_summary", "")
        result["score_details"] = st.session_state.get("game_4_score_details", {})
        st.session_state.game_4_result = result

    # Reveal only after the wallet was settled and end-of-turn interest applied.
    # The animation runs in the *same* picker used for the player's choice.
    if not st.session_state.get("game4_reveal_done", False):
        if not apply_end_of_turn_interest("game_4"):
            return
        state = st.session_state
        event = _render_game_4_range_picker(
            state.game_4_ranges,
            int((state.get("current_user_data") or {}).get("코인", 0)),
            selected_index=state.game_4_range,
            actual_score=state.game_4_result["actual_score"],
            answer_index=state.game_4_answer_index,
        )
        if event == "reveal_complete":
            state.game4_reveal_done = True
            state.pop("game4_picker_round", None)
            st.rerun()
        return

    _show_game_4_result()

