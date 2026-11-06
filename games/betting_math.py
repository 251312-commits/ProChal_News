"""Pure calculations for shared betting UI (independent of Streamlit)."""

from decimal import Decimal, InvalidOperation
from operator import itemgetter

from modules.account_math import account_amount, net_coins


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


def ranking_entries(users_data):
    """Build fresh entries in sheet order so ties stay stable across projections."""
    entries = []
    for user in users_data or []:
        if isinstance(user, dict):
            loan = user.get("대출금", 0)
            entries.append({
                "id": str(user.get("학번", user.get("id", "")) or "").strip().removesuffix(".0"),
                "nickname": str(user.get("아이디", user.get("nickname", "")) or "").strip(),
                "coins": net_coins(user.get("코인"), loan),
                "loan": loan,
            })
    return entries


def rank_by_coins(entries):
    return sorted(entries, key=itemgetter("coins"), reverse=True)


def find_player(entries, current_sid, current_nickname):
    sid = str(current_sid or "").strip().removesuffix(".0")
    nickname = str(current_nickname or "").strip()
    matches = [user for user in entries if sid and user["id"] == sid]
    if len(matches) != 1:
        matches = [user for user in entries if nickname and user["nickname"] == nickname]
    return matches[0] if len(matches) == 1 else None


def project_standings(users_data, current_coins, current_sid, current_nickname, net_gain, *, current_loan=None):
    """Return both ranks and the projected leaderboard, including the player's rivals."""
    entries = ranking_entries(users_data)
    player = find_player(entries, current_sid, current_nickname)
    if player is None:
        return None, None, []

    # Pair the live wallet with live debt when a bank transaction is newer than the cache.
    loan = player["loan"] if current_loan is None else current_loan
    player["coins"] = net_coins(current_coins, loan)
    current_rank = rank_by_coins(entries).index(player) + 1

    player["coins"] += account_amount(net_gain)
    projected = rank_by_coins(entries)
    return current_rank, projected.index(player) + 1, projected


def project_rank_change(users_data, current_coins, current_sid, current_nickname, net_gain, *, current_loan=None):
    current_rank, projected_rank, _ = project_standings(
        users_data, current_coins, current_sid, current_nickname, net_gain, current_loan=current_loan
    )
    return current_rank, projected_rank
