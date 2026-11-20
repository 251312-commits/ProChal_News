"""Idempotent, serialized wallet operations through the Apps Script ledger.

Google Sheets' normal get-then-update API cannot perform compare-and-swap.
The deployed Apps Script holds LockService across the read, validation and
single Sheets batchUpdate for account columns plus the audit ledger.
"""
from __future__ import annotations

from uuid import uuid4

import requests
import streamlit as st

from modules.account_math import account_amount
from modules.badge_notifications import queue_badge_awards
from modules.account_ids import is_valid_student_id, is_valid_teacher_id
from modules.nickname import normalize_nickname


GATEWAY_VERSION = 3


class TransactionError(RuntimeError):
    """The transaction was not confirmed; do not show success."""

    def __init__(self, message: str, *, code: str = "SERVICE_ERROR"):
        super().__init__(message)
        self.code = code


class BalanceChanged(TransactionError):
    """Fresh sheet balance is incompatible with the requested operation."""

    def __init__(self, balances: dict, code: str):
        super().__init__(
            "잔액이 변경되었거나 부족합니다. 새 잔액을 확인한 뒤 다시 시도하세요.",
            code=code,
        )
        self.balances = balances


def transaction_id(kind: str) -> str:
    """Generate once per user action and retain the ID across network retries."""
    return f"{kind}:{uuid4().hex}"


def _request(payload: dict) -> dict:
    try:
        endpoint = st.secrets["transaction_endpoint"]
        token = st.secrets["transaction_token"]
        if not str(endpoint).startswith("https://script.google.com/macros/s/"):
            raise ValueError("Unexpected transaction endpoint")
        response = requests.post(
            endpoint, json={**payload, "token": token}, timeout=40,
        )
        response.raise_for_status()
        try:
            result = response.json()
        except ValueError as exc:
            raise TransactionError(
                "Apps Script가 JSON을 반환하지 않았습니다. 웹 앱 배포 URL(/exec)과 접근 권한을 확인하세요.",
                code="BAD_RESPONSE",
            ) from exc
    except (KeyError, ValueError, TypeError) as exc:
        raise TransactionError(
            "거래 서버 설정이나 응답을 확인할 수 없습니다. 관리자에게 문의하세요.",
            code="NOT_CONFIGURED",
        ) from exc
    except requests.RequestException as exc:
        # A timeout is NOT proof of failure. Retry using the same transaction ID.
        raise TransactionError(
            "거래 확인에 실패했습니다. 같은 거래를 다시 시도하세요.",
            code="NETWORK_ERROR",
        ) from exc

    if not isinstance(result, dict) or not isinstance(result.get("ok"), bool):
        raise TransactionError("거래 서버 응답 형식이 올바르지 않습니다.")
    if not result["ok"]:
        code = result.get("code", "SERVICE_ERROR")
        balance = result.get("balances")
        if code in {"STALE_BALANCE", "INSUFFICIENT_FUNDS"} and isinstance(balance, dict):
            raise BalanceChanged(balance, code)
        errors = {
            "BUSY": "거래가 몰렸습니다. 같은 요청으로 다시 시도하세요.",
            "UNCONFIRMED_BET": "확정된 베팅을 찾을 수 없습니다. 다시 베팅하세요.",
            "UNSETTLED_ROUND": "결과가 정산되지 않은 턴에는 이자를 부과할 수 없습니다.",
            "ALREADY_REGISTERED": "이미 가입한 학번입니다. 로그인하세요.",
            "INVALID_STUDENT_ID": "학교 학번 형식이 올바르지 않습니다.",
            "TEACHER_IDS_EXHAUSTED": "교사 ID 발급 가능 범위를 초과했습니다. 관리자에게 문의하세요.",
            "NOT_CONFIGURED": "거래 서버 설정이나 거래 원장 구성이 완료되지 않았습니다. Apps Script 설정을 확인하세요.",
            "PRINCIPAL_NOT_READY": (
                "Users 시트 H열 '대출원금'이 초기화되지 않았습니다. "
                "Apps Script에서 installTransactionLedger()를 실행한 뒤 다시 시도하세요."
            ),
            "MIGRATION_REQUIRED": (
                "이전 대출 내역과 시트 잔액이 일치하지 않아 자동 복원이 중단됐습니다. "
                "Transactions 내역을 확인해야 합니다."
            ),
            "INVALID_REQUEST": "서버에 전달한 거래 요청이 거부됐습니다. Apps Script 배포 버전을 확인하세요.",
            "UNAUTHORIZED": "Apps Script와 Streamlit의 거래 인증 토큰이 일치하지 않습니다.",
            "USER_NOT_FOUND": "거래 시트에서 로그인한 계정을 찾지 못했습니다.",
            "DUPLICATE_USER": "동일한 학번 계정이 중복되어 거래를 처리할 수 없습니다.",
            "IDEMPOTENCY_CONFLICT": "이 거래 번호가 다른 내용으로 사용되었습니다.",
            "BADGE_NOT_OWNED": "아직 획득하지 않은 배지는 장착할 수 없습니다.",
            "INVALID_BADGE": "선택한 배지를 찾을 수 없습니다.",
            "BADGES_NOT_READY": "Users 시트에 배지 열이 없습니다. Apps Script에서 installBadgeColumns()를 실행하세요.",
        }
        raise TransactionError(errors.get(code, "거래가 완료되지 않았습니다. 관리자에게 문의하세요."), code=code)
    if not isinstance(result.get("balances"), dict):
        raise TransactionError("거래 후 잔액을 확인할 수 없습니다.")
    return result


