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
        result = response.json()
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
            "ALREADY_REGISTERED": "이미 가입한 학번입니다. 로그인하세요.",
            "NOT_CONFIGURED": "거래 서버가 준비되지 않았습니다. 관리자에게 문의하세요.",
            "IDEMPOTENCY_CONFLICT": "이 거래 번호가 다른 내용으로 사용되었습니다.",
        }
        raise TransactionError(errors.get(code, "거래가 완료되지 않았습니다. 관리자에게 문의하세요."), code=code)
    if not isinstance(result.get("balances"), dict):
        raise TransactionError("거래 후 잔액을 확인할 수 없습니다.")
    return result


def _student_id() -> str:
    user = st.session_state.get("current_user_data") or {}
    return str(st.session_state.get("current_user") or user.get("학번") or "").strip().removesuffix(".0")


def update_session_balances(balances: dict) -> dict:
    """Update the three account fields only after a confirmed server result."""
    normalized = {
        "코인": account_amount(balances["coins"], strict=True),
        "연승": account_amount(balances["streak"], strict=True),
        "대출금": account_amount(balances["loan"], strict=True),
    }
    user = st.session_state.get("current_user_data")
    if user is not None:
        user.update(normalized)
    return normalized


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
    result = _request({
        "transaction_id": f"bet:{round_id}",
        "kind": "bet", "round_id": round_id,
        "student_id": _student_id(), "game": game,
        "bet": int(amount),
    })
    update_session_balances(result["balances"])
    return result


def settle_game_round(game: str, amount: int, is_win: bool) -> dict:
    """Apply a single game's payout and streak, returning the committed snapshot."""
    round_id = st.session_state.get(f"{game}_round_id")
    if not round_id:
        raise TransactionError("라운드 거래 번호가 없습니다. 베팅을 다시 확정하세요.")
    result = _request({
        "transaction_id": f"settle:{round_id}",
        "kind": "settle", "round_id": round_id,
        "student_id": _student_id(), "game": game,
        "bet": int(amount), "is_win": bool(is_win),
    })
    update_session_balances(result["balances"])
    committed = result.get("settlement")
    if not isinstance(committed, dict):
        raise TransactionError("정산 기록의 잔액을 확인하지 못했습니다.")
    return {
        "reward": account_amount(committed["delta"], strict=True),
        "new_coins": account_amount(committed["coins"], strict=True),
        "new_streak": account_amount(committed["streak"], strict=True),
        "new_loan": account_amount(committed["loan"], strict=True),
        "replayed": bool(result.get("replayed")),
    }


def bank_transaction(kind: str, amount: int, tx_id: str) -> dict:
    """Borrow or repay atomically with an expected balance check and ledger row."""
    if kind not in ("borrow", "repay"):
        raise ValueError("Invalid bank operation")
    user = st.session_state.get("current_user_data") or {}
    result = _request({
        "transaction_id": tx_id,
        "kind": kind, "student_id": _student_id(),
        "amount": int(amount),
        "expected_coins": account_amount(user.get("코인"), strict=True),
        "expected_loan": account_amount(user.get("대출금"), strict=True),
    })
    update_session_balances(result["balances"])
    return result


def register_player(student_id: str, nickname: str, password: str,
                    referrer_id: str, tx_id: str) -> dict:
    """Create an account and credit both referral bonuses in one Sheets batch."""
    result = _request({
        "transaction_id": tx_id, "kind": "register",
        "student_id": student_id, "nickname": nickname,
        "password": password, "referrer_id": referrer_id,
    })
    return result["balances"]
