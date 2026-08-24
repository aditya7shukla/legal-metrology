"""
Rule engine: evaluates OCR-extracted text (and font measurements) against the
Legal Metrology (Packaged Commodities) Rules, 2011 declaration set defined in
app/rules/declarations_rules.json and app/rules/font_size_rules.json.

Design principle: the LEGAL knowledge lives in editable JSON config, not in
code, so a compliance/legal officer can update thresholds or wording without
a software release. This module is the generic evaluator over that config.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

RULES_DIR = Path(__file__).resolve().parent.parent / "rules"

with open(RULES_DIR / "declarations_rules.json", encoding="utf-8") as f:
    DECLARATION_RULES = json.load(f)

with open(RULES_DIR / "font_size_rules.json", encoding="utf-8") as f:
    FONT_RULES = json.load(f)

SEVERITY_WEIGHTS = {"critical": 30, "major": 15, "minor": 5}


def _normalized_compact(value: str) -> str:
    """OCR-insensitive form for abbreviations split by punctuation or spaces."""
    return re.sub(r"[^a-z0-9]+", "", (value or "").lower())


def _extract_structured_values(text: str) -> dict[str, str]:
    """Extract validated values even when a value sits beside/below its heading."""
    values: dict[str, str] = {}
    normalized = re.sub(r"\s+", " ", text or "")
    money = r"(?:₹|rs\.?|inr)\s*\d+(?:\.\d{1,2})?"

    mrp = re.search(rf"(?:m\s*\.?\s*r\s*\.?\s*p|maximum\s+retail\s+price).{{0,100}}?({money})", normalized, re.I)
    if mrp:
        values["MRP"] = mrp.group(0)
    usp = re.search(rf"\bu\s*\.?\s*s\s*\.?\s*p\b.{{0,120}}?({money})", normalized, re.I)
    if usp:
        values["UNIT_SALE_PRICE"] = usp.group(0)
    quantity = re.search(r"(?:net\s*(?:quantity|qty)\s*[:=-]?\s*).{0,80}?(\d+(?:\.\d+)?\s*(?:kg|g|gm|mg|ml|l|litre|liter|n|units?|pieces?|pcs))\b", normalized, re.I)
    if quantity:
        values["NET_QUANTITY"] = quantity.group(1)
    date = re.search(r"(?:mfd|mfg|manufactured|packed\s+on|date\s+of\s+(?:manufacture|packing))[^\n]{0,100}?((?:0?[1-9]|[12]\d|3[01])[/-](?:0?[1-9]|1[0-2])[/-](?:\d{2}|19\d{2}|20\d{2})|(?:0[1-9]|1[0-2])[/-](?:19|20)\d{2}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*(?:19|20)\d{2})", normalized, re.I)
    if date:
        values["MFG_DATE"] = date.group(1)
    email = re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", normalized, re.I)
    phone = re.search(r"\b(?:\+91[-\s]?)?[6-9]\d(?:[-\s]?\d){8}\b|\b0?\d{2,4}[-\s]?\d{6,8}\b", normalized)
    if email or phone:
        values["CONSUMER_CARE"] = (email or phone).group(0)
    return values


def _line_evidence(snippet: Optional[str], ocr_lines: list[dict] | None) -> list[dict]:
    if not snippet or not ocr_lines:
        return []
    terms = set(re.findall(r"[a-z0-9]{2,}", snippet.lower()))
    matches = []
    for line in ocr_lines:
        line_terms = set(re.findall(r"[a-z0-9]{2,}", (line.get("text") or "").lower()))
        if terms and len(terms & line_terms) / len(terms) >= 0.35:
            matches.append({key: line.get(key) for key in ("image_index", "text", "x", "y", "width", "height", "confidence")})
    return matches[:3]


def _text_matches_detection(
    full_text: str,
    detection: dict,
) -> tuple[bool, Optional[str]]:
    """
    OCR-tolerant declaration detection.

    Handles common OCR variations such as:
    - MRP -> MRP / M.R.P / M R P
    - Unit Sale Price -> Unit Sate Price / USP
    - MFG/MFD/PKD labels
    - dates in DD/MM/YY and DD/MM/YYYY formats
    - OCR punctuation and spacing errors
    """

    text = full_text or ""

    # ---------------------------------------------------------
    # OCR NORMALIZATION
    # ---------------------------------------------------------

    text_lower = text.lower()

    # Normalize common OCR punctuation/spacing
    normalized = re.sub(r"[\u2010-\u2015]", "-", text_lower)
    normalized = re.sub(r"\s+", " ", normalized)

    # Common OCR character substitutions.
    # Keep these conservative to avoid creating false positives.
    normalized = normalized.replace("m.r.p", "mrp")
    normalized = normalized.replace("m r p", "mrp")
    normalized = normalized.replace("u.s.p", "usp")
    normalized = normalized.replace("u s p", "usp")

    # ---------------------------------------------------------
    # KEYWORD DETECTION
    # ---------------------------------------------------------

    if detection["type"] == "keyword":

        for kw in detection.get("keywords", []):

            kw_normalized = re.sub(
                r"\s+",
                " ",
                kw.lower(),
            ).strip()

            if kw_normalized in normalized or _normalized_compact(kw_normalized) in _normalized_compact(normalized):
                idx = normalized.find(kw_normalized)
                if idx < 0:
                    idx = 0

                return (
                    True,
                    normalized[
                        max(0, idx - 30):
                        idx + len(kw_normalized) + 80
                    ].strip(),
                )

        return False, None

    # ---------------------------------------------------------
    # REGEX DETECTION
    # ---------------------------------------------------------

    if detection["type"] == "regex":

        for pattern in detection.get("patterns", []):

            try:
                m = re.search(
                    pattern,
                    text,
                    flags=re.IGNORECASE,
                )

                if m:
                    return True, m.group(0)

                # Also try normalized OCR text
                m = re.search(
                    pattern,
                    normalized,
                    flags=re.IGNORECASE,
                )

                if m:
                    return True, m.group(0)

            except re.error:
                continue

        return False, None

    # ---------------------------------------------------------
    # KEYWORD + REGEX
    # ---------------------------------------------------------

    if detection["type"] == "keyword_and_regex":

        keyword_hit = any(
            re.sub(r"\s+", " ", kw.lower()).strip()
            in normalized
            for kw in detection.get("keywords", [])
        )

        for pattern in detection.get("patterns", []):

            try:
                m = re.search(
                    pattern,
                    text,
                    flags=re.IGNORECASE,
                )

                if m:
                    return True, m.group(0)

                m = re.search(
                    pattern,
                    normalized,
                    flags=re.IGNORECASE,
                )

                if m:
                    return True, m.group(0)

            except re.error:
                continue

        if keyword_hit:
            return True, "keyword detected; structured contact detail not confidently detected"

        return False, None

    # ---------------------------------------------------------
    # KEYWORD + ADDRESS
    # ---------------------------------------------------------

    if detection["type"] == "keyword_and_address_pattern":

        kw_hit = None

        for kw in detection.get("keywords", []):

            if kw.lower() in normalized:
                kw_hit = kw
                break

        if not kw_hit:
            return False, None

        # Look for Indian PIN-code-like address evidence.
        pin_match = re.search(
            r"\b\d{6}\b",
            text,
        )

        if pin_match:
            return (
                True,
                f"{kw_hit} ... PIN {pin_match.group(0)}",
            )

        # OCR can damage the PIN, so a strong address keyword
        # combination is also accepted.
        address_terms = [
            "plot",
            "phase",
            "sector",
            "road",
            "street",
            "district",
            "tehsil",
            "haryana",
            "delhi",
            "uttar pradesh",
            "rajasthan",
            "maharashtra",
            "gujarat",
            "karnataka",
        ]

        address_hits = sum(
            1
            for term in address_terms
            if term in normalized
        )

        if address_hits >= 2:
            return (
                True,
                f"{kw_hit} ... address indicators detected",
            )

        return False, None

    # ---------------------------------------------------------
    # PRESENCE HEURISTIC
    # ---------------------------------------------------------

    if detection["type"] == "presence_heuristic":

        return True, "requires_manual_confirmation"

    return False, None

def _panel_font_requirement(panel_area_cm2: Optional[float]) -> float:
    table = FONT_RULES["net_quantity_font_table"]
    if panel_area_cm2 is None:
        return FONT_RULES["declaration_min_height_mm"]["default"]
    for row in table:
        if row["max_area_cm2"] is None or panel_area_cm2 <= row["max_area_cm2"]:
            return row["min_height_mm"]
    return table[-1]["min_height_mm"]


def evaluate_compliance(
    full_text: str,
    is_imported: bool,
    listing_type: str,
    font_measurements: list[dict],
    panel_area_cm2: Optional[float] = None,
    ocr_lines: list[dict] | None = None,
) -> dict:
    """
    Main entry point. Returns a structured compliance result:
    {
      "score": float 0-100,
      "status": "compliant" | "minor_issues" | "non_compliant",
      "declarations_found": [...],
      "violations": [ {declaration_code, title, rule_ref, violation_type, severity, description, detected_value, expected} ]
    }
    """
    violations = []
    found_declarations = []
    max_possible_score = 0
    structured_values = _extract_structured_values(full_text)

    min_font_required = _panel_font_requirement(panel_area_cm2)

    # Font-size measurements from an ordinary photograph are only estimates
    # unless a physical calibration reference was supplied.
    #
    # Only calibrated measurements are strong enough to create an automated
    # legal-compliance violation.
    smallest_relevant_height = None
    smallest_relevant_measurement = None

    for m in font_measurements:
        if not re.search(r"\d", m["text"]):
            continue

        if m.get("measurement_confidence") != "calibrated":
            continue

        h = m["estimated_height_mm"]

        if (
            smallest_relevant_height is None
            or h < smallest_relevant_height
        ):
            smallest_relevant_height = h
            smallest_relevant_measurement = m

    for decl in DECLARATION_RULES["declarations"]:
        applies = decl["applies_to"]

        if applies == "imported" and not is_imported:
            continue
        if applies == "ecommerce_listing" and listing_type != "ecommerce_listing":
            continue
        if applies == "conditional" and decl["code"] == "UNIT_SALE_PRICE":
            # The MRP-equals-USP exemption cannot be inferred reliably from a
            # photograph. A visible USP heading is useful evidence, but an
            # unreadable value must be reviewed by an officer, not converted
            # into an automatic missing-declaration finding.
            found, snippet = _text_matches_detection(full_text, decl["detection"])
            if not found:
                usp_heading = re.search(r"\bu\s*s\s*p\b", full_text, flags=re.IGNORECASE)
                if usp_heading:
                    found = True
                    snippet = usp_heading.group(0)
            if found:
                snippet = structured_values.get("UNIT_SALE_PRICE", snippet)
                found_declarations.append({"code": decl["code"], "title": decl["title"], "matched": snippet, "evidence": _line_evidence(snippet, ocr_lines)})
            continue

        max_possible_score += SEVERITY_WEIGHTS.get(decl["severity"], 10)

        if decl["detection"]["type"] == "composite":
            required = decl["detection"]["requires_codes"]
            missing = [c for c in required if c not in [f["code"] for f in found_declarations]]
            if missing:
                violations.append(
                    {
                        "declaration_code": decl["code"],
                        "declaration_title": decl["title"],
                        "rule_reference": decl["rule_ref"],
                        "violation_type": "missing",
                        "severity": decl["severity"],
                        "description": f"E-commerce listing is missing linked declarations: {', '.join(missing)}.",
                        "detected_value": None,
                        "expected_requirement": decl["notes"],
                    }
                )
            continue

        found, snippet = _text_matches_detection(full_text, decl["detection"])
        # These declarations are only valid when both their heading/context and
        # structured value survive OCR. A random number (e.g. phone status-bar
        # "5G") or blank template heading must never satisfy them.
        strict_value_codes = {"MRP", "NET_QUANTITY", "MFG_DATE"}
        if decl["code"] in structured_values:
            found, snippet = True, structured_values[decl["code"]]
        elif decl["code"] in strict_value_codes:
            found, snippet = False, None

        if not found:
            severity = decl["severity"]
            if not decl["mandatory"]:
                severity = "minor"
            violations.append(
                {
                    "declaration_code": decl["code"],
                    "declaration_title": decl["title"],
                    "rule_reference": decl["rule_ref"],
                    "violation_type": "missing",
                    "severity": severity,
                    "description": f"'{decl['title']}' was not detected on the label/listing.",
                    "detected_value": None,
                    "expected_requirement": decl["notes"],
                }
            )
        else:
            found_declarations.append({"code": decl["code"], "title": decl["title"], "matched": snippet, "evidence": _line_evidence(snippet, ocr_lines)})

        # --- Font size / readability checks ---
        #
        # IMPORTANT:
        # A normal photograph does not provide reliable real-world scale.
        # Therefore an uncalibrated pixel->mm estimate must NOT be treated
        # as a legal violation.
        #
        # Only calibrated measurements can automatically trigger this rule.

        if (
            listing_type == "physical_package"
            and smallest_relevant_height is not None
        ):
            if smallest_relevant_height < min_font_required:
                violations.append(
                    {
                        "declaration_code": "FONT_SIZE",
                        "declaration_title": "Minimum character height for numeric declarations",
                        "rule_reference": (
                            "Rule 6 read with labelling font-size practice "
                            "(see font_size_rules.json)"
                        ),
                        "violation_type": "font_too_small",
                        "severity": "major",
                        "description": (
                            f"Calibrated measurement indicates that the smallest "
                            f"detected numeric text is approximately "
                            f"{smallest_relevant_height} mm tall, below the "
                            f"{min_font_required} mm minimum."
                        ),
                        "detected_value": (
                            f"{smallest_relevant_height} mm (calibrated)"
                        ),
                        "expected_requirement": (
                            f">= {min_font_required} mm"
                        ),
                    }
                )

                max_possible_score += SEVERITY_WEIGHTS["major"]

    # --- Prohibited practice heuristics ---
    mrp_matches = re.findall(r"(₹|rs\.?)\s?\d+(\.\d{1,2})?", full_text, flags=re.IGNORECASE)
    distinct_mrp_values = set(m[1] if m[1] else "" for m in mrp_matches)  # weak heuristic, flagged as advisory
    if len(mrp_matches) >= 2:
        violations.append(
            {
                "declaration_code": "MULTIPLE_MRP",
                "declaration_title": "Possible multiple/conflicting MRP values",
                "rule_reference": "Rule 18",
                "violation_type": "prohibited_practice",
                "severity": "minor",
                "description": (
                    "More than one price-like value was detected on the label. This is often a legitimate "
                    "'was/now' reduced-MRP sticker, but should be manually verified by the inspecting officer."
                ),
                "detected_value": "; ".join(m[0] for m in mrp_matches),
                "expected_requirement": "Single unambiguous MRP inclusive of all taxes.",
            }
        )

    if not violations:
        score = 100.0
    else:
        deducted = sum(SEVERITY_WEIGHTS.get(v["severity"], 10) for v in violations)
        denom = max(max_possible_score, 1)
        score = max(0.0, 100.0 - (deducted / denom) * 100.0)

    critical_count = sum(1 for v in violations if v["severity"] == "critical")
    if critical_count > 0:
        status = "non_compliant"
    elif violations:
        status = "minor_issues" if score >= 70 else "non_compliant"
    else:
        status = "compliant"

    return {
        "score": round(score, 1),
        "status": status,
        "declarations_found": found_declarations,
        "violations": violations,
        "font_requirement_mm": min_font_required,
        "structured_values": structured_values,
    }
