"""Badge definitions and pure achievement evaluation. No sheet writes or UI side effects.

Every game completion is identified by its settled round_id. This module consumes
normalized, chronologically ordered events, not untrusted browser-provided wins.
The public API and immutable IDs from main are retained; the catalog is shared
with badge_service and the Apps Script engine rather than defined twice.
"""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable

from modules.badge_service import (
    absorb_profile, collection_enabled, get_catalog, remember_capabilities, settlement_fields,
)


@dataclass(frozen=True)
class Badge:
    id: str
    title: str
    game: str
    description: str
    rarity: str
    effect: str = ""


BADGES = tuple(
    Badge(item["id"], item["name"], item["game"], item["achievement"], item["rarity"],
          "" if item["effect"]["animation"] == "none" else item["effect"]["animation"])
    for item in get_catalog()["badges"]
)
BADGE_BY_ID = {badge.id: badge for badge in BADGES}
RARITIES = ("common", "rare", "epic", "legendary")
GAMES = frozenset(f"game_{i}" for i in range(1, 6))


def parse_owned(value: object) -> tuple[str, ...]:
    """Parse space-separated badge IDs, ignoring unknown IDs and duplicates."""
    if not isinstance(value, str):
        return ()
    return tuple(dict.fromkeys(item for item in value.split() if item in BADGE_BY_ID))


def serialize_owned(ids: Iterable[str]) -> str:
    """Store canonical catalog order, not equip order."""
    owned = set(ids)
    return " ".join(b.id for b in BADGES if b.id in owned)


def equipped_badge(value: object, owned: Iterable[str]) -> Badge | None:
    """0 or blank means unequipped; reject badges the player does not own."""
    key = str(value or "").strip()
    return BADGE_BY_ID.get(key) if key in set(owned) else None


def _hundredths(value: object) -> int | None:
    """Convert a percentage score into integer hundredths without float drift."""
    try:
        decimal = Decimal(str(value))
        if not decimal.is_finite() or decimal < 0 or decimal > 100:
            return None
        cents = decimal * 100
        return int(cents) if cents == cents.to_integral_value() else None
    except (InvalidOperation, TypeError, ValueError):
        return None


def evaluate_achievements(events: Iterable[dict]) -> set[str]:
    """Derive earned badges from ordered *settled* events.

    Each event: round_id, game, is_win; optional choice for games 2/3 and
    predicted_digits/answer_digits for game 1 (00..99).
    Events must be ordered oldest first. Repeated round IDs are ignored.
    """
    earned: set[str] = set()
    seen: set[str] = set()
    plays = {g: 0 for g in GAMES}
    wins = {g: 0 for g in GAMES}
    game_streak = {g: 0 for g in GAMES}
    choices = {"game_2": {}, "game_3": {}}
    streak_games: list[str] = []

    for event in events:
        if not isinstance(event, dict):
            continue
        round_id = str(event.get("round_id", "")).strip()
        game = event.get("game")
        if not round_id or round_id in seen or game not in GAMES or type(event.get("is_win")) is not bool:
            continue
        seen.add(round_id)
        won = event["is_win"]
        plays[game] += 1
        if won:
            wins[game] += 1
            game_streak[game] += 1
            streak_games.append(game)
        else:
            game_streak[game] = 0
            streak_games.clear()

        if sum(plays.values()) >= 1:
            earned.add("first_round")
        if all(plays.values()):
            earned.add("all_games")
        if sum(plays.values()) >= 30:
            earned.add("thirty_rounds")
        if len(streak_games) >= 3:
            earned.add("streak_three")
        if len(streak_games) >= 5 and len(set(streak_games[-5:])) >= 2:
            earned.add("streak_five_mixed")
        if len(streak_games) >= 8 and len(set(streak_games[-8:])) >= 3:
            earned.add("streak_eight_mixed")

        if game == "game_1":
            if plays[game] >= 10:
                earned.add("g1_ten")
            pred, answer = event.get("predicted_digits"), event.get("answer_digits")
            if type(pred) is int and type(answer) is int and 0 <= pred <= 99 and 0 <= answer <= 99:
                difference = abs(pred - answer)
                if won and difference == 0:
                    earned.add("g1_hit")
                if not won:
                    if 0 < difference <= 10:
                        earned.add("g1_within_ten")
                    if 0 < difference <= 3:
                        earned.add("g1_within_three")
                    if difference == 10:
                        earned.add("g1_exact_ten")
                    if difference == 1:
                        earned.add("g1_exact_one")
        if game == "game_2":
            if wins[game] >= 10:
                earned.add("g2_ten_wins")
            choice = event.get("choice")
            if won and choice in ("HIGH", "LOW"):
                choices[game][choice] = choices[game].get(choice, 0) + 1
            if all(choices[game].get(k, 0) >= 15 for k in ("HIGH", "LOW")):
                earned.add("g2_both_fifteen")
        if game == "game_3":
            choice = event.get("choice")
            if won and choice in ("홀", "짝"):
                choices[game][choice] = choices[game].get(choice, 0) + 1
            if all(choices[game].get(k, 0) >= 5 for k in ("홀", "짝")):
                earned.add("g3_both_five")
            if game_streak[game] >= 5:
                earned.add("g3_five_streak")
        if game == "game_4":
            if wins[game] >= 5:
                earned.add("g4_five_wins")
            if game_streak[game] >= 4:
                earned.add("g4_four_streak")
        if game == "game_5":
            if wins[game] >= 3:
                earned.add("g5_three_wins")
            if game_streak[game] >= 3:
                earned.add("g5_three_streak")
    return earned
