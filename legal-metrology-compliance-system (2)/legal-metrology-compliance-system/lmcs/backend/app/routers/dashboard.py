from collections import Counter
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ScanRecord, Product, ComplianceReport, ViolationDetail, ComplianceStatus, User
from app.schemas import DashboardSummary
from app.security import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/summary", response_model=DashboardSummary)
def dashboard_summary(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    since = datetime.utcnow() - timedelta(days=days)

    total_scans = db.query(ScanRecord).filter(ScanRecord.created_at >= since).count()
    total_products = db.query(Product).count()

    reports = db.query(ComplianceReport).filter(ComplianceReport.created_at >= since).all()
    compliant = sum(1 for r in reports if r.overall_status == ComplianceStatus.COMPLIANT)
    minor = sum(1 for r in reports if r.overall_status == ComplianceStatus.MINOR_ISSUES)
    non_compliant = sum(1 for r in reports if r.overall_status == ComplianceStatus.NON_COMPLIANT)
    total_reports = len(reports) or 1
    compliance_rate = round((compliant / total_reports) * 100, 1)

    violation_rows = (
        db.query(ViolationDetail.declaration_title, func.count(ViolationDetail.id))
        .join(ComplianceReport, ViolationDetail.report_id == ComplianceReport.id)
        .filter(ComplianceReport.created_at >= since)
        .group_by(ViolationDetail.declaration_title)
        .order_by(func.count(ViolationDetail.id).desc())
        .limit(10)
        .all()
    )
    top_violations = [{"declaration": title, "count": count} for title, count in violation_rows]

    scans = db.query(ScanRecord).filter(ScanRecord.created_at >= since).all()
    by_day = Counter(s.created_at.strftime("%Y-%m-%d") for s in scans)
    scans_by_day = [{"date": d, "count": c} for d, c in sorted(by_day.items())]

    products_by_cat = (
        db.query(Product.category, func.count(Product.id)).group_by(Product.category).all()
    )
    scans_by_category = [{"category": cat.value, "count": count} for cat, count in products_by_cat]

    return DashboardSummary(
        total_scans=total_scans,
        total_products=total_products,
        compliant_count=compliant,
        minor_issues_count=minor,
        non_compliant_count=non_compliant,
        compliance_rate_pct=compliance_rate,
        top_violations=top_violations,
        scans_by_day=scans_by_day,
        scans_by_category=scans_by_category,
    )
