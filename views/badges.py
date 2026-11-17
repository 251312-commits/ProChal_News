"""Mobile-friendly badge collection dialog on the main screen."""
from html import escape
from time import monotonic

import streamlit as st

from modules.badges import BADGES, BADGE_BY_ID, parse_owned, serialize_owned
from modules.loading_feedback import render_loading_feedback
from modules.badge_display import (
    RARITY_LABELS, badge_accent, badge_gallery_css, badge_image_data_uri, badge_symbol,
)
from modules.transactions import (
    TransactionError, equip_badge, refresh_account_from_gateway,
    sync_badges_from_gateway, transaction_id,
)


# The ledger reconciliation can scan the complete Transactions history.
# Keep it fresh enough for cross-tab usage without repeating it on every
# dialog open or badge click. Server authorization is always authoritative.
BADGE_SYNC_TTL_SECONDS = 90
BADGE_ERROR_RETRY_SECONDS = 20


def badge_sync_due(state: dict, now: float, *, force: bool = False) -> bool:
    """Pure refresh policy, scoped by the dialog owner in open_badge_gallery."""
    if force:
        return True
    checked = state.get("badge_gallery_checked_at")
    if not isinstance(checked, (int, float)) or not 0 <= now - checked:
        return True
    if state.get("badge_gallery_synced") is True:
        return now - checked >= BADGE_SYNC_TTL_SECONDS
    if state.get("badge_gallery_sync_error") is True:
        return now - checked >= BADGE_ERROR_RETRY_SECONDS
    return True


def _current_profile() -> tuple[set[str], str]:
    user = st.session_state.get("current_user_data") or {}
    owned = set(parse_owned(user.get("보유배지", "")))
    equipped = str(user.get("장착배지") or "0")
    return owned, equipped if equipped in owned else "0"


def _apply_equipped_badge(target: str) -> None:
    """Preserve a transaction ID across network retries for the same selection."""
    pending = st.session_state.get("badge_pending_equip")
    if not isinstance(pending, dict) or pending.get("badge_id") != target:
        pending = {"badge_id": target, "request_id": transaction_id("equip")}
        st.session_state["badge_pending_equip"] = pending
    try:
        with st.spinner("배지 장착 정보를 저장하는 중…"):
            equip_badge(target, request_id=pending["request_id"])
    except TransactionError as exc:
        st.error(f"배지를 저장하지 못했다: {exc}")
        st.caption("네트워크 오류라면 같은 버튼을 다시 눌러 저장을 재시도할 수 있다.")
        return
    st.session_state.pop("badge_pending_equip", None)
    # The equip response is the authoritative profile. Do not make the next
    # gallery open scan the full ledger again just because a badge changed.
    st.session_state["badge_gallery_synced"] = True
    st.session_state["badge_gallery_sync_error"] = False
    st.session_state["badge_gallery_sync_message"] = ""
    st.session_state["badge_gallery_checked_at"] = monotonic()
    st.session_state["badge_flash_message"] = "배지를 해제했다." if target == "0" else "배지를 장착했다."
    st.rerun()


