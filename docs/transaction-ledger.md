# Transaction ledger deployment

The old game code used get-then-update Sheets writes. These calls are not atomic, even with a balance comparison. The new code is **fail-closed** until an Apps Script gateway is deployed. Do not merge into production without completing this setup.

## Setup

1. Back up the spreadsheet. Verify the Users columns: A 학번, B 아이디, C 코인, D 연승, E 추천인, F 비밀번호, G 대출금. **Users!H 대출원금** is added by the revised installer; G remains total debt including interest, while H tracks outstanding borrowed principal excluding interest.
2. Create a Google Apps Script project as the spreadsheet owner. Copy the files from apps_script/; enable the Google Sheets API v4 advanced service in Apps Script and, if needed, its Cloud project.
3. Set Script Properties SPREADSHEET_ID (the sheet ID, not URL) and TRANSACTION_TOKEN (an independently generated random secret of at least 32 bytes).
4. **Re-run** `installTransactionLedger()` in Apps Script before deploying the new code. The installer creates and backfills Users!H (`대출원금`) from historical Transactions records when present, otherwise from the legacy G balance. This permits H to remain at 8,000C after 1,600C of interest has increased G to 9,600C. It refuses inconsistent loan histories or an already occupied H column. Verify that H was initialized for each player and that Transactions has the original 16 named columns. Protect ledger contents.
5. Deploy as Web App: execute as Me; access Anyone. Copy the HTTPS /exec URL.
6. In private Streamlit secrets add:

```toml
transaction_endpoint = "https://script.google.com/macros/s/DEPLOYMENT_ID/exec"
transaction_token = "SAME_SECRET_AS_APPS_SCRIPT"
```

Keep the existing gcp_service_account for read-only account views and News sheet updates. Do not expose the transaction token in the frontend. Restrict editor access to the spreadsheet; **all writes to Users C/D/G must pass through this gateway**. Apps Script locks cannot protect against edits made directly through gspread or in the Sheets UI.

## Guarantees

- The five games call confirm_bet() at bet confirmation and settle_game_round() once after analysis, each validating the live wallet under a shared ScriptLock.
- Each UUID round produces one bet:<uuid>, one settle:<uuid>, and one interest:<uuid> transaction. Duplicate requests return the original receipt instead of applying the operation twice. Conflicting reuse of a transaction ID is rejected.
- Immediately before displaying a settled game's result, the shared turn-end helper requests **20% compound interest** on the current outstanding loan (Users!G). The interest is rounded **up to the next whole coin**: 1,000C → 1,200C → 1,440C after two turns. It never subtracts from wallet coins (Users!C) or changes the streak (Users!D).
- Interest requires a matching committed settlement for the same player, game, and round. Even a 0C loan gets an interest ledger entry, preventing an old results screen from charging a loan taken later.
- The stake is not deducted on confirmation (existing behavior). Settlement verifies a matching confirmed bet and available coins again; another tab may consume the balance between steps, in which case no settlement occurs.
- The server enforces payout rules: game 1 +100×; games 2/3 +1×; game 4 +2×; game 5 +5×. Game 3 losses cost half the bet; other losses cost the whole bet. Winning increments the streak; losing resets it.
- Borrowing and repayment compare the current C/G/H wallet, total debt and principal to the displayed snapshot under lock. The 10,000C borrowing cap applies **only to unpaid borrowed principal (Users!H)**. Interest is added only to Users!G and may take total debt beyond 10,000C. Example: 8,000C principal + 1,600C interest = 9,600C total, yet 2,000C additional borrowing is available and leads to 10,000C principal / 11,600C total. Repayments pay accumulated interest first, then principal. Borrowing uses 1,000C increments (or final small repayment).
- C/D/G/H and a ledger row are submitted in one Sheets spreadsheets.batchUpdate request. Google Sheets applies all requests in a batch atomically. Registration and referral credits are also bundled in a single batch.
- On timeout the transaction might have committed. The client retains its transaction ID for a safe retry.

## Limitations and verification

- LockService serializes requests **only through this Apps Script**; external writers bypass the guarantee. Prevent or migrate such writes.
- **Deploy the updated apps_script/Code.gs as a new Apps Script Web App version first** (and update Streamlit's transaction_endpoint if the deployment URL changes). The older gateway does not recognize the new interest transaction; until updated, result screens will block rather than silently skip interest.
- Verify 20% interest after each of games 1–5, zero-debt turns, retries after lost responses, and a second turn's interest on the increased debt. Inspect Users!G (total debt), Users!H (principal) and the immutable Transactions interest:<round_id> rows. Old clients signed in before migration should sign in again to refresh H.
- User passwords remain in the original Users sheet layout; password security merits a separate migration.
- Before deployment run all unit tests, then verify borrow, repay, game win/loss, duplicate settlement, two-tab concurrent spends, signup and referral on isolated test accounts. Reconcile the Transactions ledger with Users C/D/G and retain a backup.
