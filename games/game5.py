"""제시된 일치율 구간에 해당하는 뉴스를 고르는 게임."""

import asyncio
from decimal import Decimal, ROUND_HALF_UP
import math
import random
from pathlib import Path
from uuid import uuid4

import streamlit as st
import streamlit.components.v1 as components

from games.shared.betting import check_user_coins_or_pop_bank
from games.shared.betting import render_betting_ui
from games.shared.loading import similarity_analysis_loading
from modules.db_handler import deferred_news_sheet, news_row_is_active, normalize_article_url
from modules.article_failures import excluded_article_urls, report_article_failure
from games.shared.interest import apply_end_of_turn_interest
from modules.transactions import BalanceChanged, TransactionError, settle_game_round, update_session_balances
from modules.news_ai import bring_article, pick_lowest_count_news, similarity_check, summary
from modules.ui_components import change_page
from views.ranking import fetch_ranking_data


GAME_5_WIN_MULTIPLIER = 5.0
GAME_5_MIN_BET = 1000
GAME_5_SCORE_MAX = 99.99
GAME_5_TARGET_RANGE_WIDTH = 2.0
_GAME5_CANDIDATE_DIR = Path(__file__).with_name("game5_ui") / "candidates"
_game5_candidate_component = components.declare_component(
    "game5_candidate_picker", path=str(_GAME5_CANDIDATE_DIR)
)

ws_news = deferred_news_sheet()


def _reset_game_5_state() -> None:
    for key in (
        "game_5_bet",
        "game_5_round_id",
        "game_5_target_range",
        "game_5_answer_index",
        "game_5_candidates",
        "game_5_selected_index",
        "game_5_pending_selection",
        "game_5_result",
        "game_5_article_index",
        "game_5_summary_revealed",
        "game_5_reader_round",
        "bet_slider_val",
        "game5_candidate_round",
    ):
        st.session_state.pop(key, None)


def _load_candidates(excluded_urls: set[str] | None = None, *, limit: int = 5) -> list[dict]:
    excluded_urls = {normalize_article_url(url) for url in (excluded_urls or set())}
    excluded_urls.update(excluded_article_urls())
    records = ws_news.get_all_records()
    news_list = []
    for row_index, item in enumerate(records, start=2):
        url = normalize_article_url(item.get("URL", ""))
        title = str(item.get("Title", "")).strip()
        if not url or not title or url in excluded_urls or not news_row_is_active(item):
            continue
        try:
            count = int(float(item.get("Count", 0) or 0))
        except (TypeError, ValueError):
            count = 0
        news_list.append({"url": url, "title": title, "count": count, "row_idx": row_index})

    candidates = pick_lowest_count_news(news_list, limit)
    if len(candidates) < limit:
        raise ValueError(f"게임 5에 필요한 뉴스 후보가 {limit}개 미만입니다.")

    return [{**item, "text": ""} for item in candidates]


@st.cache_data(ttl=3600, show_spinner=False)
def _extract_article(url: str) -> tuple[str, str]:
    return bring_article(url)


@st.cache_data(ttl=3600, show_spinner=False)
def _analyze_article_cached(article_text: str, title: str) -> dict:
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
    actual_score = max(0.0, min(float(normalized_score), GAME_5_SCORE_MAX))
    normalized_details = dict(score_details)
    normalized_details["score"] = actual_score
    normalized_details.setdefault("score_hundredths", int(actual_score * 100))
    return {
        "summary": summary_text,
        "score_details": normalized_details,
        "actual_score": actual_score,
    }


def _load_article(article: dict) -> None:
    try:
        title, text = _extract_article(article["url"])
        if not str(title or "").strip() or not str(text or "").strip():
            raise ValueError("제목 또는 본문이 비어 있는 뉴스가 후보에 포함되어 있습니다.")
    except Exception as exc:
        report_article_failure(article["url"], exc)
        raise RuntimeError(f"뉴스 본문을 불러오지 못했습니다: {exc}") from exc
    article["title"] = title
    article["text"] = text


def _calculate_score(article: dict) -> float:
    analysis = _analyze_article_cached(article["text"], article["title"])
    article["summary"] = analysis["summary"]
    article["score_details"] = analysis["score_details"]
    article["score"] = analysis["actual_score"]
    return analysis["actual_score"]


def _replace_candidate(candidates: list[dict], index: int) -> None:
    excluded_urls = {candidate["url"] for candidate in candidates}
    replacements = _load_candidates(excluded_urls, limit=1)
    if not replacements:
        raise ValueError("교체할 수 있는 뉴스 후보가 없습니다.")
    candidates[index] = replacements[0]


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


