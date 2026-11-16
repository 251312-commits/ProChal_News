# Badge awards / Google Sheets deployment

This change is not active merely because the GitHub PR is merged.
Apps Script is deployed separately and the live spreadsheet must be migrated.

## Safe rollout (spreadsheet owner)

1. Back up the existing **ProChal** spreadsheet.
2. In Users, inspect **J:K**. They must be unused or already be the intended
   `장착배지` / `보유배지` headers. G (debt), H (principal), I (last URL)
   remain untouched. Transactions A:P must retain its existing headers.
3. Copy both `apps_script/Code.gs` **and** `apps_script/Badges.gs` into the
   bound Apps Script project as separate script files. Enable the existing
   Google Sheets API v4 advanced service.
4. In Apps Script, run **`installBadgeColumns()`** as spreadsheet owner.
   It checks for conflicting data, adds Users J/K headers and initializes
   empty J account cells to string `0`. It does not delete any existing badge.
5. Reopen the sheet: verify J1=`장착배지`, K1=`보유배지`,
   J2:J(last user)=`0`, and K empty for new users. Check C/D/G/H and
   Transactions header are unchanged.
6. **Deploy > Manage deployments > Edit > New version > Deploy** to publish
   the new Apps Script code. Editing the source without a new deployment does
   not update the Streamlit `transaction_endpoint` deployment. Reuse the
   same valid `transaction_token`.
7. Deploy/merge the Python game code after the new Apps Script version.
   The Python client checks `gateway_version == 3` before placing bets or
   changing bank balances; old gateway versions are rejected before any money
   mutation.
8. On a test account, play a round of game 1 missing by 0.01%p and confirm:
   - The Transactions settle row P begins `badge-v1:`.
   - Users K includes the appropriate IDs.
   - Users J remains `0` (no equip UI implemented yet).
   - The wallet delta and per-turn interest remain correct.
   Reopen result/retry and verify no extra settled rows or badge grants.
9. Test games 2/3 choice tracking, games 4/5 completion, 3- and 5-win
   achievements, second account isolation, and failures during settlement.

## How the badge write works

A `settle:<round_id>` request carries server-side evidence already used
to decide win/loss. Under one ScriptLock the gateway validates the bet,
calculates the payout, appends the settlement with evidence in existing
Transactions P, replays all completed settlements for that player, and
updates Users K only if new badges were earned.

The wallet update, settlement row and badge update are committed in a
**single Google Sheets batchUpdate**, so a failed write does not partially
change coins or awards. Repeating the same transaction ID returns the
recorded result without awarding again; a changed score proof is rejected.

The existing settlement ledger gives historical counts and streaks.
Older rows without score digits or choices cannot satisfy achievements
that specifically require those details.

## Known constraints

- The Google Drive connector can read the target sheet but **was denied
  write permission (HTTP 403)**. The installer above must therefore be
  executed in Apps Script with owner/editor permissions.
- `installBadgeColumns()` and publishing the Apps Script Web App cannot
  be executed by GitHub merge alone.
- Badge icon rendering, nameplate color/effects, and equip/unequip UI are
  not part of this step.
- The game server's existing authentication model and transaction token
  are reused. Never put the transaction token in browser-side JavaScript.
