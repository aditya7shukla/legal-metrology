import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ComplianceReport, User, UserRole, AuditLog
from app.schemas import ComplianceReportOut, ReportReviewUpdate, PaginatedResponse  # noqa: F401
from app.security import get_current_user, require_roles

router = APIRouter(prefix="/reports", tags=["Compliance Reports"])


@router.get("", response_model=PaginatedResponse)
def list_reports(
    overall_status: str | None = None,
    is_finalized: bool | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ComplianceReport)
    if overall_status:
        query = query.filter(ComplianceReport.overall_status == overall_status)
    if is_finalized is not None:
        query = query.filter(ComplianceReport.is_finalized == is_finalized)
    total = query.count()
    items = (
        query.order_by(ComplianceReport.created_at.desc())
        .offset((page - 1) * page_size).limit(page_size).all()
    )
    return PaginatedResponse(
        total=total, page=page, page_size=page_size,
        items=[ComplianceReportOut.model_validate(r) for r in items],
    )


@router.get("/{report_id}", response_model=ComplianceReportOut)
def get_report(report_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    report = db.query(ComplianceReport).filter(ComplianceReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")
    return report


@router.patch("/{report_id}/review", response_model=ComplianceReportOut)
def review_report(
    report_id: str,
    payload: ReportReviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ENFORCEMENT_OFFICER)),
):
    """Officer review workflow: add notes, override the automated status, and/or finalize the report."""
    report = db.query(ComplianceReport).filter(ComplianceReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found.")

    if payload.reviewer_notes is not None:
        report.reviewer_notes = payload.reviewer_notes
    if payload.override_status is not None:
        report.overall_status = payload.override_status
    if payload.is_finalized is not None:
        report.is_finalized = payload.is_finalized
        report.reviewed_by = current_user.id

    db.commit()
    db.refresh(report)

    db.add(AuditLog(
        user_id=current_user.id, action="REPORT_REVIEWED", entity_type="compliance_report",
        entity_id=report.id, details=payload.model_dump(exclude_none=True),
    ))
    db.commit()
    return report


@router.get("/{report_id}/download/pdf")
def download_pdf(report_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    report = db.query(ComplianceReport).filter(ComplianceReport.id == report_id).first()
    if not report or not report.pdf_path or not os.path.exists(report.pdf_path):
        raise HTTPException(status_code=404, detail="PDF report not available.")
    return FileResponse(report.pdf_path, media_type="application/pdf", filename=f"compliance_report_{report_id}.pdf")


@router.get("/{report_id}/download/docx")
def download_docx(report_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    report = db.query(ComplianceReport).filter(ComplianceReport.id == report_id).first()
    if not report or not report.docx_path or not os.path.exists(report.docx_path):
        raise HTTPException(status_code=404, detail="DOCX report not available.")
    return FileResponse(
        report.docx_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"compliance_report_{report_id}.docx",
    )
