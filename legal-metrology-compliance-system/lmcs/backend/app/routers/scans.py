import json
import traceback
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    ScanRecord, ScanStatus, Product, ComplianceReport, ViolationDetail,
    ComplianceStatus, ViolationSeverity, User, UserRole, AuditLog,
)
from app.schemas import ScanOut, ProductCreate, PaginatedResponse
from app.security import get_current_user, require_roles
from app.services.ocr_service import run_ocr, analyze_font_sizes
from app.services.rule_engine import evaluate_compliance
from app.services.report_generator import generate_pdf_report, generate_docx_report
from app.utils.file_storage import save_upload

router = APIRouter(prefix="/scans", tags=["Scanning & Compliance Checks"])


def _get_or_create_product(db: Session, product_id: Optional[str], new_product_json: Optional[str]) -> Product:
    if product_id:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="product_id not found in repository.")
        return product
    if new_product_json:
        data = ProductCreate(**json.loads(new_product_json))
        product = Product(**data.model_dump())
        db.add(product)
        db.commit()
        db.refresh(product)
        return product
    raise HTTPException(status_code=400, detail="Either product_id or new_product must be supplied.")


@router.post("", response_model=ScanOut, status_code=201)
def create_and_process_scan(
    image: UploadFile = File(...),
    product_id: Optional[str] = Form(None),
    new_product: Optional[str] = Form(None, description="JSON-encoded ProductCreate payload"),
    listing_type: str = Form("physical_package"),
    inspection_location_text: Optional[str] = Form(None),
    location_lat: Optional[float] = Form(None),
    location_lng: Optional[float] = Form(None),
    panel_area_cm2: Optional[float] = Form(None, description="Principal display panel area, if measured"),
    calibration_mm_per_px: Optional[float] = Form(None, description="mm-per-pixel if a calibration reference was used"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ENFORCEMENT_OFFICER)),
):
    """
    Upload a product/label image and synchronously run the full pipeline:
    OCR extraction -> font analysis -> rule-based compliance evaluation ->
    persisted ScanRecord + ComplianceReport (+ PDF/DOCX artifacts).

    NOTE ON SCALE: this endpoint runs synchronously for simplicity and to keep
    the reference implementation easy to deploy. For high-volume production
    workloads, swap the body of this function for a task enqueue (Celery/RQ/
    Cloud Tasks) that calls the same service functions from a worker process —
    see docs/ARCHITECTURE.md "Scaling the pipeline".
    """
    product = _get_or_create_product(db, product_id, new_product)
    image_path, thumb_path = save_upload(image)

    scan = ScanRecord(
        product_id=product.id,
        scanned_by=current_user.id,
        image_path=image_path,
        image_original_filename=image.filename,
        thumbnail_path=thumb_path,
        status=ScanStatus.PROCESSING,
        listing_type=listing_type,
        inspection_location_text=inspection_location_text,
        location_lat=location_lat,
        location_lng=location_lng,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    try:
        ocr_result = run_ocr(image_path)
        font_measurements = analyze_font_sizes(ocr_result, calibration_mm_per_px)

        compliance = evaluate_compliance(
            full_text=ocr_result.full_text,
            is_imported=product.is_imported,
            listing_type=listing_type,
            font_measurements=font_measurements,
            panel_area_cm2=panel_area_cm2,
        )

        scan.raw_ocr_text = ocr_result.full_text
        scan.extracted_fields = {"declarations_found": compliance["declarations_found"]}
        scan.font_analysis = {
            "measurements": font_measurements,
            "required_min_mm": compliance["font_requirement_mm"],
            "skew_angle_deg": ocr_result.skew_angle_deg,
        }
        scan.status = ScanStatus.COMPLETED
        scan.completed_at = datetime.utcnow()

        report = ComplianceReport(
            scan_id=scan.id,
            overall_status=ComplianceStatus(compliance["status"]),
            compliance_score=compliance["score"],
            summary=(
                f"{len(compliance['violations'])} finding(s) across "
                f"{sum(1 for v in compliance['violations'] if v['severity']=='critical')} critical, "
                f"{sum(1 for v in compliance['violations'] if v['severity']=='major')} major, "
                f"{sum(1 for v in compliance['violations'] if v['severity']=='minor')} minor."
            ),
        )
        db.add(report)
        db.flush()  # get report.id before creating child rows

        for v in compliance["violations"]:
            db.add(ViolationDetail(
                report_id=report.id,
                declaration_code=v["declaration_code"],
                declaration_title=v["declaration_title"],
                rule_reference=v.get("rule_reference"),
                violation_type=v["violation_type"],
                severity=ViolationSeverity(v["severity"]),
                description=v.get("description"),
                detected_value=v.get("detected_value"),
                expected_requirement=v.get("expected_requirement"),
            ))

        db.commit()
        db.refresh(scan)
        db.refresh(report)

        # Generate downloadable artifacts
        product_dict = {
            "name": product.name, "brand": product.brand, "category": product.category.value,
            "manufacturer_name": product.manufacturer_name, "is_imported": product.is_imported,
            "source_channel": product.source_channel,
        }
        scan_dict = {
            "listing_type": scan.listing_type,
            "inspection_location_text": scan.inspection_location_text,
            "created_at": scan.created_at.strftime("%Y-%m-%d %H:%M UTC"),
        }
        officer_dict = {"full_name": current_user.full_name}
        pdf_path = generate_pdf_report(report.id, product_dict, scan_dict, compliance, officer_dict, image_path)
        docx_path = generate_docx_report(report.id, product_dict, scan_dict, compliance, officer_dict)
        report.pdf_path = pdf_path
        report.docx_path = docx_path
        db.commit()

        db.add(AuditLog(
            user_id=current_user.id, action="SCAN_COMPLETED",
            entity_type="scan_record", entity_id=scan.id,
            details={"product_id": product.id, "status": compliance["status"], "score": compliance["score"]},
        ))
        db.commit()

    except Exception as exc:  # noqa: BLE001
        db.rollback()
        scan.status = ScanStatus.FAILED
        scan.error_message = f"{exc}\n{traceback.format_exc()[-1500:]}"
        db.add(scan)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Processing failed: {exc}") from exc

    db.refresh(scan)
    return scan


@router.get("", response_model=PaginatedResponse)
def list_scans(
    product_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ScanRecord)
    if product_id:
        query = query.filter(ScanRecord.product_id == product_id)
    if status:
        query = query.filter(ScanRecord.status == status)
    total = query.count()
    items = query.order_by(ScanRecord.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return PaginatedResponse(
        total=total, page=page, page_size=page_size,
        items=[ScanOut.model_validate(s) for s in items],
    )


@router.get("/{scan_id}", response_model=ScanOut)
def get_scan(scan_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    scan = db.query(ScanRecord).filter(ScanRecord.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found.")
    return scan
