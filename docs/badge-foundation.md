# Badge foundation (20 titles)

This project now includes the catalog, a server-side achievement evaluator, and an atomic settlement write path. It does not install live sheet columns, deploy Apps Script, render badge icons, or implement the badge selection popup.

## Fixed design

- One equipped badge, with its title bound to its icon.
- The main page and leaderboard display only the equipped badge icon.
- Common: normal nickname; Rare: cyan text; Epic: purple text.
- Legendary: individual effects identified by `effect` in the registry.
- 20 immutable IDs in `modules/badges.py`. Never renumber IDs.
- Unequipped value is `0`. Owned IDs serialize as space-separated strings.

## Storage and migration

The existing `Transactions` sheet is the single authoritative round history.
For all *new* settlements, `Transactions!P` contains a `badge-v1:` JSON
payload with score digits (game 1) or choice (games 2 and 3).
Previous transactions remain readable; no Transactions columns change.

The separate `AchievementEvents` sheet proposed in the first draft is **not
needed**. The immutable `settle:<round_id>` record supplies the deduplication
key. Achievement progress can be recomputed from that history.

New Users fields (one row per player):
- `Users!J`: `장착배지` (default string `0`)
- `Users!K`: `보유배지` (space-separated stable IDs, default blank)

Only the Apps Script Web App may write newly earned badges under `ScriptLock`.
It commits the ledger settlement, wallet, and Users K in **one Sheets batch**.
Backups are required before running the non-destructive `installBadgeColumns()`
installer. The installer refuses to overwrite unrelated existing J/K values.

## Deployment steps

See [badge-awards-deployment.md](badge-awards-deployment.md). In particular,
copy BOTH `apps_script/Code.gs` and `apps_script/Badges.gs`, run
`installBadgeColumns()` as spreadsheet owner, and deploy a new Apps Script
Web App version before activating the new Streamlit code. Version 3 of the
wallet gateway blocks bets when the server is outdated or badge columns
are missing.

The connected Drive account available during development had read permission
but its sheet write attempt returned HTTP 403. No live spreadsheet cells
were changed by that attempt.

## Historical data limitations

Past settlements in Transactions can prove completion, game, wins and streaks,
so those achievements may be awarded retroactively when the player completes
their next settled round. But previous rows do not contain game 1 score digits
or game 2/3 choices, so those achievements **cannot** be retroactively granted
from those rows. An old game 1 win without two-digit evidence is also
insufficient proof for `g1_hit`, because past game rules were different.

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

## Remaining UI work

Read the returned `badges` profile on the main/ranking view, add an icon-only
nameplate and a modal for equip/unequip, and implement Legendary CSS effects.
The server-side equip endpoint is deliberately not included in this PR.
