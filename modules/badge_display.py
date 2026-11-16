"""Badge symbols and nameplate presentation shared by the main and ranking views.

BADGE_SYMBOLS is the one place to replace temporary glyphs with images later.
Only catalog IDs can be rendered, and all user-controlled names are HTML escaped.
"""
from base64 import b64encode
from functools import lru_cache
from html import escape
from pathlib import Path

from modules.badges import BADGES, BADGE_BY_ID, equipped_badge, parse_owned


# Temporary monochrome Unicode symbols (not emoji) remain tintable by CSS.
BADGE_SYMBOLS = {
    "first_round": "✦",
    "all_games": "⌘",
    "thirty_rounds": "▣",
    "streak_three": "↗",
    "streak_five_mixed": "⟁",
    "streak_eight_mixed": "✶",
    "g1_ten": "∑",
    "g1_within_ten": "◎",
    "g1_within_three": "⊙",
    "g1_exact_ten": "≠",
    "g1_exact_one": "⋄",
    "g1_hit": "◈",
    "g2_ten_wins": "⇡",
    "g2_both_fifteen": "⇅",
    "g3_both_five": "◐",
    "g3_five_streak": "≋",
    "g4_five_wins": "▥",
    "g4_four_streak": "⟦",
    "g5_three_wins": "⌕",
    "g5_three_streak": "◉",
    "all_legendary": "♛",
    "bankrupt": "☒",
    "loan_survivor": "⌛",
    "first_borrow": "▤",
    "first_repay": "✓",
}
assert set(BADGE_SYMBOLS) == set(BADGE_BY_ID)


RARITY_LABELS = {
    "common": "COMMON", "rare": "RARE",
    "epic": "EPIC", "legendary": "LEGENDARY", "mythic": "MYTHIC",
}
# Distinct Legendary accents; Common/Rare/Epic use their shared tier color.
LEGENDARY_ACCENTS = {
    "streak_eight_mixed": "#F6CB64",
    "g1_hit": "#80E3FF",
    "g4_four_streak": "#C7A4FF",
    "g5_three_streak": "#FF8097",
    "loan_survivor": "#FFD48C",
}
MYTHIC_ACCENTS = {
    "all_legendary": "#FFE172",
    "bankrupt": "#FF526A",
}
RARITY_ACCENTS = {
    "common": "#C6C6D5",
    "rare": "#4DE9EC",
    "epic": "#B78BFF",
    "legendary": "#F6CB64",
    "mythic": "#FFE172",
}


def badge_symbol(badge_id: str) -> str:
    """Legacy fallback for clients that cannot render images."""
    return BADGE_SYMBOLS.get(badge_id, "✦")


# Local, text-based SVG assets require no image CDN and scale on high-DPI phones.
BADGE_ART_DIR = Path(__file__).resolve().parents[1] / "assets" / "badges"


@lru_cache(maxsize=32)
def badge_image_data_uri(badge_id: str) -> str:
    """Return a trusted in-repo SVG as an embeddable data URI.

    Badge IDs are taken only from the fixed catalog: never interpolate a
    user-supplied filename into a filesystem path.
    """
    if badge_id not in BADGE_BY_ID:
        return ""
    path = BADGE_ART_DIR / f"{badge_id}.svg"
    try:
        raw = path.read_bytes()
    except OSError:
        return ""
    return "data:image/svg+xml;base64," + b64encode(raw).decode("ascii")


def badge_accent(badge_id: str) -> str:
    badge = BADGE_BY_ID.get(badge_id)
    if badge is None:
        return "#53505B"
    return MYTHIC_ACCENTS.get(badge_id, LEGENDARY_ACCENTS.get(badge_id, RARITY_ACCENTS[badge.rarity]))


