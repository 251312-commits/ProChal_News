"""Mobile-friendly badge collection dialog on the main screen."""
from html import escape

import streamlit as st

from modules.badges import BADGES, BADGE_BY_ID, parse_owned
from modules.badge_display import (
    RARITY_LABELS, badge_accent, badge_gallery_css, badge_image_data_uri, badge_symbol,
)
from modules.transactions import (
    TransactionError, equip_badge, refresh_account_from_gateway,
    sync_badges_from_gateway, transaction_id,
)


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
        equip_badge(target, request_id=pending["request_id"])
    except TransactionError as exc:
        st.error(f"배지를 저장하지 못했다: {exc}")
        st.caption("네트워크 오류라면 같은 버튼을 다시 눌러 저장을 재시도할 수 있다.")
        return
    st.session_state.pop("badge_pending_equip", None)
    st.session_state["badge_gallery_synced"] = False
    st.session_state["badge_flash_message"] = "배지를 해제했다." if target == "0" else "배지를 장착했다."
    st.rerun()


@st.dialog("BADGE ARCHIVE  ·  배지 컬렉션", width="small")
def badge_gallery_dialog() -> None:
    if not st.session_state.get("badge_gallery_synced"):
        try:
            sync_badges_from_gateway()
            st.session_state["badge_gallery_synced"] = True
            st.session_state["badge_gallery_sync_error"] = False
        except TransactionError as exc:
            if exc.code == "OUTDATED_BADGE_GATEWAY":
                # During deployment, still show existing unlocked badges.
                try:
                    refresh_account_from_gateway()
                    st.session_state["badge_gallery_synced"] = True
                    st.session_state["badge_gallery_sync_error"] = False
                    st.caption("새 은행 업적은 Apps Script를 최신 버전으로 배포하면 동기화된다.")
                except TransactionError as refresh_error:
                    st.session_state["badge_gallery_sync_error"] = True
                    st.warning(f"최신 배지 정보를 불러오지 못했다: {refresh_error}")
            else:
                st.session_state["badge_gallery_sync_error"] = True
                st.warning(f"최신 배지 정보를 불러오지 못했다: {exc}")

    owned, equipped = _current_profile()
    selected_id = st.session_state.get("badge_gallery_selected")
    if selected_id not in BADGE_BY_ID:
        selected_id = equipped if equipped != "0" else BADGES[0].id
        st.session_state["badge_gallery_selected"] = selected_id

    st.html(
        '<div class="pc-badge-count">'
        f'획득 <b>{len(owned)} / {len(BADGES)}</b> '
        '· 컬러 = 획득 · 어두운 회색 = 미획득'
        '</div>',
    )

    # A 4-column grid stays usable on narrow phones, with vertically
    # scrolling dialog content. Locked badges still open their requirements.
    with st.container(key="badge_gallery"):
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
    st.html(badge_gallery_css(" ".join(owned), selected_id))
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


def open_badge_gallery() -> None:
    """Initialize dialog state each time the main-screen button is pressed."""
    student_id = str(st.session_state.get("current_user", ""))
    if st.session_state.get("badge_gallery_owner") != student_id:
        st.session_state.pop("badge_gallery_selected", None)
        st.session_state.pop("badge_pending_equip", None)
    st.session_state["badge_gallery_owner"] = student_id
    st.session_state["badge_gallery_synced"] = False
    st.session_state["badge_gallery_sync_error"] = False
    badge_gallery_dialog()
