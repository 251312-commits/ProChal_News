"""제시된 일치율 구간에 해당하는 뉴스를 고르는 게임."""

import asyncio
import random

import streamlit as st

from games.common import check_user_coins_or_pop_bank, render_betting_ui
from modules.db_handler import init_gspread, init_news_sheet
from modules.news_ai import bring_article, pick_3_lowest_count_news, similarity_check, summary
from modules.ui_components import change_page
from views.ranking import fetch_ranking_data


GAME_5_WIN_MULTIPLIER = 5.0
GAME_5_MIN_BET = 1000

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
        "bet_slider_val",
    ):
        st.session_state.pop(key, None)


def _load_candidates() -> list[dict]:
    records = ws_news.get_all_records()
    news_list = []
    for row_index, item in enumerate(records, start=2):
        url = str(item.get("URL", "")).strip()
        title = str(item.get("Title", "")).strip()
        if not url or not title:
            continue
        try:
            count = int(float(item.get("Count", 0) or 0))
        except (TypeError, ValueError):
            count = 0
        news_list.append({"url": url, "title": title, "count": count, "row_idx": row_index})

    candidates = pick_3_lowest_count_news(news_list)
    if len(candidates) < 3:
        raise ValueError("게임 5에 필요한 뉴스 후보가 3개 미만입니다.")

    loaded = []
    for item in candidates:
        try:
            title, text = bring_article(item["url"])
        except Exception as exc:
            raise RuntimeError(f"뉴스 본문을 불러오지 못했습니다: {exc}") from exc
        if not title or not text:
            raise ValueError("제목 또는 본문이 비어 있는 뉴스가 후보에 포함되어 있습니다.")
        article = {**item, "title": title, "text": text}
        article["score"] = _calculate_score(article)
        loaded.append(article)
    return loaded


def _calculate_score(article: dict) -> float:
    summary_text = asyncio.run(summary(article["text"]))
    if not summary_text:
        raise ValueError("뉴스 본문 요약 결과가 비어 있습니다.")
    score_details = similarity_check(summary_text, article["title"])
    score = score_details.get("score")
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        raise ValueError("뉴스 일치율 결과가 올바른 숫자가 아닙니다.")
    return float(score)


def _build_exclusive_range(candidates: list[dict], answer_index: int) -> tuple[int, int]:
    """Build the widest integer range containing only the selected score."""
    answer_score = candidates[answer_index]["score"]
    other_scores = {
        candidate["score"]
        for index, candidate in enumerate(candidates)
        if index != answer_index
    }
    if answer_score in other_scores:
        raise ValueError("후보 뉴스의 일치율이 같아 정답 구간을 분리할 수 없습니다.")

    lower_scores = [score for score in other_scores if score < answer_score]
    upper_scores = [score for score in other_scores if score > answer_score]
    lower = max(lower_scores, default=0) + (1 if lower_scores else 0)
    upper = min(upper_scores, default=100) - (1 if upper_scores else 0)
    if lower > answer_score or answer_score > upper:
        raise ValueError("후보 뉴스의 일치율로 정답 구간을 만들 수 없습니다.")
    return lower, upper


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
        )
        if confirmed_bet is not None:
            st.session_state.game_5_bet = confirmed_bet
            st.rerun()
        return

    if "game_5_candidates" not in st.session_state:
        with st.spinner("📰 뉴스 후보를 준비하는 중입니다..."):
            try:
                candidates = _load_candidates()
                unique_score_indices = [
                    index
                    for index, candidate in enumerate(candidates)
                    if sum(other["score"] == candidate["score"] for other in candidates) == 1
                ]
                if not unique_score_indices:
                    raise ValueError(
                        "후보 뉴스의 일치율이 모두 겹쳐 정답 구간을 만들 수 없습니다."
                    )
                answer_index = random.choice(unique_score_indices)
                target_range = _build_exclusive_range(candidates, answer_index)
            except (RuntimeError, ValueError, TypeError) as exc:
                st.error(f"뉴스 후보를 준비하지 못했습니다: {exc}")
                return

        st.session_state.game_5_candidates = candidates
        st.session_state.game_5_answer_index = answer_index
        st.session_state.game_5_target_range = target_range
        st.rerun()

    candidates = st.session_state.game_5_candidates
    target_range = st.session_state.game_5_target_range
    st.info(
        f"🎯 정답 일치율 구간: **{target_range[0]}~{target_range[1]}%**\n\n"
        "아래 뉴스 중 이 구간에 해당하는 뉴스 하나를 선택하세요."
    )

    for index, article in enumerate(candidates):
        with st.container(border=True):
            st.subheader(f"📰 후보 {index + 1}: {article['title']}")
            st.write(article["text"])
            if st.button(
                f"후보 {index + 1} 선택",
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
        with st.spinner("🤖 선택한 뉴스의 일치율을 분석 중입니다..."):
            try:
                actual_score = _calculate_score(selected_article)
            except (RuntimeError, ValueError, TypeError) as exc:
                st.error(f"일치율을 계산하지 못했습니다: {exc}")
                return

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
            "target_range": f"{target_range[0]}~{target_range[1]}%",
            "reward": reward,
            "is_win": is_win,
            "new_coins": new_coins,
            "new_streak": new_streak,
        }

    result = st.session_state.game_5_result
    st.markdown("---")
    st.subheader("🏆 최종 결과")
    if result["is_win"]:
        st.balloons()
        st.success(f"🎉 정답입니다! +{result['reward']:,} C")
    else:
        st.error(f"❌ 틀렸습니다! {result['reward']:,} C")
    st.metric("선택한 뉴스의 실제 일치율", f"{result['actual_score']}%")
    st.info(f"정답 구간: {result['target_range']}")
    st.write(f"현재 보유 코인: **{result['new_coins']:,} C**")
    st.write(f"현재 연승 기록: **{result['new_streak']} 연승**")

    col_retry, col_main = st.columns(2)
    with col_retry:
        if st.button("🔄 다시 도전하기", use_container_width=True):
            _reset_game_5_state()
            st.rerun()
    with col_main:
        if st.button("⬅️ 메인으로 돌아가기", use_container_width=True):
            _reset_game_5_state()
            change_page("main")