@st.dialog("BADGE ARCHIVE  ·  배지 컬렉션", width="small")
def badge_gallery_dialog() -> None:
    # A manual refresh remains available when awards arrive from another tab.
    count_col, refresh_col = st.columns([7, 1], gap="small")
    with refresh_col:
        refresh_now = st.button(
            "↻", key="badge_refresh_now", help="최신 배지와 업적 다시 불러오기",
            use_container_width=True,
        )

    now = monotonic()
    if badge_sync_due(st.session_state, now, force=refresh_now):
        st.session_state["badge_gallery_checked_at"] = now
        try:
            with st.spinner("최신 배지 정보를 불러오는 중…"):
                sync_badges_from_gateway()
            st.session_state["badge_gallery_synced"] = True
            st.session_state["badge_gallery_sync_error"] = False
            st.session_state["badge_gallery_sync_message"] = ""
        except TransactionError as exc:
            if exc.code == "OUTDATED_BADGE_GATEWAY":
                # Old servers reject badge_sync before touching the wallet.
                try:
                    refresh_account_from_gateway()
                    st.session_state["badge_gallery_synced"] = True
                    st.session_state["badge_gallery_sync_error"] = False
                    st.session_state["badge_gallery_sync_message"] = (
                        "새 은행 업적은 Apps Script를 최신 버전으로 배포하면 동기화된다."
                    )
                except TransactionError as fallback_error:
                    st.session_state["badge_gallery_synced"] = False
                    st.session_state["badge_gallery_sync_error"] = True
                    st.session_state["badge_gallery_sync_message"] = (
                        f"최신 배지 정보를 불러오지 못했다: {fallback_error}"
                    )
            else:
                st.session_state["badge_gallery_synced"] = False
                st.session_state["badge_gallery_sync_error"] = True
                st.session_state["badge_gallery_sync_message"] = (
                    f"최신 배지 정보를 불러오지 못했다: {exc}"
                )

    message = st.session_state.get("badge_gallery_sync_message")
    if message:
        if st.session_state.get("badge_gallery_sync_error"):
            st.warning(message)
        else:
            st.caption(message)

    owned, equipped = _current_profile()
    selected_id = st.session_state.get("badge_gallery_selected")
    if selected_id not in BADGE_BY_ID:
        selected_id = equipped if equipped != "0" else BADGES[0].id
        st.session_state["badge_gallery_selected"] = selected_id

    with count_col:
        st.html(
            '<div class="pc-badge-count">'
            f'획득 <b>{len(owned)} / {len(BADGES)}</b> '
            '· 컬러 = 획득 · 어두운 회색 = 미획득'
            '</div>',
        )

    # Only this square panel scrolls. The count, selected badge details,
    # equip/unequip actions, and the dialog close button stay OUTSIDE it.
    # Streamlit 1.55 enables native vertical scrolling for fixed-height
    # containers; CSS adjusts both dimensions to a responsive square.
    with st.container(height=320, border=True, key="badge_gallery"):
        for offset in range(0, len(BADGES), 4):
            columns = st.columns(4, gap="small")
            for index, column in enumerate(columns):
                badge_index = offset + index
                if badge_index >= len(BADGES):
                    continue
                badge = BADGES[badge_index]
                unlocked = badge.id in owned
                name_class = "is-equipped" if badge.id == equipped else (
                    "" if unlocked else "is-locked"
                )
                with column:
                    with st.container(key=f"badge_card_{badge.id}"):
                        if st.button(
                            badge.title,
                            key=f"badge_choose_{badge.id}",
                            help=f"{badge.title} · {badge.description}",
                            use_container_width=True,
                        ):
                            selected_id = badge.id
                            st.session_state["badge_gallery_selected"] = selected_id
                        st.html(
                            '<div class="pc-badge-tile-name '
                            f'{name_class}">{escape(badge.title)}</div>',
                        )

    # Generate the selected-card border after processing the current click.
    st.html(badge_gallery_css(serialize_owned(owned), selected_id))
    chosen = BADGE_BY_ID[selected_id]
    unlocked = selected_id in owned
    color = badge_accent(selected_id) if unlocked else "#73717B"
    art_uri = badge_image_data_uri(selected_id)
    art_markup = (
        f'<img src="{art_uri}" alt="" decoding="async" '
        f'style="{"filter:grayscale(1) brightness(.35);" if not unlocked else ""}" />'
        if art_uri else escape(badge_symbol(selected_id))
    )
    badge_status = "장착 중" if selected_id == equipped else (
        "획득 완료" if unlocked else "미획득"
    )
    st.html(
        f'<div class="pc-badge-detail">'
        f'<div class="pc-badge-detail-icon" style="color:{color}">'
        f'{art_markup}</div>'
        f'<div><div class="pc-badge-detail-rarity" style="color:{color}">'
        f'{RARITY_LABELS[chosen.rarity]} · {badge_status}</div>'
        f'<div class="pc-badge-detail-title">{escape(chosen.title)}</div>'
        f'<div class="pc-badge-detail-condition">해금 조건: '
        f'{escape(chosen.description)}</div></div></div>',
    )

    if not unlocked:
        st.caption("아직 얻지 못한 배지이다. 조건을 달성하면 컬러로 바뀐다.")
    elif st.session_state.get("badge_gallery_sync_error"):
        st.error("최신 보유 정보를 확인하지 못해 장착 기능을 사용할 수 없다.")
    elif selected_id == equipped:
        if st.button("장착 해제", key="badge_unequip", use_container_width=True):
            _apply_equipped_badge("0")
    else:
        if st.button("이 배지 장착", key="badge_equip", use_container_width=True):
            _apply_equipped_badge(selected_id)

    if equipped != "0" and selected_id != equipped and not st.session_state.get("badge_gallery_sync_error"):
        if st.button("배지 착용 안 함", key="badge_none", use_container_width=True):
            _apply_equipped_badge("0")


    # Badge clicks rerun only this dialog fragment, not the page router.
    render_loading_feedback()


def open_badge_gallery() -> None:
    """Initialize dialog state each time the main-screen button is pressed."""
    student_id = str(st.session_state.get("current_user", ""))
    if st.session_state.get("badge_gallery_owner") != student_id:
        st.session_state.pop("badge_gallery_selected", None)
        st.session_state.pop("badge_pending_equip", None)
        for key in (
            "badge_gallery_synced", "badge_gallery_sync_error",
            "badge_gallery_checked_at", "badge_gallery_sync_message",
        ):
            st.session_state.pop(key, None)
    st.session_state["badge_gallery_owner"] = student_id
    badge_gallery_dialog()