def nameplate_html(nickname: object, equipped: object, owned: object) -> str:
    """Return escaped, compact icon + name HTML, or plain name if unequipped."""
    display_name = escape(str(nickname or ""), quote=True)
    badge = equipped_badge(equipped, parse_owned(owned))
    if badge is None:
        return display_name

    title = escape(badge.title, quote=True)
    effect = badge.effect if badge.rarity in ("legendary", "mythic") else "plain"
    data_uri = badge_image_data_uri(badge.id)
    # A text fallback remains only when a packaged art file is missing.
    content = (
        f'<img class="pc-nameplate-art" src="{data_uri}" alt="" loading="lazy" />'
        if data_uri else escape(badge_symbol(badge.id))
    )
    return (
        f'<span class="pc-nameplate pc-tier-{badge.rarity} pc-effect-{effect}" '
        f'style="--pc-badge-accent:{badge_accent(badge.id)}">'
        f'<span class="pc-nameplate-symbol" title="{title}" aria-label="{title} 배지">{content}</span>'
        f'<span class="pc-nameplate-text">{display_name}</span>'
        f'</span>'
    )


NAMEPLATE_CSS = """
<style>
.pc-nameplate {
  --pc-badge-accent:#fff; display:inline-flex; align-items:center; vertical-align:baseline;
  max-width:100%; gap:.32em; position:relative; white-space:nowrap;
}
.pc-nameplate-symbol {
  font-family: "Segoe UI Symbol", "Apple Symbols", sans-serif;
  display:inline-flex; align-items:center; justify-content:center;
  font-size:1.05em; line-height:1; flex:0 0 auto; position:relative;
  color:var(--pc-badge-accent)!important;
}
.pc-nameplate-art {
  display:block; width:1.45em; height:1.45em; max-width:none;
  object-fit:contain; flex:none; user-select:none; pointer-events:none;
}
.pc-nameplate-text { min-width:0; overflow:hidden; text-overflow:ellipsis; }
.pc-nameplate.pc-tier-rare .pc-nameplate-text,
.pc-nameplate.pc-tier-epic .pc-nameplate-text,
.pc-nameplate.pc-tier-legendary .pc-nameplate-text,
.pc-nameplate.pc-tier-mythic .pc-nameplate-text {
  color:var(--pc-badge-accent)!important; text-shadow:none!important;
}
.pc-nameplate.pc-tier-rare .pc-nameplate-symbol {filter:drop-shadow(0 0 3px #4de9ec77);}
.pc-nameplate.pc-tier-epic .pc-nameplate-symbol {filter:drop-shadow(0 0 5px #ba8affaa);}
.pc-nameplate.pc-tier-legendary,
.pc-nameplate.pc-tier-mythic {
  filter:drop-shadow(0 0 6px var(--pc-badge-accent));
}
.pc-nameplate.pc-tier-mythic {
  filter:drop-shadow(0 0 5px var(--pc-badge-accent)) drop-shadow(0 0 9px var(--pc-badge-accent));
}
.pc-nameplate.pc-tier-legendary .pc-nameplate-symbol,
.pc-nameplate.pc-tier-mythic .pc-nameplate-symbol {
  text-shadow:0 0 6px var(--pc-badge-accent),0 0 13px var(--pc-badge-accent);
}
.pc-nameplate.pc-effect-loan_hourglass .pc-nameplate-symbol::after {
  content:"⌛";position:absolute;font-size:.55em;top:-.4em;right:-.38em;
  animation:pc-orbit 3.8s ease-in-out infinite;
}
.pc-nameplate.pc-effect-golden_crown .pc-nameplate-symbol::after {
  content:"✦";position:absolute;font-size:.55em;top:-.5em;right:-.5em;
  animation:pc-shimmer 2s ease-in-out infinite;color:#FFF1BD;
}
.pc-nameplate.pc-effect-scarlet_alarm .pc-nameplate-symbol::after {
  content:"";position:absolute;inset:-.15em;border:1px solid #FF5068;
  border-radius:50%;box-shadow:0 0 8px #FF344E88;animation:pc-alarm 1.6s ease-in-out infinite;
}
.pc-nameplate.pc-effect-orbiting_stars .pc-nameplate-symbol::after {
  content:"✧"; position:absolute; font-size:.55em; top:-.55em; right:-.5em;
  animation:pc-orbit 2.8s linear infinite;
}
.pc-nameplate.pc-effect-numeric_particles .pc-nameplate-symbol::after {
  content:"01"; position:absolute; letter-spacing:-.12em; font:700 .35em monospace;
  right:-.9em; top:-.65em; animation:pc-digits 2.5s ease-in-out infinite;
}
.pc-nameplate.pc-effect-closing_brackets .pc-nameplate-text::before {
  content:"["; display:inline-block; margin-right:.1em;
  animation:pc-bracket-left 2.4s ease-in-out infinite;
}
.pc-nameplate.pc-effect-closing_brackets .pc-nameplate-text::after {
  content:"]"; display:inline-block; margin-left:.1em;
  animation:pc-bracket-right 2.4s ease-in-out infinite;
}
.pc-nameplate.pc-effect-scanline::after {
  content:"";position:absolute;inset:0;pointer-events:none;border-radius:4px;
  background:linear-gradient(90deg,transparent 5%,#ffbac533 48%,#ffffff77 51%,transparent 56%);
  background-size:240% 100%;animation:pc-scan 3.2s ease-in-out infinite;
}
@keyframes pc-shimmer {0%,100%{opacity:.3;transform:scale(.7)}50%{opacity:1;transform:scale(1.2)}}
@keyframes pc-alarm {0%,100%{opacity:.4;transform:scale(.94)}50%{opacity:1;transform:scale(1.2)}}
@keyframes pc-orbit {0%{transform:rotate(0deg) translateX(6px) rotate(0deg)}
100%{transform:rotate(360deg) translateX(6px) rotate(-360deg)}}
@keyframes pc-digits {0%,100%{opacity:.2;transform:translateY(4px)}
50%{opacity:1;transform:translateY(-3px)}}
@keyframes pc-bracket-left {0%,100%{transform:translateX(-4px)}50%{transform:translateX(0)}}
@keyframes pc-bracket-right {0%,100%{transform:translateX(4px)}50%{transform:translateX(0)}}
@keyframes pc-scan {0%{background-position:190% 0}100%{background-position:-100% 0}}
@media (prefers-reduced-motion: reduce) {
 .pc-nameplate *, .pc-nameplate::after, .pc-nameplate *::after,
 .pc-nameplate *::before {animation:none!important;transition:none!important}
}
</style>
"""


