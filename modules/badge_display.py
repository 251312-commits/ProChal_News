"""Badge symbols and nameplate presentation shared by the main and ranking views.

BADGE_SYMBOLS is the one place to replace temporary glyphs with images later.
Only catalog IDs can be rendered, and all user-controlled names are HTML escaped.
"""
from html import escape

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
}
assert set(BADGE_SYMBOLS) == set(BADGE_BY_ID)


RARITY_LABELS = {
    "common": "COMMON", "rare": "RARE",
    "epic": "EPIC", "legendary": "LEGENDARY",
}
# Distinct Legendary accents; Common/Rare/Epic use their shared tier color.
LEGENDARY_ACCENTS = {
    "streak_eight_mixed": "#F6CB64",
    "g1_hit": "#80E3FF",
    "g4_four_streak": "#C7A4FF",
    "g5_three_streak": "#FF8097",
}
RARITY_ACCENTS = {
    "common": "#C6C6D5",
    "rare": "#4DE9EC",
    "epic": "#B78BFF",
    "legendary": "#F6CB64",
}


def badge_symbol(badge_id: str) -> str:
    return BADGE_SYMBOLS.get(badge_id, "✦")


def badge_accent(badge_id: str) -> str:
    badge = BADGE_BY_ID.get(badge_id)
    if badge is None:
        return "#53505B"
    return LEGENDARY_ACCENTS.get(badge_id, RARITY_ACCENTS[badge.rarity])


def nameplate_html(nickname: object, equipped: object, owned: object) -> str:
    """Return escaped, compact icon + name HTML, or plain name if unequipped."""
    display_name = escape(str(nickname or ""), quote=True)
    badge = equipped_badge(equipped, parse_owned(owned))
    if badge is None:
        return display_name

    symbol = escape(badge_symbol(badge.id))
    title = escape(badge.title, quote=True)
    effect = badge.effect if badge.rarity == "legendary" else "plain"
    return (
        f'<span class="pc-nameplate pc-tier-{badge.rarity} pc-effect-{effect}" '
        f'style="--pc-badge-accent:{badge_accent(badge.id)}">'
        f'<span class="pc-nameplate-symbol" title="{title}" aria-label="{title} 배지">{symbol}</span>'
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
.pc-nameplate-text { min-width:0; overflow:hidden; text-overflow:ellipsis; }
.pc-nameplate.pc-tier-rare .pc-nameplate-text,
.pc-nameplate.pc-tier-epic .pc-nameplate-text,
.pc-nameplate.pc-tier-legendary .pc-nameplate-text {
  color:var(--pc-badge-accent)!important; text-shadow:none!important;
}
.pc-nameplate.pc-tier-rare .pc-nameplate-symbol {filter:drop-shadow(0 0 3px #4de9ec77);}
.pc-nameplate.pc-tier-epic .pc-nameplate-symbol {filter:drop-shadow(0 0 5px #ba8affaa);}
.pc-nameplate.pc-tier-legendary {
  filter:drop-shadow(0 0 6px var(--pc-badge-accent));
}
.pc-nameplate.pc-tier-legendary .pc-nameplate-symbol {
  text-shadow:0 0 6px var(--pc-badge-accent),0 0 13px var(--pc-badge-accent);
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
.st-key-badge_gallery .stButton button {
  box-sizing:border-box!important;
  width:100%!important; min-width:0!important; max-width:100%!important;
  min-height:54px!important; height:54px!important;
  font-family:"Segoe UI Symbol","Apple Symbols",sans-serif!important;
  font-size:1.85rem!important; line-height:1!important;
  border-radius:12px!important; margin:0!important; padding:0!important;
  box-shadow:none!important;
}
.st-key-badge_gallery .stButton button p {
  font-family:"Segoe UI Symbol","Apple Symbols",sans-serif!important;
  font-size:inherit!important; line-height:1!important; white-space:nowrap!important;
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
    box-sizing:border-box!important; min-width:0!important;
    width:100%!important; max-width:100%!important;
    overflow-x:hidden!important;
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
 justify-content:center;font-size:2.2rem;border-radius:11px;
 background:#2A1B3F;border:1px solid currentColor;font-family:"Segoe UI Symbol","Apple Symbols",sans-serif}
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
    # Keep every dynamic button rule INSIDE the single style tag. Appending
    # selectors after </style> made raw CSS appear as broken HTML in the dialog.
    return "".join(rules) + "\n</style>"