def _confirm_article_selection(index: int) -> None:
    candidates = st.session_state.get("game_5_candidates", [])
    if not 0 <= index < len(candidates):
        st.error("선택할 뉴스 정보를 찾을 수 없습니다.")
        return

    st.markdown(
        """
        <style>
        .st-key-game5-confirm-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            z-index: 2147483000;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 16px;
            margin: 0;
            background: rgba(8, 3, 20, .82);
            backdrop-filter: blur(5px);
        }
        .st-key-game5-confirm-overlay > div {
            width: auto;
            max-width: 100%;
            display: flex;
            justify-content: center;    
        }
        .st-key-game5-confirm-overlay [data-testid="stVerticalBlockBorderWrapper"] {
            width: min(420px, calc(100vw - 32px));
            max-width: 420px;
            border: 2px solid #a94ce0;
            border-radius: 18px;
            background: #1b0b2b;
            box-shadow: 0 18px 60px rgba(0,0,0,.55);
            padding: 20px 18px;
            margin: auto;
        }
        .st-key-game5-confirm-overlay [data-testid="stHorizontalBlock"] {
            display: flex;
            flex-direction: row;
            flex-wrap: nowrap;
            gap: 16px;
        }
        .st-key-game5-confirm-overlay [data-testid="column"],
        .st-key-game5-confirm-overlay [data-testid="stColumn"] {
            flex: 1 1 50%;
            width: 50%;
            min-width: 0;
        }
        .st-key-game5-confirm-overlay [data-testid="stButton"] button {
            white-space: nowrap;
            overflow: hidden;
            text-overflow: clip;
            min-width: 0;
        }
        @media (max-width: 480px) {
            .st-key-game5-confirm-overlay [data-testid="stHorizontalBlock"] {
                gap: 12px;
            }
            .st-key-game5-confirm-overlay [data-testid="stVerticalBlockBorderWrapper"] {
                width: min(420px, calc(100vw - 24px));
                padding: 16px 12px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container(key="game5-confirm-overlay", border=True):
        st.markdown(f"### 후보 {index + 1}을 정답으로 결정할까요?")
        st.caption(candidates[index]["title"])
        confirm_col, cancel_col = st.columns(2)
        with confirm_col:
            if st.button("결정하기", key="game_5_confirm_selection", use_container_width=True):
                st.session_state.game_5_selected_index = index
                st.session_state.pop("game_5_pending_selection", None)
                st.session_state.pop("game_5_result", None)
                st.session_state.page = "game_5_result"
                st.rerun(scope="app")
        with cancel_col:
            if st.button("다시 보기", key="game_5_cancel_selection", use_container_width=True):
                st.session_state.pop("game_5_pending_selection", None)
                st.rerun(scope="app")


def _show_article_detail() -> None:
    from games.shared.article_reader import render_article_reader

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
    action = render_article_reader(
        article,
        game_id="game_5",
        reward=int(st.session_state.get("game_5_bet", 0)) * int(GAME_5_WIN_MULTIPLIER),
        guidance="본문을 확인한 뒤 후보 목록으로 돌아가 정답 구간에 해당하는 뉴스를 결정하세요.",
        return_label="후보 목록으로 돌아가기",
    )
    if action == "predict":
        st.session_state.pop("game_5_article_index", None)
        change_page("game_5")
    elif action == "bank":
        change_page("bank")


def _show_result() -> None:
    from games.shared.result import show_summary_before_score
    import streamlit.components.v1 as components

    components.html(
        "<script>try{window.parent.scrollTo({top:0,left:0,behavior:'instant'})}catch(e){}</script>",
        height=0,
        width=0,
    )

    st.markdown(
        """
        <style>
        .stApp:has(.st-key-game5-result-shell) {
            overflow-x: hidden;
        }
        .block-container:has(.st-key-game5-result-shell) {
            max-width: 690px !important;
            margin-inline: auto !important;
        }
        .st-key-game5-result-shell {
            width: 100%;
            min-height: 70vh;
        }
        .st-key-game5-result-shell [data-testid="stVerticalBlockBorderWrapper"] {
            border: 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    result = st.session_state.get("game_5_result")
    if not result:
        candidates = st.session_state.get("game_5_candidates", [])
        target_range = st.session_state.get("game_5_target_range")
        selected_index = st.session_state.get("game_5_selected_index")
        if not isinstance(selected_index, int) or not 0 <= selected_index < len(candidates):
            change_page("game_5")
            return
        if not isinstance(target_range, (list, tuple)) or len(target_range) != 2:
            change_page("game_5")
            return

        selected_article = candidates[selected_index]
        with similarity_analysis_loading():
            try:
                if "score" not in selected_article or not selected_article.get("text"):
                    _load_article(selected_article)
                    selected_article["score"] = _calculate_score(selected_article)
                actual_score = float(selected_article["score"])
                is_win = target_range[0] <= actual_score <= target_range[1]
                bet_coin = int(st.session_state.game_5_bet)
                settled = settle_game_round("game_5", bet_coin, is_win)
            except BalanceChanged as changed:
                update_session_balances(changed.balances)
                st.error(str(changed))
                return
            except (RuntimeError, ValueError, TypeError, TransactionError) as exc:
                st.error(f"결과를 계산하지 못했습니다: {exc}")
                return

        st.session_state.game_5_result = {
            "title": selected_article["title"],
            "summary": selected_article.get("summary", ""),
            "score_details": selected_article.get("score_details"),
            "actual_score": actual_score,
            "target_range": _format_score_range(target_range),
            "reward": settled["reward"],
            "is_win": is_win,
            "new_coins": settled["new_coins"],
            "new_streak": settled["new_streak"],
        }
        st.rerun()
        return
    if not apply_end_of_turn_interest("game_5"):
        return

    with st.container(key="game5-result-shell"):
        show_summary_before_score(
            result.get("summary", ""),
            "game_5_summary_revealed",
            title=result.get("title", ""),
            score=result["actual_score"],
            details=result.get("score_details"),
            score_precision=2,
        )
        st.title("🏆 게임 5 최종 결과")
        if result["is_win"]:
            st.balloons()
            st.success(f"🎉 정답입니다! +{result['reward']:,} C")
        else:
            st.error(f"❌ 틀렸습니다! {result['reward']:,} C")
        metric_col, range_col = st.columns(2)
        with metric_col:
            st.metric("선택한 뉴스의 실제 일치율", f"{result['actual_score']:.2f}%")
        with range_col:
            st.metric("정답 구간", result["target_range"])
        st.markdown(
            f"""
            <div style="background:#110022; border:2px solid #8A2BE2; padding:15px;
                        border-radius:10px; text-align:center; margin:15px 0;">
                <p style="color:#ffffff; margin:0; font-weight:bold;">
                    현재 보유 코인: <span style="color:#00ffcc;">{result['new_coins']:,} C</span>
                </p>
                <p style="color:#ffffff; margin:0; font-weight:bold;">
                    현재 연승 기록: <span style="color:#ff00ff;">{result['new_streak']} 연승</span>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_retry, col_main = st.columns(2)
        with col_retry:
            if st.button("🔄 다시 도전하기", use_container_width=True):
                _reset_game_5_state()
                change_page("game_5")
        with col_main:
            if st.button("⬅️ 메인으로 돌아가기", use_container_width=True):
                _reset_game_5_state()
                change_page("main")


def _render_game5_candidate_picker(candidates: list[dict], target_range: tuple[float, float]) -> None:
    round_id = st.session_state.get("game5_candidate_round")
    if not isinstance(round_id, str):
        round_id = uuid4().hex
        st.session_state.game5_candidate_round = round_id

    user_data = st.session_state.get("current_user_data") or {}
    balance = int(user_data.get("코인", 0))
    event = _game5_candidate_component(
        key=f"game5-candidates-{round_id}",
        round_id=round_id,
        range_text=_format_score_range(target_range),
        coins=balance,
        titles=[str(article.get("title", "")) for article in candidates],
        default=None,
    )

    if not isinstance(event, dict) or event.get("round_id") != round_id:
        return

    action = event.get("action")
    if action in ("back", "bank"):
        change_page("main" if action == "back" else "bank")
        return
    index = event.get("index")
    if type(index) is not int or not 0 <= index < len(candidates):
        return

    if action == "read":
        article = candidates[index]
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
                        return
                    st.warning(f"실패한 기사를 교체했습니다: {exc}")
                    st.rerun()
                    return
        st.session_state.game_5_article_index = index
        change_page("game_5_article")
    elif action == "select":
        st.session_state.game_5_pending_selection = index
        st.rerun(scope="app")


def show_game_5():
    if "game_5_bet" not in st.session_state:
        if not check_user_coins_or_pop_bank(GAME_5_MIN_BET):
            return

        user_data = st.session_state.get('current_user_data', {})
        current_coins = int(user_data.get('코인', 0))
        current_sid = str(st.session_state.get('current_user', ''))
        current_nickname = str(user_data.get('아이디', ''))
        try:
            users_data = fetch_ranking_data()
        except Exception:
            users_data = None
        
        confirmed_bet = render_betting_ui(
            current_coins=current_coins,
            users_data=users_data,
            current_sid=current_sid,
            current_nickname=current_nickname,
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
    pending_index = st.session_state.get("game_5_pending_selection")
    if isinstance(pending_index, int):
        _confirm_article_selection(pending_index)
        return

    with st.container(key="game5-candidate-picker-stage"):
        st.html("""
        <style>
        .st-key-game5-candidate-picker-stage {
            position: fixed; inset: 0; z-index: 1000;
            width: 100%; height: 100vh; height: 100dvh;
            overflow: hidden; background: #160622;
        }
        .st-key-game5-candidate-picker-stage iframe {
            display: block; border: 0; width: 100%;
            height: 100vh !important; height: 100dvh !important;
        }
        [data-testid="stApp"]:has(.st-key-game5-candidate-picker-stage) [data-testid="stHeader"] {
            display: none;
        }
        [data-testid="stMain"]:has(.st-key-game5-candidate-picker-stage) {
            overflow: hidden;
        }
        </style>
        """)
        _render_game5_candidate_picker(candidates, target_range)



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
                        <h2><span>02</span>구간 확인</h2>
                        <div class="game5-guide-icon">%</div>
                        <p>정답 뉴스가 포함되는<br>일치율 구간이 제시된다.</p>
                    </li>
                    <li>
                        <h2><span>03</span>뉴스 선택</h2>
                        <div class="game5-guide-icon">?</div>
                        <p>후보 뉴스 <b>5개</b>를 읽고<br>구간에 해당할 것 같은<br>뉴스를 선택한다.</p>
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
