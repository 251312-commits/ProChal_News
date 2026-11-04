"""Shared AI-summary typewriter reveal, shown before any game score.

The summary is already generated and scored before this UI runs; the animation
only controls what the player sees, and never re-runs a wager or sheet update.
"""

from html import escape
import re
import time


_WORD = re.compile(r"([^\W_]+)")
_STYLE = """
<style>
.st-key-news_comparison {
    padding: clamp(.85rem, 3vw, 1.35rem);
    border: 1px solid #685184; border-radius: 14px;
    background: linear-gradient(145deg, #241631, #110d1d);
    gap: .45rem;
}
.st-key-news_comparison .news-label {
    color: #ccb9e6; font-size: .82rem; font-weight: 700;
}
.st-key-news_comparison .news-copy {
    color: #fff6ff; line-height: 1.6; white-space: pre-wrap;
    overflow-wrap: anywhere;
}
.st-key-news_comparison .news-message {
    border-left: 3px solid #a589d9; border-radius: 0 10px 10px;
    background: #30233e; padding: .6rem .85rem;
}
.st-key-news_comparison mark {
    background: #f8d98b; color: #271a09; border-radius: .18em;
}
.st-key-news_comparison [data-testid="stCaptionContainer"] p,
.st-key-news_comparison .stProgress p { color: #e7def0; }
@media (prefers-reduced-motion: no-preference) {
    .st-key-news_comparison .news-scan mark { animation: news-ink .45s ease-out; }
    @keyframes news-ink {
        from { background-color: transparent; color: #fff6ff; }
        to { background-color: #f8d98b; color: #271a09; }
    }
}
</style>
"""


def _marked_text(text, shared):
    """Preserve the supplied text and mark only whole, literal matches."""
    return "".join(
        f"<mark>{escape(part)}</mark>" if part in shared else escape(part)
        for part in _WORD.split(text)
    )


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


def show_summary_before_score(summary_text: str, state_key: str, *, title: str, score: int) -> None:
    """Reveal the two model inputs, then the stored score, once per round."""
    import streamlit as st

    text = str(summary_text or "").strip()
    if not text:
        return

    title_words = {word for word in _WORD.findall(title) if len(word) >= 2}
    shared = title_words.intersection(_WORD.findall(text))
    score = int(score)
    reveal = (title, text, score)
    animate = st.session_state.get(state_key) != reveal

    with st.container(key="news_comparison"):
        st.html(_STYLE)
        st.html('<div class="news-label">기사 제목</div>')
        headline = st.empty()
        st.html('<div class="news-label">AI 요약문</div>')
        message = st.empty()

        if animate:
            headline.html(f'<div class="news-copy">{escape(title)}</div>')
            # Stream plain text so even Markdown-like news is displayed literally.
            partial = []
            next_frame = 0.0
            for letter in type_summary_characters(text):
                partial.append(letter)
                now = time.monotonic()
                if now >= next_frame:
                    message.html(
                        f'<div class="news-copy news-message">{escape("".join(partial))}'
                        '<span aria-hidden="true">▍</span></div>'
                    )
                    next_frame = now + 0.03

        effect = " news-scan" if animate else ""
        headline.html(f'<div class="news-copy{effect}">{_marked_text(title, shared)}</div>')
        message.html(f'<div class="news-copy news-message{effect}">{_marked_text(text, shared)}</div>')
        if shared:
            st.caption("금색은 두 글에 똑같이 나온 낱말이다. 점수는 AI가 두 글의 의미를 비교해 매긴다.")
        else:
            st.caption("같은 표기의 낱말(두 글자 이상)은 없다. AI는 두 글의 의미를 비교해 점수를 매긴다.")

        if animate:
            time.sleep(0.8)  # Give the player a beat to compare the texts before the score.
        st.progress(score, text=f"AI 유사도 · {score} / 100점")
        st.session_state[state_key] = reveal
