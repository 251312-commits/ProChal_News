# Badge collection and equip deployment

This change adds a **mobile-friendly BADGE ARCHIVE** button above the main
promo banner. The popup shows all 25 permanent achievements in one grid:
- Earned: rarity color (Common silver, Rare cyan, Epic purple, five Legendary colors, and two Mythic colors).
- Locked: dark-grey symbol and label; tap to inspect unlock requirement.
- Tap an earned symbol to inspect its title, rarity, and condition; select
  **이 배지 장착** to persist the equipped ID to Users!J.
- **장착 해제** or **배지 착용 안 함** stores `0`. Ownership in Users!K is unchanged.
- The equipped symbol appears beside the nickname on the main banner and
  the ranking cards, alongside Rare/Epic text colors and unique Legendary/Mythic effects.
- Symbol definitions are centralized in `modules/badge_display.py`; replace
  these Unicode glyphs with checked-in icons/images without changing badge IDs.

## Apps Script deployment is required before equipping

The old deployed version-3 transaction gateway still supports badge unlocks,
but it does not understand the new `equip` operation. This PR deliberately
keeps the general `gateway_version = 3` so that **betting and banking do not
stop working** during this optional feature upgrade.

1. Back up the `ProChal` Google Sheet (no additional sheet columns needed).
2. Copy the updated `apps_script/Code.gs` into the *same* Apps Script project
   already containing `Badges.gs`. Keep `Badges.gs` unchanged.
3. Deploy a **new web app version** through Apps Script > Deploy > Manage
   deployments > Edit > New version > Deploy. Do not only save the editor.
4. Open the Streamlit app after merging this PR, and click the collection button.
5. Try an earned badge, verify `Users!J` contains its ID, reload,
   then try `장착 해제` and verify J becomes `0`. Users K should not change.
6. Verify a locked badge cannot be equipped, and that the badge shows on the
   leaderboard after the (existing) 10-second ranking cache refresh.

## Server-side safety

The new `equip:<uuid>` operation is authorized by the existing
server-only transaction token and calls the same gateway under ScriptLock.
The server verifies the badge is in **that account's own Users!K**.
It commits Users!J and an audit ledger row together in a Sheets batch.
Replaying an identical request returns the saved profile without a duplicate
write; changing its badge ID is an idempotency conflict.
No wallet, debt, balance, streak, or badge ownership is modified.

The Python client probes `badge_capabilities.equip` before sending a
mutation. If Apps Script has not been redeployed yet, the popup reports the
missing feature but the rest of the game stays functional.

## Verification

Run:
- `python -m unittest discover -s tests -v`
- `node --test tests/test_transaction_gateway.cjs`

Automated tests simulate Google Sheets/LockService, including a failed
batch, replays, cross-user ownership, locked badges, and client capability
probing. Manual mobile browser checks remain necessary for actual dialog
layout and animations.

## New bank and Mythic achievements (25 total)

| Badge | Tier | Server-confirmed unlock |
|---|---|---|
| 전설의 정복자 | MYTHIC / gold | Own all **five** Legendary badges (including 금리의 생존자); Mythic badges are excluded from the requirement |
| 파산 선고 | MYTHIC / red | Coins < 1,000C **and** remaining principal credit < 1,000C (no minimum additional borrowing) |
| 금리의 생존자 | LEGENDARY | A single borrowing of at least 5,000C, followed by **five distinct settled turn-end interest receipts while debt remains outstanding**, then repay the **entire loan including interest** |
| 첫 신용 | COMMON | First successful bank borrowing |
| 첫 상환 | COMMON | First successful repayment of at least 1C |

The bank minimum borrowing increment is 1,000C, the outstanding principal cap
is 10,000C, and loan interest compounds by 20% per completed round. A partial
repayment or an early full repayment does **not** grant the Legendary finance badge.

Successful borrow/repay/settle/interest operations award badges atomically
inside the existing Apps Script transaction. Historical successful borrow and
repayment entries can be recognized when the player next makes a transaction.
Opening the badge collection also invokes the authenticated `badge_sync`
reconciliation action. This covers players who were **already bankrupt**
before deployment and cannot place a new bet or take a new loan. The normal
`status` balance probe remains read-only; `badge_sync` writes an audit
entry only when one or more missing badges are actually earned.
An already earned badge is retained even if the user later borrows again or
recovers from bankruptcy.

### Upgrade

1. Back up the spreadsheet, but **do not add columns**: Users J/K and
   Transactions A:P stay unchanged.
2. Copy updated `apps_script/Badges.gs` **and** `apps_script/Code.gs`
   into the existing Apps Script project.
3. Publish a **new web-app deployment version**.
4. Merge the GitHub PR and restart/redeploy Streamlit.
5. Verify successful bank borrow/repay awards and the new 25-item gallery.

The Python UI continues to accept the previous 20 permanent IDs. The new IDs
are appended, never renumbered or reused.
