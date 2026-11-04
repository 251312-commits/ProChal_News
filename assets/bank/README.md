# Bank scene illustrations

These seven transparent AVIF assets are responsive derivatives of the seven bank illustrations supplied for the mobile UI. They are cropped and compressed for fast page loads.

| Asset | Screen |
| --- | --- |
| `bank_temple.avif` | Bank lobby and opening animation |
| `bank_crest.svg` | Printed emblem on the envelope |
| `bank_cushion.avif` | Home screen, purple cushion |
| `bank_envelope_closed.avif` | Home screen and opening animation |
| `bank_envelope_open.avif` | Opening animation |
| `bank_paper.avif` | Loan/repayment document and animation |
| `bank_wax_seal.avif` | Document header |
| `bank_stamp.avif` | Spare stamp illustration |

`views/bank_scene.py` loads these images as data URLs through the existing image helper. The previous PNG fallback remains available. The loan and repayment rules, state and Google Sheets persistence are unchanged.
