"""Shared AI-summary typewriter reveal, shown before any game score.

The summary is already generated and scored before this UI runs; the animation
only controls what the player sees, and never re-runs a wager or sheet update.
"""

import time


def type_summary_characters(summary_text: str):
    """Yield each Unicode character with a short, bounded typing delay."""
    text = str(summary_text or "").strip()
    if not text:
        return

    # Keep longer summaries from delaying score reveal excessively.
    delay = min(0.032, 3.0 / len(text))
    for index, character in enumerate(text):
        yield character
        if index == len(text) - 1:
            break
        if character in ".!?。！？":
            time.sleep(min(0.12, delay * 4))
        elif character in ",，;；":
            time.sleep(min(0.07, delay * 2))
        else:
            time.sleep(delay)


def show_summary_before_score(summary_text: str, state_key: str) -> None:
    """Animate once per round; keep the full summary visible on reruns."""
    import streamlit as st

    text = str(summary_text or "").strip()
    if not text:
        return

    with st.container(border=True, key=f"{state_key}_panel"):
        st.markdown("#### 📰 AI 뉴스 요약")
        st.caption("요약문 출력이 끝나면 AI 분석 점수와 게임 결과가 공개된다.")

        # A Streamlit rerun (including a result-screen button click) must not
        # replay the animation or cause the settled result to be recalculated.
        if st.session_state.get(state_key) == text:
            st.write(text)
        else:
            st.write_stream(type_summary_characters(text))
            st.session_state[state_key] = text
