from __future__ import annotations
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.models import UserRole, ProductCategory, ScanStatus, ComplianceStatus, ViolationSeverity


# ---------- Auth / Users ----------

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str = Field(min_length=8)
    role: UserRole = UserRole.ENFORCEMENT_OFFICER
    designation: Optional[str] = None
    jurisdiction: Optional[str] = None


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    full_name: str
    email: EmailStr
    role: UserRole
    designation: Optional[str] = None
    jurisdiction: Optional[str] = None
    is_active: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ---------- Products ----------

class ProductCreate(BaseModel):
    name: str
    brand: Optional[str] = None
    category: ProductCategory = ProductCategory.OTHER
    manufacturer_name: Optional[str] = None
    is_imported: bool = False
    barcode: Optional[str] = None
    source_channel: Optional[str] = None


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    brand: Optional[str] = None
    category: ProductCategory
    manufacturer_name: Optional[str] = None
    is_imported: bool
    barcode: Optional[str] = None
    source_channel: Optional[str] = None
    created_at: datetime
    updated_at: datetime


# ---------- Scans ----------

class ScanCreateMeta(BaseModel):
    """Multipart form fields accompanying the uploaded image."""
    product_id: Optional[str] = None
    new_product: Optional[ProductCreate] = None
    listing_type: str = "physical_package"
    inspection_location_text: Optional[str] = None
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None


class ScanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    product_id: str
    scanned_by: str
    image_path: str
    thumbnail_path: Optional[str] = None
    status: ScanStatus
    listing_type: str
    raw_ocr_text: Optional[str] = None
    extracted_fields: Optional[Any] = None
    font_analysis: Optional[Any] = None
    inspection_location_text: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    report_id: Optional[str] = None
    report_id: Optional[str] = None


class ScanDiagnosticOut(BaseModel):
    """OCR evidence for an authorized officer reviewing a report."""
    model_config = ConfigDict(from_attributes=True)
    scan_id: str
    image_original_filename: Optional[str] = None
    raw_ocr_text: Optional[str] = None
    extracted_fields: Optional[Any] = None
    font_analysis: Optional[Any] = None


# ---------- Violations / Reports ----------

class ViolationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    declaration_code: str
    declaration_title: str
    rule_reference: Optional[str] = None
    violation_type: str
    severity: ViolationSeverity
    description: Optional[str] = None
    detected_value: Optional[str] = None
    expected_requirement: Optional[str] = None


class ComplianceReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    scan_id: str
    overall_status: ComplianceStatus
    compliance_score: float
    rule_version: str
    summary: Optional[str] = None
    pdf_path: Optional[str] = None
    docx_path: Optional[str] = None
    is_finalized: bool
    reviewer_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    violations: list[ViolationOut] = []


class ReportReviewUpdate(BaseModel):
    reviewer_notes: Optional[str] = None
    is_finalized: Optional[bool] = None
    override_status: Optional[ComplianceStatus] = None


# ---------- Dashboard ----------

class DashboardSummary(BaseModel):
    total_scans: int
    total_products: int
    compliant_count: int
    minor_issues_count: int
    non_compliant_count: int
    compliance_rate_pct: float
    top_violations: list[dict]
    scans_by_day: list[dict]
    scans_by_category: list[dict]


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[Any]
