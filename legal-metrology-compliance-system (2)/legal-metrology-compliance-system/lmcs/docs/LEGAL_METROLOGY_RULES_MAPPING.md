# Legal Metrology Rules → Detection Logic Mapping

This document explains, declaration by declaration, how the automated system
interprets Rule 6 of the Legal Metrology (Packaged Commodities) Rules, 2011,
and — critically — where that interpretation is a heuristic rather than a
legal determination.

> **This mapping must be reviewed by a Legal Metrology / legal compliance
> officer against the current, Gazette-notified consolidated text of the
> Rules before the system is used for any enforcement decision.** The
> Rules have been amended multiple times since 2011 (e.g. 2013, 2015, 2017,
> proposed 2022 amendments, and periodic FAQ clarifications from the
> Department of Consumer Affairs as recently as September/November 2025);
> this reference implementation was built from publicly available summaries
> as of August 2026 and may not reflect the very latest notification.
> Source: https://consumeraffairs.gov.in/pages/legal-metrology-act

The live, editable version of this table is
`backend/app/rules/declarations_rules.json` — update it there, not just in
this document, since that file is what the software actually runs.

## Mandatory declarations (Rule 6(1))

| Declaration | Rule ref. | Mandatory for | Detection approach | Key limitation |
|---|---|---|---|---|
| Name & address of manufacturer/packer/importer | 6(1)(a) | All packages | Keyword match (`manufactured by`, `packed by`, `marketed by`, `imported by`) + heuristic address check (looks for a 6-digit PIN code nearby) | OCR errors on this text (e.g. "Manulactured" instead of "Manufactured") will cause false "missing" flags — always visually check before relying on a missing-declaration result. |
| Country of origin | 6(1)(a), imported goods | Imported products only | Keyword match (`country of origin`, `made in`, `product of`) | Only evaluated when the product record's `is_imported` flag is set — accurate flagging depends on the officer correctly tagging the product at scan time. |
| Common/generic name of commodity | 6(1)(b) | All packages | **Always flagged for manual confirmation** — no reliable automated pattern exists to distinguish a product's generic name from brand text | Deliberately conservative: the system does not claim to auto-verify this declaration; it surfaces it for the officer to confirm by eye. |
| Net quantity (standard units) | 6(1)(c), Rules 8–11 | All packages | Regex for a number followed by a standard unit (g, kg, ml, l, mg, pieces, etc.) | Does not verify the *accuracy* of the declared quantity against the actual product weight — that requires physical weighing, outside this system's scope. |
| Month & year of manufacture/packing/import | 6(1)(e) | All packages | Regex for MM/YYYY, month-name + year, or `mfd`/`mfg`/`packed on` + year patterns | Handwritten or embossed (not printed) dates are unreliable for OCR; heavily stylized date stamps may not match the regex. |
| Maximum Retail Price (MRP) | 6(1)(f), Rule 18 | All packages | Regex for ₹/Rs. + a numeric amount, or an explicit "MRP"/"M.R.P." label | Per Dept. FAQs (Sept/Nov 2025), both "₹" and "Rs." are accepted — both are matched. Does not verify the "inclusive of all taxes" wording is present as a separate, distinct check beyond the price match itself. |
| Unit sale price | 6(1)(f)/6(11) | Conditional — not required when MRP equals unit sale price, and not required on e-commerce listings | Regex for "unit sale price" / "price per kg/litre/etc." | Treated as `minor` severity by default because the exemption is common and the system cannot determine unit-price-equals-MRP automatically. |
| Consumer care details | 6(1)(g) | All packages | Keyword match (`customer care`, `consumer care`, `helpline`, etc.) OR regex for a 10-digit phone number / email address | A generic customer-service line without a physical address may still pass this check even though the Rule technically expects name/address too — a known gap. |
| E-commerce listing declarations | 6(10) | `listing_type = ecommerce_listing` only | Composite check: requires manufacturer, generic name, net quantity, MRP, and consumer care to all be individually present | Month/year of manufacture is intentionally **not** required for this composite, per the Rule's exemption for digital listings. |

## Prohibited practices (heuristic, advisory)

| Practice | Rule ref. | How it's detected | Note |
|---|---|---|---|
| Sticker over date/MRP | 6(2) | **Not automatically detectable from a single photo** — requires comparing an original print layer against an affixed sticker, which needs either multiple photos or manual inspection | Not implemented as an automated check; flagged here as a known gap for the officer's physical inspection. |
| Multiple/conflicting MRP | Rule 18 | Regex counts how many ₹/Rs.-prefixed numeric values appear on the label | Frequently a false positive on legitimate "was/now" reduced-price stickers — scored as `minor`/advisory, explicitly worded to ask for officer verification rather than asserting a violation. |

## Font size / readability (Rule 6 read with labelling practice)

The specific character-height table used
(`backend/app/rules/font_size_rules.json`) is derived from commonly cited
area-based minimum character-height practice (rooted in the erstwhile
Standards of Weights & Measures (Packaged Commodities) Rules, 1977, Rule 8,
carried forward in departmental practice) — **not copied verbatim from a
single current Gazette citation**, and is flagged in the file's own
`_meta.disclaimer` field for that reason. It is intentionally editable
configuration so an officer can correct the exact thresholds.

Font height is measured in millimetres from the OCR bounding box, converted
from pixels using either:
- a **calibrated** scale (`calibration_mm_per_px`, if supplied — e.g. derived
  from a reference card of known size placed in the photo), or
- a **fallback assumed DPI** (300 DPI), in which case every measurement is
  explicitly labeled `"estimated"` in the API response and PDF/DOCX report,
  never presented as an exact, calibrated figure.

## Why this design

The goal is to make the system **useful for triage and standardization**
(consistent first-pass screening, structured reports, searchable history)
**without overstating its authority**. Every report — PDF, DOCX, and the
in-app view — carries a disclaimer that automated findings must be verified
by the inspecting officer, and the review/finalize workflow exists precisely
so a human signs off before any finding is treated as final.
