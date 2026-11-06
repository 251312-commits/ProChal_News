# Transaction ledger deployment

The old game code used get-then-update Sheets writes. These calls are not atomic, even with a balance comparison. The new code is **fail-closed** until an Apps Script gateway is deployed. Do not merge into production without completing this setup.

## Setup

1. Back up the spreadsheet. Verify the Users columns: A 학번, B 아이디, C 코인, D 연승, E 추천인, F 비밀번호, G 대출금.
2. Create a Google Apps Script project as the spreadsheet owner. Copy the files from apps_script/; enable the Google Sheets API v4 advanced service in Apps Script and, if needed, its Cloud project.
3. Set Script Properties SPREADSHEET_ID (the sheet ID, not URL) and TRANSACTION_TOKEN (an independently generated random secret of at least 32 bytes).
4. Run installTransactionLedger() from the Apps Script editor and verify that the Transactions tab has the 16 named columns. Protect its contents.
5. Deploy as Web App: execute as Me; access Anyone. Copy the HTTPS /exec URL.
6. In private Streamlit secrets add:

```toml
transaction_endpoint = "https://script.google.com/macros/s/DEPLOYMENT_ID/exec"
transaction_token = "SAME_SECRET_AS_APPS_SCRIPT"
```

Keep the existing gcp_service_account for read-only account views and News sheet updates. Do not expose the transaction token in the frontend. Restrict editor access to the spreadsheet; **all writes to Users C/D/G must pass through this gateway**. Apps Script locks cannot protect against edits made directly through gspread or in the Sheets UI.

## Guarantees

- The five games call confirm_bet() at bet confirmation and settle_game_round() once after analysis, each validating the live wallet under a shared ScriptLock.
- Each UUID round produces one bet:<uuid> and one settle:<uuid> transaction. Duplicate requests return their original settled snapshot instead of paying again. Conflicting reuse of a transaction ID is rejected.
- The stake is not deducted on confirmation (existing behavior). Settlement verifies a matching confirmed bet and available coins again; another tab may consume the balance between steps, in which case no settlement occurs.
- The server enforces payout rules: game 1 +100×; games 2/3 +1×; game 4 +2×; game 5 +5×. Game 3 losses cost half the bet; other losses cost the whole bet. Winning increments the streak; losing resets it.
- Borrowing and repayments compare the current C/G wallet and debt to the displayed snapshot under lock, enforce 1,000C increments (or final small repayment) and cap debt at 10,000C.
- C/D/G and a ledger row are submitted in one Sheets spreadsheets.batchUpdate request. Google Sheets applies all requests in a batch atomically. Registration and referral credits are also bundled in a single batch.
- On timeout the transaction might have committed. The client retains its transaction ID for a safe retry.

## Limitations and verification

- LockService serializes requests **only through this Apps Script**; external writers bypass the guarantee. Prevent or migrate such writes.
- The pre-existing interface displays 20% compound interest per turn, but existing game code did not accrue it. This change does not introduce new loan interest rules.
- User passwords remain in the original Users sheet layout; password security merits a separate migration.
- Before deployment run all unit tests, then verify borrow, repay, game win/loss, duplicate settlement, two-tab concurrent spends, signup and referral on isolated test accounts. Reconcile the Transactions ledger with Users C/D/G and retain a backup.
