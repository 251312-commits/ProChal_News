"""Art-deco marquee for the masked and revealed news score."""

from html import escape


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
