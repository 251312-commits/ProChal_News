"""Shared AI-summary typewriter reveal, shown before any game score.

The summary is already generated and scored before this UI runs; the animation
only controls what the player sees, and never re-runs a wager or sheet update.
"""

from html import escape
import time


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
.st-key-news_comparison .score-steps {
    margin: .45rem 0; padding-left: 1.65rem; color: #e7def0;
}
.st-key-news_comparison .score-steps li {
    padding: .25rem 0 .35rem .2rem; line-height: 1.5; overflow-wrap: anywhere;
}
.st-key-news_comparison .score-steps li::marker { color: #c4a7e4; font-weight: 700; }
.st-key-news_comparison .score-steps strong { color: #fff6ff; }
.st-key-news_comparison .score-steps data {
    display: inline-block; color: #f8d98b; font-variant-numeric: tabular-nums;
}
.st-key-news_comparison [data-testid="stCaptionContainer"] p,
.st-key-news_comparison .stProgress p { color: #e7def0; }
@media (prefers-reduced-motion: no-preference) {
    .st-key-news_comparison .score-reveal li { animation: score-step-in .2s ease-out backwards; }
    .st-key-news_comparison .score-reveal li:nth-child(2) { animation-delay: .22s; }
    .st-key-news_comparison .score-reveal li:nth-child(3) { animation-delay: .44s; }
    @keyframes score-step-in { from { opacity: 0; transform: translateY(.2rem); } }
}
</style>
"""


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


def show_summary_before_score(
    summary_text: str, state_key: str, *, title: str, score: int, details=None
) -> None:
    """Reveal the two model inputs, then the stored score, once per round."""
    import streamlit as st

    text = str(summary_text or "").strip()
    if not text:
        return

    score = int(score)
    reveal = (title, text, score)
    animate = st.session_state.get(state_key) != reveal

    with st.container(key="news_comparison"):
        st.html(_STYLE)
        st.html('<div class="news-label">기사 제목</div>')
        st.html(f'<div class="news-copy">{escape(title)}</div>')
        st.html('<div class="news-label">AI 요약문</div>')
        message = st.empty()

        if animate:
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

        message.html(f'<div class="news-copy news-message">{escape(text)}</div>')
        if details is not None:
            token_count = details["token_count"]
            logit = details["logit"]
            normalized = details["normalized"]
            effect = " score-reveal" if animate else ""
            st.html(f'<div class="news-label">채점 모델 · {escape(details["model_name"])}</div>')
            st.html(f"""
                <ol class="score-steps{effect}">
                  <li><strong>입력 묶기</strong> · <data value="{token_count}">{token_count}토큰</data><br>
                    AI 요약문과 기사 제목을 이 순서로 묶었다. 토큰 수에는 시작·구분 기호도 포함된다.</li>
                  <li><strong>문맥에서 관련성 읽기</strong> · <data value="{logit}">원점수 ≈ {logit:.4f}</data><br>
                    두 글의 토큰이 서로의 문맥을 반영한다. 모델의 분류층이 첫 토큰의 최종 표현에서
                    관련성 원점수(logit) 하나를 산출한다.</li>
                  <li><strong>게임 점수로 환산</strong> · <data value="{normalized}">시그모이드 값 ≈ {normalized:.4f}</data><br>
                    시그모이드 함수로 원점수를 0~1 사이로 바꾼 뒤, 100을 곱하고 반올림한다.</li>
                </ol>
            """)
            if animate:
                time.sleep(0.8)
        else:
            st.caption("이 라운드에는 최종 점수만 저장됐다.")

        st.progress(score, text=f"AI 유사도 · {score} / 100점")
        st.session_state[state_key] = reveal
