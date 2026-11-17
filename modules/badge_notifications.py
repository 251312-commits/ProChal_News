"""One-shot, account-scoped announcements for server-confirmed badge awards.

This module never calculates achievements or writes badge ownership.
"""
from html import escape

import streamlit as st

from modules.badges import BADGE_BY_ID
from modules.badge_display import (
    RARITY_LABELS, badge_accent, badge_image_data_uri, badge_symbol,
)

_OWNER = "badge_award_owner"
_QUEUE = "badge_award_queue"
_SEEN = "badge_award_seen"


def _active_owner() -> str:
    """Discard another account's queued notifications on account changes."""
    owner = str(st.session_state.get("current_user") or "")
    if st.session_state.get(_OWNER) != owner:
        st.session_state[_OWNER] = owner
        st.session_state[_QUEUE] = ()
        st.session_state[_SEEN] = ()
    return owner


def queue_badge_awards(badge_ids: object) -> tuple[str, ...]:
    """Queue newly unlocked catalog IDs once, including on transaction replays."""
    if not _active_owner() or not isinstance(badge_ids, (tuple, list)):
        return ()
    seen = set(st.session_state.get(_SEEN, ()))
    new_ids: list[str] = []
    for badge_id in badge_ids:
        if not isinstance(badge_id, str) or badge_id not in BADGE_BY_ID or badge_id in seen:
            continue
        new_ids.append(badge_id)
        seen.add(badge_id)
    if new_ids:
        st.session_state[_QUEUE] = (*st.session_state.get(_QUEUE, ()), *new_ids)
        st.session_state[_SEEN] = (*st.session_state.get(_SEEN, ()), *new_ids)
    return tuple(new_ids)


def pending_badge_ids() -> tuple[str, ...]:
    if not _active_owner():
        return ()
    return tuple(
        badge_id for badge_id in st.session_state.get(_QUEUE, ())
        if isinstance(badge_id, str) and badge_id in BADGE_BY_ID
    )


def acknowledge_badge_awards(badge_ids: object) -> None:
    """Acknowledge only the displayed badges, preserving any later awards."""
    pending = pending_badge_ids()
    if not isinstance(badge_ids, (tuple, list)):
        return
    acknowledged = {item for item in badge_ids if isinstance(item, str)}
    st.session_state[_QUEUE] = tuple(item for item in pending if item not in acknowledged)


def pending_badge_cards() -> list[dict[str, str]]:
    """Presentation metadata from the trusted local catalog and SVG assets."""
    cards = []
    for badge_id in pending_badge_ids():
        badge = BADGE_BY_ID[badge_id]
        cards.append({
            "id": badge.id,
            "title": badge.title,
            "description": badge.description,
            "rarity": RARITY_LABELS[badge.rarity],
            "accent": badge_accent(badge.id),
            "image": badge_image_data_uri(badge.id),
            "symbol": badge_symbol(badge.id),
        })
    return cards


_AWARD_CSS = """
<style>
.pc-award-shell { color:#f9edff; text-align:center; padding:2px 0 6px; }
.pc-award-eyebrow {font:800 11px/1.5 sans-serif;letter-spacing:.19em;color:#f6ca77;margin:0 0 6px;}
.pc-award-heading {font:900 clamp(20px,5vw,26px)/1.2 sans-serif;margin:0 0 14px;color:#fff2ff;}
.pc-award-list {display:grid;gap:10px;max-height:min(56dvh,410px);overflow-y:auto;overscroll-behavior:contain;padding:6px 4px 10px;}
.pc-award-card {--award-accent:#dac8ed;display:flex;align-items:center;gap:10px;text-align:left;
  border:1px solid var(--award-accent);border-radius:16px;padding:9px 12px;
  background:linear-gradient(125deg,#3b194e,#190e2c 70%);box-shadow:0 0 16px #b552e63d,inset 0 0 10px #ffffff0e;}
.pc-award-art {width:clamp(67px,20vw,96px);height:clamp(67px,20vw,96px);
  flex:none;display:grid;place-items:center;color:var(--award-accent);font-size:40px;
  filter:drop-shadow(0 0 9px var(--award-accent));animation:pc-award-arrive .65s ease-out both;}
.pc-award-art img {width:100%;height:100%;object-fit:contain;}
.pc-award-info {min-width:0;overflow-wrap:anywhere;}
.pc-award-rarity {font:850 10px/1.4 sans-serif;letter-spacing:.14em;color:var(--award-accent);}
.pc-award-title {font:900 clamp(16px,4vw,20px)/1.25 sans-serif;margin:4px 0;color:#fff;}
.pc-award-description {font:500 12px/1.45 sans-serif;color:#d8bfe4;margin:0;}
.pc-award-footnote {color:#c9a5da;font:600 12px/1.5 sans-serif;margin:12px 0 2px;}
[data-testid="stDialog"]:has(.pc-award-shell) [role="dialog"] {
  width:min(420px,calc(100dvw - 24px))!important;max-height:calc(100dvh - 20px)!important;
  background:linear-gradient(160deg,#351543,#150b22 75%)!important;
  border:1px solid #bc83d1!important;box-shadow:0 0 42px #ad4ed971!important;
}
@keyframes pc-award-arrive {from {transform:scale(.76) rotate(-9deg);opacity:0}to {transform:scale(1);opacity:1}}
@media (prefers-reduced-motion:reduce) {.pc-award-art {animation:none;}}
</style>
"""


@st.dialog("NEW BADGE · 신규 배지 획득", width="small", dismissible=False)
def _badge_award_dialog() -> None:
    cards = pending_badge_cards()
    if not cards:
        return
    count = len(cards)
    markup = [
        '<div class="pc-award-shell"><p class="pc-award-eyebrow">ACHIEVEMENT UNLOCKED</p>',
        f'<h2 class="pc-award-heading">새로운 배지 {count}개 획득!</h2>',
        '<div class="pc-award-list">',
    ]
    for card in cards:
        artwork = (
            f'<img src="{card["image"]}" alt="" />'
            if card["image"] else escape(card["symbol"])
        )
        markup.append(
            f'<article class="pc-award-card" style="--award-accent:{card["accent"]}">'
            f'<div class="pc-award-art">{artwork}</div>'
            f'<div class="pc-award-info"><div class="pc-award-rarity">{card["rarity"]}</div>'
            f'<h3 class="pc-award-title">{escape(card["title"])}</h3>'
            f'<p class="pc-award-description">{escape(card["description"])}</p></div>'
            '</article>'
        )
    markup.append(
        '</div><p class="pc-award-footnote">획득한 배지는 메인 화면의 배지 컬렉션에서 장착할 수 있다.</p></div>'
    )
    st.html(_AWARD_CSS + "".join(markup))
    if st.button("확인 · 계속하기", key="badge-award-confirm", use_container_width=True, type="primary"):
        acknowledge_badge_awards([card["id"] for card in cards])
        st.rerun()


def show_pending_badge_award() -> None:
    """Call from the main router after the active page finishes rendering."""
    if pending_badge_ids():
        _badge_award_dialog()
