# Article load failure recovery

## Player behavior

- A selected article must yield a usable title and at least 40 non-whitespace characters of body text.
- If extraction fails, keep the confirmed bet, immediately exclude the URL for this Streamlit session, discard the article candidates and return to a fresh selection screen.
- Do not increment `News!B (Count)` for an article that failed to load.
- Game 5 replaces a failed candidate. A failure in AI summarization/scoring is not treated as an article extraction failure.
- Direct links are reported only when they already match an existing News pool entry; an unregistered bad link does not create a new article record.

## Shared counter

`News!J` = `FailureCount` (0–3), `News!K` = `FailureEventIds` (up to 3 IDs, JSON).
The Apps Script web app processes authenticated `kind: "article_failure"` requests under `LockService`. It identifies articles by canonical URL / URL hash, persists the count and active state in one Sheets batchUpdate, and ignores retries of the same event ID. Different users share the same counter. At count 3, `News!H (Active)` becomes `FALSE`; the article stays in the sheet for inspection, but is omitted from all games. Duplicate rows matching the URL are disabled together.

Transient network, timeout, HTTP 429 and 5xx errors only exclude that URL from the current session, without incrementing the global counter. If the Apps Script gateway cannot confirm a write, local recovery still happens but the global count is not guaranteed.

## Deployment

1. Merge the PR so Streamlit loads the new Python code.
2. Replace the deployed Apps Script project's `Code.gs` with this repository's `apps_script/Code.gs`, leaving `Badges.gs` unchanged.
3. Deploy a **new version** of the Apps Script Web App, executed as owner. Keep `SPREADSHEET_ID`, `TRANSACTION_TOKEN`, the Sheets advanced service, and the existing `transaction_endpoint` / `transaction_token` Streamlit secrets.
4. The first request (or Streamlit `init_news_sheet`) creates the News J:K headers. Do not repurpose those columns.
5. Check a test article's failure counter and Active value, and confirm another account can no longer select it after the third counted failure.

No existing rows are physically deleted. To restore an article intentionally, change `FailureCount` to 0, `FailureEventIds` to an empty array `[]`, and `Active` to `TRUE`.