def _student_id() -> str:
    user = st.session_state.get("current_user_data") or {}
    return str(st.session_state.get("current_user") or user.get("학번") or "").strip().removesuffix(".0")


def update_session_balances(balances: dict) -> dict:
    """Refresh wallet, total debt and borrowed principal from a committed result."""
    normalized = {
        "코인": account_amount(balances["coins"], strict=True),
        "연승": account_amount(balances["streak"], strict=True),
        "대출금": account_amount(balances["loan"], strict=True),
    }
    # Historical receipts may omit principal; bank writes require this field.
    if "principal" in balances:
        normalized["대출원금"] = account_amount(balances["principal"], strict=True)
    user = st.session_state.get("current_user_data")
    if user is not None:
        user.update(normalized)
    return normalized


def refresh_account_from_gateway(*, require_badge_equip: bool = False,
                                 require_badge_sync: bool = False) -> dict:
    """Check gateway compatibility and refresh authoritative C/D/G/H.

    Mutations must not target gateways that omit the principal field;
    otherwise a committed loan may be incorrectly treated as a failure.
    """
    try:
        result = _request({
            "transaction_id": transaction_id("status"),
            "kind": "status", "student_id": _student_id(),
        })
    except TransactionError as exc:
        if exc.code == "INVALID_REQUEST":
            raise TransactionError(
                "거래 서버가 구버전일 가능성이 큽니다. 최신 apps_script/Code.gs를 "
                "Apps Script 웹 앱의 새 버전으로 배포하세요.",
                code="OUTDATED_GATEWAY",
            ) from exc
        raise
    if result.get("gateway_version") != GATEWAY_VERSION:
        raise TransactionError(
            "거래 서버와 앱 버전이 다릅니다. Apps Script 웹 앱을 최신 버전으로 배포하세요.",
            code="OUTDATED_GATEWAY",
        )
    if require_badge_equip and (result.get("badge_capabilities") or {}).get("equip") is not True:
        raise TransactionError(
            "배지 장착 기능을 사용하려면 최신 Code.gs를 Apps Script 새 버전으로 배포해야 합니다.",
            code="OUTDATED_BADGE_GATEWAY",
        )
    if require_badge_sync and (result.get("badge_capabilities") or {}).get("sync") is not True:
        raise TransactionError(
            "업적 동기화를 사용하려면 최신 Apps Script를 배포해야 합니다.",
            code="OUTDATED_BADGE_GATEWAY",
        )
    balances = result["balances"]
    if "principal" not in balances:
        raise TransactionError(
            "거래 서버 응답에 대출원금이 없습니다. Users H열 초기화를 확인하세요.",
            code="PRINCIPAL_NOT_READY",
        )
    update_session_balances(balances)
    _update_session_badges(result.get("badges"))
    return balances


