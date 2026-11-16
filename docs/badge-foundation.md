# Badge foundation (20 titles)

This branch introduces the **catalog and deterministic achievement evaluator only**.
It does not grant badges in production, modify Google Sheets, add profile UI,
or change the betting/settlement gateway. Merge is safe for existing players.

## Fixed design

- One equipped badge, with its title bound to its icon.
- The main page and leaderboard display only the equipped badge icon.
- Common: normal nickname; Rare: cyan text; Epic: purple text.
- Legendary: individual effects identified by `effect` in the registry.
- 20 immutable IDs in `modules/badges.py`. Never renumber IDs.
- Unequipped value is `0`. Owned IDs serialize as space-separated strings.

## Proposed sheet migration (NOT executed)

Back up the spreadsheet, verify **Users!J and Users!K are empty**, and add:
- `Users!J`: `장착배지` (default `0`)
- `Users!K`: `보유배지` (default blank)

For accurate history and partial progress, create a separate `AchievementEvents`
sheet with immutable `round_id` as the deduplication key and fields:
`student_id, round_id, game, is_win, choice, predicted_digits, answer_digits, settled_at`.
Store only game results confirmed by the server, not client-supplied claims.
A player can own many badges but equip only one.

**Security and consistency:** the existing Apps Script transaction gateway locks
coin mutations and has idempotent settlement IDs. Future badge event writes
should occur under the same lock, or be reconciled from committed settlements.
Never update Users J/K with a client-side read-modify-write that can lose unlocks.
Do not change the 16-column Transactions schema or Users G/H/I assignments.

## Important historical limitation

Existing Transactions rows can prove completion, game, win/loss and streak.
They do not retain game 1 predicted/answer digits or game 2/3 choices.
Therefore old rounds cannot retroactively earn those detail-dependent badges
without an independent authoritative record. Do not fabricate these values.

## Evaluator contract

`evaluate_achievements(events)` accepts chronological **settled** event
dictionaries, keyed by unique `round_id`. Duplicate IDs are ignored.
It returns all badges justified by those events; the caller should union
the result with previously owned IDs to preserve lifetime unlocks.

A game-specific streak ignores other games' results; the global streak
resets after any loss. The five/eight-win mixed conditions require distinct
games within the same last five/eight consecutive global wins.
For game 1, the difference compares the two-digit prediction and answer
(00..99), not circular modulo arithmetic; `0.01%p` means a one-digit
hundredth difference. A hit is separate from a near miss.

## Next integration phase

1. Add a versioned, non-destructive schema installer and transactional
   badge updates to Apps Script.
2. Persist authoritative per-round detail once and compute progress after
   successful settlement (with retry/recovery).
3. Add equipped badge read/display to main and ranking, plus badge dialog.
4. Provide icon assets and four Legendary nameplate animations.
5. Add migration, concurrency, replay, and mobile UI tests.
