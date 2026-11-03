"""Pure calculations for shared betting UI (independent of Streamlit)."""

from decimal import Decimal, InvalidOperation


def _as_int(value):
    """Parse Google Sheets coin values without changing an invalid row to a crash."""
    try:
        return int(str(value).strip().replace(",", ""))
    except (ValueError, TypeError):
        try:
            return int(float(str(value).strip().replace(",", "")))
        except (ValueError, TypeError, OverflowError):
            return 0


def calculate_expected_gain(bet_amount, payout_multiplier):
    """Net coin increase on a win (not the stake-inclusive gross return).

    A game that adds 100 * bet to the user's stored balance passes 100.
    This matches the existing game_1 settlement behavior.
    """
    try:
        multiplier = Decimal(str(payout_multiplier))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("payout_multiplier must be a finite non-negative number") from exc
    if not multiplier.is_finite() or multiplier < 0:
        raise ValueError("payout_multiplier must be a finite non-negative number")
    return int(Decimal(int(bet_amount)) * multiplier)


def format_payout_multiplier(payout_multiplier):
    """Canonical UI text, e.g. 1.9x or 100x."""
    # Validate identically to calculate_expected_gain.
    calculate_expected_gain(0, payout_multiplier)
    return f"{Decimal(str(payout_multiplier)).normalize():f}x"


def project_rank_change(users_data, current_coins, current_sid, current_nickname, net_gain):
    """Return (current_rank, projected_win_rank), using ranking page's ordinal order.

    If the current user cannot be identified uniquely, return (None, None)
    instead of inventing rank 1. Match student ID first; nickname only when
    unique. Ties are resolved by the original sheet order, as in ranking.py.
    The active user's session coin balance overrides stale cached sheet data.
    """
    if not users_data:
        return None, None

    sid = str(current_sid or "").strip().removesuffix(".0")
    nickname = str(current_nickname or "").strip()
    normalized = []
    for user in users_data:
        if not isinstance(user, dict):
            continue
        user_sid = str(user.get("학번", user.get("id", "")) or "").strip().removesuffix(".0")
        user_nickname = str(user.get("아이디", user.get("nickname", "")) or "").strip()
        normalized.append({
            "sid": user_sid,
            "nickname": user_nickname,
            "coins": _as_int(user.get("코인", 0)),
        })

    if not normalized:
        return None, None

    matches = [i for i, user in enumerate(normalized) if sid and user["sid"] == sid]
    if len(matches) != 1:
        matches = [i for i, user in enumerate(normalized) if nickname and user["nickname"] == nickname]
    if len(matches) != 1:
        return None, None

    my_index = matches[0]
    normalized[my_index]["coins"] = _as_int(current_coins)
    before_order = sorted(range(len(normalized)), key=lambda idx: normalized[idx]["coins"], reverse=True)
    current_rank = before_order.index(my_index) + 1

    normalized[my_index]["coins"] += _as_int(net_gain)
    after_order = sorted(range(len(normalized)), key=lambda idx: normalized[idx]["coins"], reverse=True)
    projected_rank = after_order.index(my_index) + 1
    return current_rank, projected_rank