def _update_session_badges(profile: object) -> tuple[str, ...]:
    """Copy only a server-confirmed badge profile into the current session."""
    if not isinstance(profile, dict):
        return ()
    from modules.badges import BADGE_BY_ID, serialize_owned
    raw_owned = profile.get("owned")
    if not isinstance(raw_owned, list) or any(not isinstance(item, str) for item in raw_owned):
        return ()
    owned = [item for item in raw_owned if item in BADGE_BY_ID]
    equipped = profile.get("equipped", "0")
    equipped = equipped if equipped in owned else "0"
    user = st.session_state.get("current_user_data")
    if isinstance(user, dict):
        user["장착배지"] = equipped
        user["보유배지"] = serialize_owned(owned)
    # Numeric progress is accepted only from the authenticated gateway.
    # Older deployments may omit this optional response field.
    raw_progress = profile.get("progress")
    if isinstance(raw_progress, dict):
        progress = {}
        for badge_id, entries in raw_progress.items():
            if badge_id not in BADGE_BY_ID or not isinstance(entries, list):
                continue
            valid = []
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                label, current, target = (
                    entry.get("label"), entry.get("current"), entry.get("target")
                )
                if (isinstance(label, str) and len(label) <= 80
                        and type(current) is int and type(target) is int
                        and 0 <= current <= target <= 1000000):
                    valid.append({"label": label, "current": current, "target": target})
            if valid:
                progress[badge_id] = valid
        st.session_state["badge_gallery_progress"] = progress
    unlocked = profile.get("unlocked", [])
    if not isinstance(unlocked, list):
        return ()
    return tuple(item for item in unlocked if isinstance(item, str) and item in BADGE_BY_ID and item in owned)


def sync_badges_from_gateway() -> tuple[str, ...]:
    """Reconcile bank achievements from the ledger and current wallet.

    This explicit operation is used when opening the badge dialog so that
    players who are already bankrupt can still collect their Mythic badge.
    A stale gateway is detected before attempting any server mutation.
    """
    # Badge sync returns the live wallet and badge profile under ScriptLock.
    try:
        result = _request({
            "transaction_id": transaction_id("badge_sync"),
            "kind": "badge_sync",
            "student_id": _student_id(),
        })
    except TransactionError as exc:
        if exc.code == "INVALID_REQUEST":
            # Older v3 deployments reject this operation before any mutation.
            raise TransactionError(
                "업적 동기화를 지원하지 않는 거래 서버입니다. 최신 Apps Script를 배포하세요.",
                code="OUTDATED_BADGE_GATEWAY",
            ) from exc
        raise
    profile = result.get("badges")
    if not isinstance(profile, dict):
        raise TransactionError("배지 동기화 결과를 확인할 수 없습니다.", code="BAD_RESPONSE")
    update_session_balances(result["balances"])
    unlocked = _update_session_badges(profile)
    if "progress" not in profile:
        st.session_state.pop("badge_gallery_progress", None)
    queue_badge_awards(unlocked)
    return unlocked


