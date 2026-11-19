"""Shared full-screen news slot and timed reader for games 1–4."""
import streamlit as st

from games.shared.betting import calculate_expected_gain
from games.shared.article_reader import render_article_reader
from games.shared.roulette import render_news_slot
from modules.news_ai import bring_article, pick_3_lowest_count_news
from modules.article_failures import excluded_article_urls, report_article_failure
from modules.db_handler import (
    LAST_ARTICLE_HEADER,
    deferred_user_sheet,
    deferred_news_sheet,
    news_row_is_active,
    normalize_article_url,
    save_last_article_url,
)
from modules.ui_components import change_page


ws_news = deferred_news_sheet()
ws_users = deferred_user_sheet()


def _current_student_id():
    state = st.session_state
    user = state.get("current_user_data") or {}
    return str(state.get("current_user") or user.get("학번") or "").strip().removesuffix(".0")


def _remember_article(url):
    state = st.session_state
    canonical = normalize_article_url(url)
    user = state.get("current_user_data")
    if isinstance(user, dict):
        user[LAST_ARTICLE_HEADER] = canonical
    try:
        save_last_article_url(ws_users, _current_student_id(), canonical)
    except Exception:
        # A sheet metadata write must not prevent the selected article from opening.
        pass



def _get_news_candidates(candidates_key):
    if candidates_key not in st.session_state:
        with st.spinner("기사 후보를 확인하는 중…"):
            raw_records = ws_news.get_all_records()
        news_data = []
        state = st.session_state
        user = state.get("current_user_data") or {}
        current_sid = _current_student_id()
        last_seen = normalize_article_url(user.get(LAST_ARTICLE_HEADER, ""))

        excluded = excluded_article_urls()
        with st.spinner("🎰 슬롯머신 기사 추천 중..."):
            for idx, row in enumerate(raw_records):
                url = str(row.get('URL', '')).strip()
                if not url or not news_row_is_active(row):
                    continue
                canonical = normalize_article_url(url)
                if canonical in excluded:
                    continue
                if last_seen and canonical == last_seen:
                    continue
                submitted_by = str(row.get("SubmittedBy", "") or "").strip().removesuffix(".0")
                if current_sid and submitted_by == current_sid:
                    continue
                try:
                    count = int(row.get('Count', 0))
                except (TypeError, ValueError):
                    count = 0
                title = str(row.get('Title', '')).strip()

                if not title or title == "None":
                    try:
                        title, _ = bring_article(url)
                        ws_news.update_cell(idx + 2, 3, title)
                    except Exception:
                        title = f"뉴스 기사 #{idx+1}"

                news_data.append({
                    'row_idx': idx + 2,
                    'url': canonical,
                    'count': count,
                    'title': title,
                    'submitted_by': submitted_by,
                    'source_type': str(row.get("SourceType", "") or "base").strip() or "base",
                })

        if not news_data:
            st.warning("구글 시트 'News' 탭에 등록된 뉴스 URL이 없습니다.")
            return []

        st.session_state[candidates_key] = pick_3_lowest_count_news(news_data)

    return st.session_state[candidates_key]


def _open_chosen_article(item, news_key, candidates_key):
    with st.spinner("선택 기사 읽어오는 중..."):
        try:
            title, clean_text, image_url = bring_article(item["url"], include_image=True)
            if not str(title or "").strip() or not str(clean_text or "").strip():
                raise ValueError("기사 제목 또는 본문이 비어 있습니다.")
        except Exception as exc:
            # The confirmed bet survives a broken article; choose another.
            report_article_failure(item["url"], exc)
            st.session_state.pop(candidates_key, None)
            st.session_state[f"{news_key}_load_error"] = (
                "선택한 기사를 불러오지 못해 후보에서 제외했다. 다른 기사를 선택해 주세요."
            )
            st.rerun()
            return

    # A view is counted only after article text was obtained successfully.
    # Metadata write failures should not discard a readable article.
    with st.spinner("기사 선택을 저장하는 중…"):
        try:
            ws_news.update_cell(item['row_idx'], 2, item['count'] + 1)
        except Exception:
            pass

    st.session_state[news_key] = {
        "title": title, "text": clean_text, "url": item["url"],
        "image_url": image_url,
    }
    _remember_article(item['url'])
    del st.session_state[candidates_key]
    st.rerun()



def get_game_news_selection(game_id: str, *, win_multiplier=None):
    """Return title, body and URL after the shared timed reader finishes.

    Before then each rerun returns (None, None, None). Candidates and reader
    events are keyed per game/round to prevent stale iframe actions.
    """
    news_key = f"selected_news_{game_id}"
    candidates_key = f"candidates_{game_id}"
    read_done_key = f"read_done_{game_id}"

    if st.session_state.get(read_done_key, False):
        chosen = st.session_state.get(news_key)
        if chosen:
            return chosen["title"], chosen["text"], chosen["url"]
        st.session_state.pop(read_done_key, None)

    notice = st.session_state.pop(f"{news_key}_load_error", None)
    if notice:
        st.toast(notice, icon="⚠️")

    chosen = st.session_state.get(news_key)
    if not chosen:
        candidates = _get_news_candidates(candidates_key)
        if candidates:
            index = render_news_slot(
                candidates, game_id=game_id, continuous_reel=True,
                allow_back=(game_id not in {"game_1", "game_3"}),
                allow_direct_url=True,
            )
            if index is not None:
                _open_chosen_article(candidates[index], news_key, candidates_key)
        return None, None, None

    reward = None
    if win_multiplier is not None:
        reward = calculate_expected_gain(st.session_state[f"{game_id}_bet"], win_multiplier)
    action = render_article_reader(chosen, game_id=game_id, reward=reward)
    if action == "predict":
        st.session_state[read_done_key] = True
        st.rerun()
    elif action == "bank":
        change_page("bank")
    return None, None, None
