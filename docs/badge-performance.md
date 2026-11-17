# Badge archive performance improvements

The badge popup previously made two sequential Apps Script requests for every
first-time open (`status` then `badge_sync`) and every equip/unequip
(`status` then `equip`). It also repeated reconciliation on every reopen
and rebuilt 25 embedded SVG image backgrounds whenever a badge was selected.

## New behavior

- **Opening the archive, first visit:** one authenticated `badge_sync` request
  updates the wallet and badge profile directly from the authoritative Apps
  Script server. The server still holds ScriptLock and checks existing ledger
  rows; no earned badge is calculated from a client-side counter.
- **Reopening / selecting:** the confirmed profile stays in Streamlit session
  state for 90 seconds, per authenticated player. No gateway call is needed for
  ordinary selection or a quick reopen. Cross-tab changes can be fetched via
  the small ↻ button at the top right of the popup.
- **Equipping / unequipping:** one `equip` request. The server checks ownership
  against Users!K under the same transaction lock before updating Users!J.
  The confirmed response updates session state and the short-lived cache.
  The existing transaction ID is retained for timeout retries.
- **Old gateway:** unsupported `badge_sync` or `equip` operations respond with
  `INVALID_REQUEST` before any mutation. The client provides a clear upgrade
  message. An old server can still return read-only badge status when the
  gallery opens, without losing earned items.
- **Network errors:** for a temporary sync failure the popup displays its
  last known data but disables equip and automatically retries after 20 s;
  the ↻ button retries immediately.
- **SVG rendering:** artwork backgrounds are injected once into the main page
  only when opening the collection. Dialog fragment reruns transmit only small
  ownership/selection CSS, not the 25 base64-embedded illustrations. Cached
  Python CSS generation also avoids redundant work.

## Scope and limitations

No change is required to `apps_script/Code.gs`, `Badges.gs`, the Google
spreadsheet, badge IDs, wallet rules, or earned records. This change requires
only the Streamlit app to be redeployed.

The **first** badge sync still requires a full authoritative ledger scan on
the Apps Script side. Its wall-clock latency will depend on the current size
of Transactions and Google Sheets performance. This PR removes redundant
round trips but does not claim to make a full historical scan constant-time.
A scalable follow-up would maintain server-side incremental progress with
an atomic checkpoint instead of recomputing all historical events.

## Verification

Run `python -m unittest discover -s tests -v` and
`node --test tests/test_transaction_gateway.cjs`.
In the browser, check initial archive open, repeated opens within 90 s,
↻ refresh, new badge unlock, equip/unequip (including locked rejection),
phone scroll/square area, other-tab changes and old-server compatibility.