def equip_badge(badge_id: str, *, request_id: str | None = None) -> dict:
    """Persist one equipped badge (or '0' for none) under the gateway lock.

    The gateway, not the client, checks whether the player owns the selected
    badge. A caller may reuse request_id after a timeout to safely retry.
    """
    from modules.badges import BADGE_BY_ID

    if badge_id != "0" and badge_id not in BADGE_BY_ID:
        raise ValueError("Unknown badge identifier")
    # The gateway verifies badge ownership under ScriptLock.
    try:
        result = _request({
            "transaction_id": request_id or transaction_id("equip"),
            "kind": "equip",
            "student_id": _student_id(),
            "badge_id": badge_id,
        })
    except TransactionError as exc:
        if exc.code == "INVALID_REQUEST":
            raise TransactionError(
                "배지 장착을 지원하지 않는 거래 서버입니다. 최신 Apps Script를 배포하세요.",
                code="OUTDATED_BADGE_GATEWAY",
            ) from exc
        raise
    profile = result.get("badges")
    if not isinstance(profile, dict):
        raise TransactionError("장착한 배지 정보를 확인할 수 없습니다.", code="BAD_RESPONSE")
    update_session_balances(result["balances"])
    _update_session_badges(profile)
    # A retry may return a newer profile if another tab has changed the badge.
    if profile.get("equipped") != badge_id:
        raise TransactionError("다른 창에서 장착 배지가 변경됐습니다. 목록을 새로 확인하세요.", code="STALE_BADGE")
    return profile


def confirm_bet(game: str, amount: int) -> dict:
    """Validate the live wallet and append a bet confirmation under a lock.

    No stake is deducted until settlement; both points check the latest wallet.
    A persisted round ID guarantees retries cannot create a second bet record.
    """
    key = f"{game}_round_id"
    round_id = st.session_state.get(key)
    if not round_id:
        round_id = uuid4().hex
        st.session_state[key] = round_id
    # Confirm compatibility before committing even the first bet.
    refresh_account_from_gateway()
    result = _request({
        "transaction_id": f"bet:{round_id}",
        "kind": "bet", "round_id": round_id,
        "student_id": _student_id(), "game": game,
        "bet": int(amount),
    })
    update_session_balances(result["balances"])
    return result


def settle_game_round(game: str, amount: int, is_win: bool, *, badge_evidence: dict | None = None) -> dict:
    """Settle one round and commit earned badges atomically in Apps Script."""
    round_id = st.session_state.get(f"{game}_round_id")
    if not round_id:
        raise TransactionError("라운드 거래 번호가 없습니다. 베팅을 다시 확정하세요.")
    result = _request({
        "transaction_id": f"settle:{round_id}",
        "kind": "settle", "round_id": round_id,
        "student_id": _student_id(), "game": game,
        "bet": int(amount), "is_win": bool(is_win),
        "badge_evidence": badge_evidence or {},
    })
    update_session_balances(result["balances"])
    committed = result.get("settlement")
    if not isinstance(committed, dict):
        raise TransactionError("정산 기록의 잔액을 확인하지 못했습니다.")
    receipt = {
        "reward": account_amount(committed["delta"], strict=True),
        "new_coins": account_amount(committed["coins"], strict=True),
        "new_streak": account_amount(committed["streak"], strict=True),
        "new_loan": account_amount(committed["loan"], strict=True),
        "replayed": bool(result.get("replayed")),
    }
    newly_unlocked = _update_session_badges(result.get("badges"))
    receipt["unlocked_badges"] = newly_unlocked
    queue_badge_awards(newly_unlocked)
    st.session_state.pop("badge_gallery_checked_at", None)
    return receipt


