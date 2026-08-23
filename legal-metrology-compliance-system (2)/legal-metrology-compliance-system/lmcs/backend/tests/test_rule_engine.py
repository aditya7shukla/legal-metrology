"""
Unit tests for the rule engine. Run with: pytest tests/ -v
These tests exercise the compliance evaluator directly (no DB/HTTP needed),
which is where the actual regulatory logic lives and where correctness matters most.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.rule_engine import evaluate_compliance


def test_fully_compliant_label():
    text = """
    SunGold Refined Sunflower Oil
    Net Quantity: 1 L
    MRP Rs. 185.00 (Inclusive of all taxes)
    Mfd: 03/2026
    Manufactured by SunGold Foods Pvt Ltd, Plot 12, MIDC, Pune 411019
    Consumer Care: 1800-123-4567, care@sungold.example.com
    """
    result = evaluate_compliance(
        full_text=text, is_imported=False, listing_type="physical_package",
        font_measurements=[{"text": "MRP Rs. 185.00", "estimated_height_mm": 3.0}],
    )
    critical = [v for v in result["violations"] if v["severity"] == "critical"]
    assert not critical, f"Expected no critical violations, got: {critical}"
    assert result["score"] > 60


def test_missing_mrp_and_mfg_date_flagged():
    text = "SunGold Refined Sunflower Oil Net Quantity: 1 L Manufactured by SunGold Foods Pvt Ltd, Pune 411019"
    result = evaluate_compliance(
        full_text=text, is_imported=False, listing_type="physical_package", font_measurements=[],
    )
    codes = [v["declaration_code"] for v in result["violations"]]
    assert "MRP" in codes
    assert "MFG_DATE" in codes
    assert result["status"] == "non_compliant"


def test_imported_product_requires_country_of_origin():
    text = "Wireless Earbuds Net Quantity: 1 Unit MRP Rs. 2999.00 Mfd: 01/2026 Manufactured by AudioMax, China"
    result = evaluate_compliance(
        full_text=text, is_imported=True, listing_type="physical_package", font_measurements=[],
    )
    codes = [v["declaration_code"] for v in result["violations"]]
    assert "COUNTRY_OF_ORIGIN" in codes


def test_font_too_small_flagged():
    text = "Net Quantity: 500 g MRP Rs. 99.00 Mfd: 01/2026 Manufactured by ABC Pvt Ltd, Delhi 110001"
    result = evaluate_compliance(
        full_text=text, is_imported=False, listing_type="physical_package",
        font_measurements=[{"text": "MRP Rs. 99.00", "estimated_height_mm": 0.5}],
        panel_area_cm2=50,
    )
    codes = [v["declaration_code"] for v in result["violations"]]
    assert "FONT_SIZE" in codes


def test_ecommerce_listing_does_not_require_mfg_month_physically_but_checks_composite():
    text = "SunGold Oil Net Quantity: 1 L MRP Rs. 185.00 Manufactured by SunGold Foods, Pune 411019 Consumer Care: 1800-123-4567"
    result = evaluate_compliance(
        full_text=text, is_imported=False, listing_type="ecommerce_listing", font_measurements=[],
    )
    # Should not demand MFG_DATE as hard as physical (still flagged individually,
    # but ECOMMERCE_DECLARATIONS composite should pass since core fields present)
    ecom = [v for v in result["violations"] if v["declaration_code"] == "ECOMMERCE_DECLARATIONS"]
    assert not ecom
