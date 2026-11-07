"""Shared AI-summary typewriter reveal, shown before any game score.

The summary is already generated and scored before this UI runs; the animation
only controls what the player sees, and never re-runs a wager or sheet update.
"""

from base64 import b64encode
from html import escape
from math import ceil, tanh
from pathlib import Path
import time
from uuid import uuid4

from modules.ui_components import load_local_image_url



STAGE_CSS = """
.score-stage {
    --brass: linear-gradient(114deg,#6a3b22 0%,#efc37b 15%,#795032 29%,#ffe3a2 48%,#aa713b 64%,#543522 79%,#f8d798 93%,#785130);
    position:relative; isolation:isolate; overflow:hidden; container-type:inline-size;
    box-sizing:border-box; width:100%; max-width:34rem; margin:.4rem auto; border:1px solid #a1774f;
    border-radius:12px; padding:clamp(24px,7%,36px) clamp(18px,6%,34px) clamp(20px,6%,32px); text-align:center;
    color:#f5deb5; background-color:#210e26;
    background-image:var(--score-stage-art,linear-gradient(145deg,#3c1b47,#160a1a));
    background-position:center; background-repeat:no-repeat; background-size:100% 100%;
}
.score-stage *, .score-stage *::before, .score-stage *::after { box-sizing:border-box; }
.score-stage .stage-title {
    display:inline-flex; align-items:center; justify-content:center; gap:10px; position:relative;
    z-index:1; margin:0 auto -3px; padding:3px 19px; border:1px solid #c39765; border-radius:4px;
    background:linear-gradient(#43253e,#251422); color:#ffe4b5; font:700 .91rem/1.45 Georgia,serif; letter-spacing:.09em;
    box-shadow:0 0 0 2px #342026, inset 0 0 0 2px #513442;
}
.score-stage .stage-title::before, .score-stage .stage-title::after {
    content:""; width:16px; height:5px; border-block:1px solid #c99b62;
}
.score-stage .stage-housing {
    position:relative; padding:12px 11px; border-radius:14px; background:var(--brass);
    box-shadow:inset 0 0 0 1px #e3b980,0 5px 8px #100811;
}
.score-stage .stage-lamps {
    position:absolute; left:14%; right:14%; height:6px;
    background:radial-gradient(circle,#fff2b8 0 1.5px,#ffcd79 2px,#ab6935 2.7px,transparent 3.1px) center/11.111% 6px repeat-x;
    filter:drop-shadow(0 0 3px #ffc16e); pointer-events:none;
}
.score-stage .stage-lamps.top { top:3px; } .score-stage .stage-lamps.bottom { bottom:3px; }
.score-stage .stage-window {
    position:relative; overflow:hidden; display:grid; place-items:center; min-height:92px;
    min-height:clamp(84px,28cqi,132px); padding:5px 4px 8px;
    border:1px solid #38231f; border-radius:8px; background:linear-gradient(160deg,#28172f,#130c1d 45%,#30182d);
    box-shadow:inset 0 0 0 2px #684835,inset 0 0 0 5px #251826,inset 0 -10px 20px #110b17;
}
.score-stage .stage-digits {
    position:relative; display:inline-block; white-space:nowrap; color:#fce9c8;
    font:700 clamp(38px,14vw,80px)/1 Georgia,"Times New Roman",serif;
    font-size:clamp(36px,18cqi,82px); font-variant-numeric:lining-nums tabular-nums;
    letter-spacing:.015em; text-shadow:0 2px #754f3b,0 3px 6px #100815;
}
.score-stage .stage-digits .score-fraction {
    color:#ffdc81; background:transparent; padding:0; border:0; text-shadow:0 2px #9b5e26,0 0 12px #efaf493b;
}
.score-stage .stage-footer {
    min-height:35px; padding:9px 0 0; display:flex; justify-content:center; align-items:center; gap:8px;
    font:600 .86rem/1.25 system-ui,sans-serif; color:#e3c9df;
}
.score-stage .stage-footer .score-guess { color:#dbc2d8; font:inherit; border:0; padding:0; }
.score-stage .stage-footer .score-guess b { color:#ffe09a; font-variant-numeric:tabular-nums; margin-left:.2em; }
.score-stage .stage-beats {
    width:34px; height:9px; opacity:.85; clip-path:polygon(0 40%,11% 40%,11% 18%,33% 18%,33% 0,66% 0,66% 18%,88% 18%,88% 40%,100% 40%,100% 60%,88% 60%,88% 82%,66% 82%,66% 100%,33% 100%,33% 82%,11% 82%,11% 60%,0 60%);
    background:repeating-linear-gradient(90deg,#c28bce 0 3px,transparent 3px 6px);
}
.score-stage[data-reveal-phase="rolling"] .stage-digits { color:#ad8aad; text-shadow:0 1px 1px #f4ddf466,0 4px 7px #100815; }
.score-stage[data-reveal-phase="rolling"] .stage-lamps { opacity:.35; }
@media (prefers-reduced-motion:no-preference) {
    .score-stage[data-reveal-phase="rolling"] .stage-lamps { animation:score-warm-lamps 2.6s ease-in both; }
    .score-stage[data-reveal-phase="rolling"] .stage-beats { animation:score-drum-beats .52s ease-in-out 4 alternate; }
    .score-stage[data-reveal-phase="landed"] .stage-window::after {
        content:""; position:absolute; inset:-30%; pointer-events:none;
        background:linear-gradient(111deg,transparent 41%,#ffd88a44 48%,#fff0b577 50%,transparent 55%);
        animation:score-brass-sweep .66s ease-out both;
    }
    .score-stage[data-reveal-phase="landed"] .stage-digits::after {
        content:"✦"; position:absolute; right:-.27em; top:-.16em; font-size:.44em; color:#fff1c4;
        text-shadow:0 0 9px #ffd07e; animation:score-corner-glint .68s ease-out both;
    }
    @keyframes score-warm-lamps { from {opacity:.22;} 70% {opacity:.60;} to {opacity:.92;} }
    @keyframes score-drum-beats { from {transform:scaleY(.45);} to {transform:scaleY(1.2);} }
    @keyframes score-brass-sweep { from {transform:translateX(-70%);} to {transform:translateX(75%);} }
    @keyframes score-corner-glint { from {opacity:0; transform:scale(.3);} 24% {opacity:1;transform:scale(1);} to {opacity:0;transform:scale(.2);} }
}
"""


