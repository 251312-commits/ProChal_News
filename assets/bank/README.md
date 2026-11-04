# Bank UI PNG assets

The bank screen in `views/bank.py` uses the **existing** `assets/bet_background.jpg`; there is no dedicated bank background file.

Upload these seven transparent PNG files into this folder (`assets/bank/`):

| Filename | Artwork | Used on |
| --- | --- | --- |
| `bank_envelope_closed.png` | Closed pink envelope with seal | Landing and transition |
| `bank_envelope_open.png` | Open pink envelope with purple lining | Transition |
| `bank_cushion.png` | Purple velvet cushion | Landing |
| `bank_paper.png` | Decorative stacked pink paper | Loan and repayment |
| `bank_wax_seal.png` | Red wax crown seal | Loan and repayment |
| `bank_temple.png` | Royal BANK facade | All bank views |
| `bank_stamp.png` | Purple-gold rubber stamp | Loan and repayment |

The art is deliberately separate from editable Korean labels, numerical values, controls and transaction logic. Rounded action buttons use CSS (no button PNG).

The supplied artwork is available as `bank_ui_assets.zip` in the ChatGPT conversation. Extract it at the repository root: the archive already contains `assets/bank/*.png`.

Behavior: `show_bank()` shows the envelope landing page; `show_bank_loan()` and `show_bank_repay()` draw separate document screens. A short one-shot CSS crossfade from closed envelope to open envelope to paper runs on entry only (not on each slider rerun). All existing Google Sheets C/D writes remain in `views/bank.py`.

The layout has a graceful fallback if image assets are not yet present, but the illustrated design requires the seven files.