def apply_round_interest(game: str) -> dict:
    """Accrue interest for a settled round once, under the ledger's script lock.

    The transaction ID is derived from the same confirmed round as settlement.
    A replay uses the original interest receipt while refreshing live balances.
    """
    round_id = st.session_state.get(f"{game}_round_id")
    if not round_id:
        raise TransactionError("라운드 거래 번호가 없어 이자를 부과할 수 없습니다.")
    refresh_account_from_gateway()
    result = _request({
        "transaction_id": f"interest:{round_id}",
        "kind": "interest", "round_id": round_id,
        "student_id": _student_id(), "game": game,
    })
    interest = result.get("interest")
    if not isinstance(interest, dict):
        raise TransactionError("이자 부과 기록을 확인할 수 없습니다.")
    try:
        charged = account_amount(interest["charged"], strict=True)
        loan_before = account_amount(interest["loan_before"], strict=True)
        loan_after = account_amount(interest["loan_after"], strict=True)
    except (KeyError, TypeError, ValueError) as exc:
        raise TransactionError("이자 부과 기록의 금액이 올바르지 않습니다.") from exc
    if loan_after - loan_before != charged:
        raise TransactionError("이자 계산 기록이 일치하지 않습니다.")
    update_session_balances(result["balances"])
    queue_badge_awards(_update_session_badges(result.get("badges")))
    st.session_state.pop("badge_gallery_checked_at", None)
    return {
        "charged": charged, "loan_before": loan_before,
        "new_loan": loan_after, "replayed": bool(result.get("replayed")),
    }


def bank_transaction(kind: str, amount: int, tx_id: str) -> dict:
    """Borrow or repay atomically with an expected balance check and ledger row."""
    if kind not in ("borrow", "repay"):
        raise ValueError("Invalid bank operation")
    # A capability probe is required before any mutation, and also refreshes
    # stale session balances from another tab or an already completed request.
    refresh_account_from_gateway()
    user = st.session_state.get("current_user_data") or {}
    if user.get("대출원금") is None or user.get("대출원금") == "":
        raise TransactionError("대출원금 정보가 없습니다. 계정 데이터를 갱신한 후 다시 시도하세요.")
    result = _request({
        "transaction_id": tx_id,
        "kind": kind, "student_id": _student_id(),
        "amount": int(amount),
        "expected_coins": account_amount(user.get("코인"), strict=True),
        "expected_loan": account_amount(user.get("대출금"), strict=True),
        "expected_principal": account_amount(user["대출원금"], strict=True),
    })
    if "principal" not in result["balances"]:
        raise TransactionError("거래 서버에 대출원금 관리 기능이 적용되지 않았습니다.", code="NOT_CONFIGURED")
    update_session_balances(result["balances"])
    queue_badge_awards(_update_session_badges(result.get("badges")))
    st.session_state.pop("badge_gallery_checked_at", None)
    return result


def register_player(student_id: str, nickname: str, password: str,
                    referrer_id: str, tx_id: str) -> dict:
    """Create an account and credit both referral bonuses in one Sheets batch."""
    if not is_valid_student_id(student_id):
        raise TransactionError("학교 학번 형식이 올바르지 않습니다.", code="INVALID_STUDENT_ID")
    try:
        nickname = normalize_nickname(nickname)
    except ValueError as exc:
        raise TransactionError(str(exc), code="INVALID_NICKNAME") from exc
    result = _request({
        "transaction_id": tx_id, "kind": "register",
        "student_id": student_id, "nickname": nickname,
        "password": password, "referrer_id": referrer_id,
    })
    return result["balances"]


def register_teacher(nickname: str, password: str, tx_id: str) -> dict:
    """Allocate a unique teacher ID and create an account in one gateway transaction."""
    try:
        nickname = normalize_nickname(nickname)
    except ValueError as exc:
        raise TransactionError(str(exc), code="INVALID_NICKNAME") from exc
    try:
        result = _request({
            "transaction_id": tx_id, "kind": "register_teacher",
            "student_id": "", "nickname": nickname, "password": password,
            "referrer_id": "",
        })
    except TransactionError as exc:
        if exc.code == "INVALID_REQUEST":
            raise TransactionError(
                "거래 서버가 교사 회원가입을 지원하지 않습니다. "
                "최신 Apps Script 웹 앱 버전을 배포해 주세요.",
                code="OUTDATED_GATEWAY",
            ) from exc
        raise
    assigned_id = result.get("student_id")
    if not is_valid_teacher_id(assigned_id):
        raise TransactionError("교사 ID 발급 결과가 올바르지 않습니다.", code="BAD_RESPONSE")
    return {"student_id": assigned_id, "balances": result["balances"]}
