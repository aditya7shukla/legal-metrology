import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, ForeignKey, Text, Enum, JSON
)
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class UserRole(str, enum.Enum):
    ADMIN = "admin"                      # Full system access, user management
    ENFORCEMENT_OFFICER = "officer"      # Can scan, inspect, generate reports
    VIEWER = "viewer"                    # Read-only access to dashboards/reports


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.ENFORCEMENT_OFFICER, nullable=False)
    designation = Column(String(150), nullable=True)     # e.g. "Legal Metrology Inspector, Delhi"
    jurisdiction = Column(String(150), nullable=True)    # e.g. "North District"
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    scans = relationship("ScanRecord", back_populates="scanned_by_user")


class ProductCategory(str, enum.Enum):
    FOOD = "food"
    COSMETICS = "cosmetics"
    ELECTRONICS = "electronics"
    HOUSEHOLD = "household"
    FMCG_OTHER = "fmcg_other"
    OTHER = "other"


class Product(Base):
    """A repository entry for a distinct product/SKU that has been scanned one or more times."""
    __tablename__ = "products"

    id = Column(String, primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False, index=True)
    brand = Column(String(255), nullable=True, index=True)
    category = Column(Enum(ProductCategory), default=ProductCategory.OTHER)
    manufacturer_name = Column(String(255), nullable=True)
    is_imported = Column(Boolean, default=False)
    barcode = Column(String(64), nullable=True, index=True)
    source_channel = Column(String(100), nullable=True)  # e.g. "Retail Store", "Amazon.in", "Flipkart"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    scans = relationship("ScanRecord", back_populates="product", cascade="all, delete-orphan")


class ScanStatus(str, enum.Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ScanRecord(Base):
    """One scan/inspection event: an uploaded image + the extracted/validated data."""
    __tablename__ = "scan_records"

    id = Column(String, primary_key=True, default=gen_uuid)
    product_id = Column(String, ForeignKey("products.id"), nullable=False)
    scanned_by = Column(String, ForeignKey("users.id"), nullable=False)

    image_path = Column(String(500), nullable=False)
    image_original_filename = Column(String(255), nullable=True)
    thumbnail_path = Column(String(500), nullable=True)

    status = Column(Enum(ScanStatus), default=ScanStatus.QUEUED)
    listing_type = Column(String(50), default="physical_package")  # physical_package | ecommerce_listing

    raw_ocr_text = Column(Text, nullable=True)
    extracted_fields = Column(JSON, nullable=True)     # structured extraction result
    font_analysis = Column(JSON, nullable=True)        # per-declaration font/readability measurements
    location_lat = Column(Float, nullable=True)
    location_lng = Column(Float, nullable=True)
    inspection_location_text = Column(String(255), nullable=True)

    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    product = relationship("Product", back_populates="scans")
    scanned_by_user = relationship("User", back_populates="scans")
    compliance_report = relationship(
        "ComplianceReport", back_populates="scan", uselist=False, cascade="all, delete-orphan"
    )
    images = relationship("ScanImage", back_populates="scan", cascade="all, delete-orphan")

    @property
    def report_id(self) -> str | None:
        return self.compliance_report.id if self.compliance_report else None

    @property
    def report_id(self) -> str | None:
        """Convenience accessor so API responses can link straight to the generated report."""
        return self.compliance_report.id if self.compliance_report else None


class ScanImage(Base):
    """Original plus optional close-up images captured for one inspection."""
    __tablename__ = "scan_images"

    id = Column(String, primary_key=True, default=gen_uuid)
    scan_id = Column(String, ForeignKey("scan_records.id"), nullable=False, index=True)
    image_path = Column(String(500), nullable=False)
    original_filename = Column(String(255), nullable=True)
    is_primary = Column(Boolean, default=False, nullable=False)
    quality_assessment = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    scan = relationship("ScanRecord", back_populates="images")


class ComplianceStatus(str, enum.Enum):
    COMPLIANT = "compliant"
    MINOR_ISSUES = "minor_issues"
    NON_COMPLIANT = "non_compliant"


class ComplianceReport(Base):
    __tablename__ = "compliance_reports"

    id = Column(String, primary_key=True, default=gen_uuid)
    scan_id = Column(String, ForeignKey("scan_records.id"), unique=True, nullable=False)

    overall_status = Column(Enum(ComplianceStatus), default=ComplianceStatus.NON_COMPLIANT)
    compliance_score = Column(Float, default=0.0)  # 0-100
    rule_version = Column(String(20), default="1.0.0")

    summary = Column(Text, nullable=True)
    pdf_path = Column(String(500), nullable=True)
    docx_path = Column(String(500), nullable=True)

    reviewed_by = Column(String, ForeignKey("users.id"), nullable=True)
    reviewer_notes = Column(Text, nullable=True)
    is_finalized = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    scan = relationship("ScanRecord", back_populates="compliance_report")
    violations = relationship("ViolationDetail", back_populates="report", cascade="all, delete-orphan")


class ViolationSeverity(str, enum.Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"


class ViolationDetail(Base):
    __tablename__ = "violation_details"

    id = Column(String, primary_key=True, default=gen_uuid)
    report_id = Column(String, ForeignKey("compliance_reports.id"), nullable=False)

    declaration_code = Column(String(64), nullable=False)   # e.g. NET_QUANTITY, MRP
    declaration_title = Column(String(255), nullable=False)
    rule_reference = Column(String(120), nullable=True)
    violation_type = Column(String(50), nullable=False)      # missing | incorrect_format | font_too_small | illegible | prohibited_practice
    severity = Column(Enum(ViolationSeverity), default=ViolationSeverity.MAJOR)
    description = Column(Text, nullable=True)
    detected_value = Column(Text, nullable=True)             # what the system actually found (if anything)
    expected_requirement = Column(Text, nullable=True)

    report = relationship("ComplianceReport", back_populates="violations")


class AuditLog(Base):
    """Immutable trail of significant actions for accountability in an enforcement context."""
    __tablename__ = "audit_logs"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    action = Column(String(120), nullable=False)   # e.g. "LOGIN", "SCAN_CREATED", "REPORT_FINALIZED"
    entity_type = Column(String(80), nullable=True)
    entity_id = Column(String(80), nullable=True)
    details = Column(JSON, nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
