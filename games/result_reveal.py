"""Shared AI-summary typewriter reveal, shown before any game score.

The summary is already generated and scored before this UI runs; the animation
only controls what the player sees, and never re-runs a wager or sheet update.
"""

from base64 import b64encode
from functools import lru_cache
from html import escape
from math import ceil, tanh
from pathlib import Path
import time
from uuid import uuid4

from games.score_stage import STAGE_CSS, score_stage


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
.st-key-news_comparison .score-diagram {
    display: block; width: 100%; max-width: 28rem; height: auto; margin: .35rem auto 0;
}
.st-key-news_comparison [data-testid="stCaptionContainer"] p { color: #e7def0; }
.st-key-news_comparison .news-still { display: none; }
@media (prefers-reduced-motion: reduce) {
    .st-key-news_comparison .news-still { display: inline; }
    .st-key-news_comparison .news-typing { display: none; }
}
</style>
"""


@lru_cache(maxsize=1)
def _theatre_style():
    asset = Path(__file__).resolve().parents[1] / "assets/score_reveal/theatre.webp"
    art = b64encode(asset.read_bytes()).decode("ascii")
    return f"<style>.st-key-news_comparison{{--score-stage-art:url(data:image/webp;base64,{art})}}{STAGE_CSS}</style>"


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


def _score_diagram(details, animate):
    """Plot the stored reranker output on the sigmoid over a symmetric logit axis."""
    logit = details["logit"]
    normalized = details["normalized"]
    model_label = escape(details["model_name"].rsplit("/", 1)[-1])
    token_count = details["token_count"]
    limit = max(4, ceil(abs(logit)))
    left, right, top, bottom = 151, 298, 132, 177
    # Sample σ(x) = (1 + tanh(x / 2)) / 2, stable for large |logit|.
    points = []
    for index in range(81):
        t = index / 80
        raw = (2 * t - 1) * limit
        y = bottom - (bottom - top) * (1 + tanh(raw / 2)) / 2
        points.append(f"{left + t * (right - left):.2f},{y:.2f}")
    cx = left + (logit + limit) / (2 * limit) * (right - left)
    cy = bottom - normalized * (bottom - top)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 214"
        font-family="system-ui, Apple SD Gothic Neo, Malgun Gothic, sans-serif" text-anchor="middle"
        class="{'play' if animate else 'still'}">
      <style>
        @media (prefers-reduced-motion: no-preference) {{
          .play .model {{ animation: trace-appear .25s both; }}
          .play .logit {{ animation: trace-appear .25s .18s both; }}
          .play .curve {{ animation: trace-appear .25s .36s both; }}
          @keyframes trace-appear {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
        }}
      </style>
      <g fill="none" stroke="#ad94c4" stroke-width="1.5">
        <path d="M74 29 V33 Q74 37 80 37 H154 Q160 37 160 43 V47"/>
        <path d="M246 29 V33 Q246 37 240 37 H166 Q160 37 160 43"/>
      </g>
      <g fill="#392c4a" stroke="#9c83b3">
        <rect x="14" y="4" width="120" height="25" rx="12"/>
        <rect x="186" y="4" width="120" height="25" rx="12"/>
      </g>
      <g fill="#fff6ff" font-size="13" font-weight="600">
        <text x="74" y="21">① AI 요약문</text><text x="246" y="21">② 기사 제목</text>
      </g>
      <g class="model">
        <rect x="22" y="47" width="276" height="35" rx="8" fill="#392948" stroke="#c7a6dd"/>
        <path d="M213 55 V74" stroke="#836b94"/>
        <text x="119" y="69" fill="#fff6ff" font-size="13" font-weight="700">{model_label}</text>
        <text x="255" y="69" fill="#f8da9d" font-size="13">{token_count}토큰</text>
      </g>
      <g class="logit">
        <path d="M160 82 V88 Q160 93 154 93 H57 Q51 93 51 99 V114"
              fill="none" stroke="#ad94c4" stroke-width="1.5"/>
        <path d="m47 108 4 6 4-6" fill="none" stroke="#ad94c4" stroke-width="1.5"/>
        <rect x="3" y="117" width="98" height="55" rx="8" fill="#241c2e" stroke="#816599"/>
        <text x="52" y="136" fill="#dccce8" font-size="12">관련성 원점수</text>
        <text x="52" y="157" fill="#fff1d3" font-size="17" font-weight="700">{logit:.4f}</text>
        <path d="M102 144 H119 m-5 -4 5 4 -5 4" fill="none" stroke="#dec38b" stroke-width="1.5"/>
      </g>
      <g class="curve">
        <rect x="122" y="100" width="195" height="97" rx="8" fill="#221a2b" stroke="#816599"/>
        <text x="133" y="119" text-anchor="start" fill="#dfcfe9" font-size="12">시그모이드</text>
        <text x="305" y="119" text-anchor="end" fill="#f9d992" font-weight="700" font-size="14">≈ {normalized:.6f}</text>
        <path d="M{left} {top} V{bottom} H{right}" stroke="#927da2" fill="none"/>
        <path d="M{(left + right) / 2} {top} V{bottom}" stroke="#54475f" stroke-dasharray="2 3"/>
        <g font-size="10.5" fill="#cbbbd5">
          <text x="141" y="{top + 4}">1</text><text x="141" y="{bottom + 2}">0</text>
          <text x="{left}" y="191">−{limit}</text><text x="{(left + right) / 2}" y="191">0</text>
          <text x="{right}" y="191">+{limit}</text>
        </g>
        <polyline points="{' '.join(points)}" fill="none" stroke="#b599df" stroke-width="2.3"/>
        <path d="M{left} {cy:.2f} H{cx:.2f} V{bottom}" stroke="#f1ce89" fill="none" stroke-dasharray="2 3"/>
        <circle cx="{cx:.2f}" cy="{cy:.2f}" r="4.3" fill="#ffdb88" stroke="#392438" stroke-width="1.5"/>
        <path d="M220 197 V200 Q220 204 215 204 H165 Q160 204 160 209 V212 m-4 -4 4 4 4-4"
              fill="none" stroke="#dec38b" stroke-width="1.5"/>
      </g>
    </svg>"""
    # Streamlit's HTML sanitizer removes inline SVG. The image is entirely local.
    image = b64encode(svg.encode()).decode("ascii")
    alt = escape(
        f"AI 요약문과 기사 제목을 함께 입력. {details['model_name']}, {token_count}토큰. "
        f"관련성 원점수 약 {logit:.4f}, 시그모이드 변환값 약 {normalized:.6f}."
    )
    return f'<img class="score-diagram" alt="{alt}" src="data:image/svg+xml;base64,{image}">'


def show_summary_before_score(
    summary_text: str, state_key: str, *, title: str, score: float, details=None, prediction=None,
    score_precision: int = 0,
) -> None:
    """Show stored model measurements and the score used to settle this round."""
    import streamlit as st

    text = str(summary_text or "").strip()
    escaped_text = escape(text)
    reveal = (title, text, score)
    previous = st.session_state.get(state_key)
    seen = previous == reveal
    pending = previous if isinstance(previous, dict) and previous.get("result") == reveal else None

    with st.container(key="news_comparison"):
        st.html(_STYLE + _theatre_style())
        st.html('<div class="news-label">기사 제목</div>')
        st.html(f'<div class="news-copy">{escape(title)}</div>')
        if text:
            st.html('<div class="news-label">AI 요약문</div>')
            message = st.empty()
            if not seen and pending is None:
                partial = []
                next_frame = 0.0
                for letter in type_summary_characters(text):
                    partial.append(letter)
                    now = time.monotonic()
                    if now >= next_frame:
                        message.html(
                            '<div class="news-copy news-message"><span class="news-typing">'
                            f'{escape("".join(partial))}<span aria-hidden="true">▍</span></span>'
                            f'<span class="news-still">{escaped_text}</span></div>'
                        )
                        next_frame = now + 0.03
            message.html(f'<div class="news-copy news-message">{escaped_text}</div>')

        hundredths = details.get("score_hundredths") if details else None
        guess = ""
        if hundredths is None:
            score_label = digits = f"{score:.{score_precision}f}"
        else:
            whole, fraction = divmod(hundredths, 100)
            score_label = f"{whole}.{fraction:02d}"
            digits = score_label
            if prediction is not None:
                digits = f'{whole}.<span class="score-fraction">{fraction:02d}</span>'
                guess = f'<div class="score-guess">내 예측 <b>{prediction:02d}</b></div>'

        stage = st.empty()
        reveal_id = state_key
        if not seen:
            if pending is None:
                pending = {"result": reveal, "id": uuid4().hex, "until": time.monotonic() + 2.6}
                st.session_state[state_key] = pending
            reveal_id = pending["id"]
            remaining = pending["until"] - time.monotonic()
            if remaining > 0:
                stage.html(score_stage("rolling", reveal_id))
                time.sleep(remaining)

        stage.html(score_stage(
            "settled" if seen else "landed", reveal_id, digits_html=digits,
            score_label=score_label, guess_html=guess,
        ))
        st.session_state[state_key] = reveal
        # Even the sigmoid chart discloses the exact outcome. Send it after the unveiling.
        if details is not None:
            st.html(_score_diagram(details, not seen))
        else:
            st.caption("이 라운드에는 최종 점수만 저장됐다.")