def score_stage(phase, reveal_id, *, digits_html="", score_label="", guess_html=""):
    """Render the pending stage without inserting any score, even in accessible text."""
    if phase not in ("rolling", "landed", "settled"):
        raise ValueError("Unknown score reveal phase")
    if phase == "rolling":
        digits = "??.??"
        label = "점수 공개 대기"
        footer = '<span class="stage-beats" aria-hidden="true"></span>두구두구…'
    else:
        digits = digits_html
        label = f"AI 유사도 {escape(score_label)}점"
        footer = guess_html or "최종 점수"
    return (
        f'<div class="score-stage" data-reveal-id="{escape(reveal_id)}" data-reveal-phase="{phase}">'
        '<div class="stage-title">AI 유사도</div>'
        '<div class="stage-housing"><i class="stage-lamps top" aria-hidden="true"></i>'
        '<div class="stage-window"><div class="stage-digits" role="img" '
        f'aria-label="{label}">{digits}</div></div>'
        '<i class="stage-lamps bottom" aria-hidden="true"></i></div>'
        f'<div class="stage-footer">{footer}</div></div>'
    )


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


def _theatre_style():
    asset = Path(__file__).resolve().parents[2] / "assets/score_reveal/theatre.webp"
    art = load_local_image_url(str(asset))
    return f'<style>.st-key-news_comparison{{--score-stage-art:url("{art}")}}{STAGE_CSS}</style>'

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