def badge_gallery_css(owned: object, selected_id: str) -> str:
    """Theme the Streamlit button grid based on server-confirmed ownership."""
    owned_set = set(parse_owned(owned))
    rules = [
        """
<style>
/* A single, square scrollport: the badge list is the only scrollable region
   on normal mobile portrait screens. Selection details/buttons live outside.
   Native st.container(height=320) provides keyboard and touch scrolling. */
.st-key-badge_gallery {
  --pc-badge-side:max(145px, min(320px, calc(100dvw - 78px), calc(100dvh - 270px)));
  box-sizing:border-box!important;
  width:var(--pc-badge-side)!important;
  height:var(--pc-badge-side)!important;
  min-width:0!important;
  min-height:0!important;
  max-width:100%!important;
  max-height:var(--pc-badge-side)!important;
  aspect-ratio:1 / 1!important;
  flex:none!important;
  margin-inline:auto!important;
  padding:8px!important;
  overflow-y:auto!important;
  overflow-x:hidden!important;
  overscroll-behavior:contain;
  -webkit-overflow-scrolling:touch;
  touch-action:pan-y;
  scrollbar-width:thin;
  scrollbar-color:#A47DE7 #1C142B;
  background:linear-gradient(150deg,#160E24,#090D18)!important;
  border:1px solid #6F4E9D!important;
  border-radius:12px!important;
}
.st-key-badge_gallery::-webkit-scrollbar {width:5px;}
.st-key-badge_gallery::-webkit-scrollbar-thumb {background:#9A70C8;border-radius:6px;}
.st-key-badge_gallery::-webkit-scrollbar-track {background:#170F26;}
.st-key-badge_gallery .stButton button {
  box-sizing:border-box!important;
  width:100%!important; min-width:0!important; max-width:100%!important;
  min-height:54px!important; height:54px!important;
  font-family:"Segoe UI Symbol","Apple Symbols",sans-serif!important;
  font-size:1.85rem!important; line-height:1!important;
  border-radius:12px!important; margin:0!important; padding:0!important;
  box-shadow:none!important;
}
.st-key-badge_gallery .stButton button {
  position:relative!important; isolation:isolate!important;
}
.st-key-badge_gallery .stButton button p {
  /* Keep the badge title accessible, but use the illustrated asset visually. */
  font-size:0!important; line-height:0!important;
  color:transparent!important; user-select:none!important;
}
.st-key-badge_gallery div[data-testid="stVerticalBlock"] {gap:.12rem!important;}
.st-key-badge_gallery .pc-badge-tile-name {
  font-size:.68rem; line-height:1.3; text-align:center; min-height:2.1rem;
  color:#E9E3F4;overflow-wrap:anywhere;letter-spacing:-.03em;
}
.st-key-badge_gallery .pc-badge-tile-name.is-locked {color:#62616B!important;}
.st-key-badge_gallery .pc-badge-tile-name.is-equipped {color:#FFE6A9!important;}
.st-key-badge_gallery .stButton {margin-bottom:0!important;}
.st-key-badge_gallery,
.st-key-badge_gallery [data-testid="stColumn"] {
  min-width:0!important; max-width:100%!important; box-sizing:border-box!important;
}
.st-key-badge_gallery [data-testid="stHorizontalBlock"] {
  min-width:0!important; max-width:100%!important;
}
/* Protect portrait AND landscape phones (e.g. 874×402) from modal overflow. */
[role="dialog"]:has(.st-key-badge_gallery) {
  box-sizing:border-box!important;
  min-width:0!important; max-width:min(560px, calc(100dvw - 16px))!important;
  max-height:calc(100dvh - 16px)!important;
  overflow-x:hidden!important; overflow-y:auto!important;
}
@media (max-width: 700px) {
  /* The modal itself must fit inside the mobile viewport. */
  [role="dialog"]:has(.st-key-badge_gallery) {
    box-sizing:border-box!important;
    width:calc(100dvw - 16px)!important;
    max-width:calc(100dvw - 16px)!important;
    min-width:0!important; margin-inline:auto!important;
    max-height:calc(100dvh - 16px)!important;
    overflow-x:hidden!important; overflow-y:auto!important;
  }
  [role="dialog"]:has(.st-key-badge_gallery) [data-testid="stVerticalBlock"] {
    min-width:0!important; max-width:100%!important;
  }
  .st-key-badge_gallery {
    /* Keep the same responsive side on phones; do not stretch to dialog width. */
    width:var(--pc-badge-side)!important;
    height:var(--pc-badge-side)!important;
    max-width:100%!important;
    max-height:var(--pc-badge-side)!important;
    overflow-x:hidden!important;
    overflow-y:auto!important;
  }
  .st-key-badge_gallery [data-testid="stHorizontalBlock"] {
    display:flex!important; flex-flow:row nowrap!important;
    width:100%!important; min-width:0!important; max-width:100%!important;
    gap:4px!important;
  }
  /* Streamlit 1.55 uses stColumn, not the older 'column' test ID. */
  .st-key-badge_gallery [data-testid="stColumn"] {
    flex:1 1 0!important; width:0!important; max-width:none!important;
    min-width:0!important; padding:0!important;
  }
  .st-key-badge_gallery .stButton button {
    min-height:46px!important; height:46px!important;
    font-size:1.5rem!important; padding:0!important;
  }
  .st-key-badge_gallery .pc-badge-tile-name {
    font-size:.61rem!important; line-height:1.3!important;
    min-height:2rem!important;
  }
  .pc-badge-detail {gap:9px!important;padding:10px!important;max-width:100%!important;min-width:0!important;}
  .pc-badge-detail > div:last-child {min-width:0!important;overflow-wrap:anywhere!important;}
  .pc-badge-detail-icon {min-width:44px!important;width:44px!important;height:44px!important;font-size:1.7rem!important;}
}
@media (max-width: 370px) {
  .st-key-badge_gallery [data-testid="stHorizontalBlock"] {gap:3px!important;}
  .st-key-badge_gallery .pc-badge-tile-name {font-size:.57rem!important;}
}
.st-key-badge_header_controls button {
 border:1px solid #A985FF!important;border-radius:9px!important;
 background:linear-gradient(90deg,#211036,#32134A)!important;
 color:#F4E9FF!important;min-height:42px!important;box-shadow:0 0 9px #9C4BFF55!important;
 font-size:.9rem!important;font-weight:800!important;
}
.pc-badge-detail {display:flex;align-items:center;gap:14px;
 max-width:100%; min-width:0;box-sizing:border-box;
 border:1px solid #5B4179;border-radius:13px;padding:12px;margin:12px 0 6px;
 background:#1B102A;color:#FFFFFF}
.pc-badge-detail-icon {min-width:56px;height:56px;display:flex;align-items:center;
 justify-content:center;font-size:2.2rem;border-radius:11px;overflow:hidden;box-sizing:border-box;
 background:#2A1B3F;border:1px solid currentColor;font-family:"Segoe UI Symbol","Apple Symbols",sans-serif}
.pc-badge-detail-icon img {width:100%;height:100%;display:block;object-fit:contain;}
.pc-badge-detail-rarity {font-size:.7rem;font-weight:800;letter-spacing:.16em}
.pc-badge-detail-title {font-size:1.05rem;font-weight:800;margin-top:2px}
.pc-badge-detail-condition {font-size:.82rem;line-height:1.5;color:#D6CDDF;margin-top:3px}
.pc-badge-count {color:#D3BDFD;font-size:.86rem;margin:4px 0 12px}
"""
    ]
    for badge in BADGES:
        key = f".st-key-badge_card_{badge.id}"
        is_owned = badge.id in owned_set
        color = badge_accent(badge.id) if is_owned else "#4F4C59"
        background = "#261631" if is_owned else "#141218"
        stroke = f"{color}" if is_owned else "#38343E"
        if badge.id == selected_id:
            stroke = "#FFFFFF" if is_owned else "#7E7387"
        rules.append(
            f"{key} .stButton button {{background:{background}!important;"
            f"color:{color}!important;border:2px solid {stroke}!important;"
            f"box-shadow:{'0 0 11px ' + color + '77' if badge.id == selected_id and is_owned else 'none'}!important;}}"
        )
        uri = badge_image_data_uri(badge.id)
        if uri:
            # Pseudo-element art preserves the native Streamlit button,
            # hover/click behavior, keyboard focus and mobile 4-column grid.
            effect = "none" if is_owned else "grayscale(1) brightness(.30) contrast(1.1)"
            rules.append(
                f"{key} .stButton button::before {{content:'';display:block;"
                f"position:absolute;inset:1px;pointer-events:none;"
                f"background-image:url('{uri}');background-position:center;"
                f"background-repeat:no-repeat;background-size:contain;"
                f"filter:{effect};opacity:{'1' if is_owned else '.72'};}}"
            )
    # Keep every dynamic button rule INSIDE the single style tag. Appending
    # selectors after </style> made raw CSS appear as broken HTML in the dialog.
    return "".join(rules) + "\n</style>"
