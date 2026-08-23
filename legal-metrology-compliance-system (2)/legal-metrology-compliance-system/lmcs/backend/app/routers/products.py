from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product, User, UserRole, ScanRecord
from app.schemas import ProductCreate, ProductOut, PaginatedResponse
from app.security import get_current_user, require_roles

router = APIRouter(prefix="/products", tags=["Product Repository"])


@router.post("", response_model=ProductOut, status_code=201)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.ENFORCEMENT_OFFICER)),
):
    product = Product(**payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("", response_model=PaginatedResponse)
def search_products(
    q: str | None = Query(None, description="Free-text search over name, brand, manufacturer, barcode"),
    category: str | None = None,
    is_imported: bool | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Product)
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(Product.name.ilike(like), Product.brand.ilike(like),
                Product.manufacturer_name.ilike(like), Product.barcode.ilike(like))
        )
    if category:
        query = query.filter(Product.category == category)
    if is_imported is not None:
        query = query.filter(Product.is_imported == is_imported)

    total = query.count()
    items = (
        query.order_by(Product.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedResponse(
        total=total, page=page, page_size=page_size,
        items=[ProductOut.model_validate(p) for p in items],
    )


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product


@router.get("/{product_id}/history")
def get_product_history(
    product_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Full inspection history for a product: every scan + its compliance outcome."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    scans = (
        db.query(ScanRecord)
        .filter(ScanRecord.product_id == product_id)
        .order_by(ScanRecord.created_at.desc())
        .all()
    )
    history = []
    for s in scans:
        report = s.compliance_report
        history.append({
            "scan_id": s.id,
            "status": s.status.value,
            "created_at": s.created_at,
            "listing_type": s.listing_type,
            "compliance_status": report.overall_status.value if report else None,
            "compliance_score": report.compliance_score if report else None,
            "report_id": report.id if report else None,
        })
    return {"product": ProductOut.model_validate(product), "history": history}
