"""
One-time seed script for local/demo environments.
Run with:  python -m scripts.seed
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal, Base, engine
from app.models import User, UserRole, Product, ProductCategory
from app.security import hash_password

Base.metadata.create_all(bind=engine)


def run():
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == "admin@legalmetrology.gov.in").first():
            print("Seed data already present. Skipping.")
            return

        admin = User(
            full_name="System Administrator",
            email="admin@legalmetrology.gov.in",
            hashed_password=hash_password("ChangeMe@123"),
            role=UserRole.ADMIN,
            designation="Director, Legal Metrology",
        )
        officer = User(
            full_name="Demo Enforcement Officer",
            email="officer@legalmetrology.gov.in",
            hashed_password=hash_password("ChangeMe@123"),
            role=UserRole.ENFORCEMENT_OFFICER,
            designation="Legal Metrology Inspector",
            jurisdiction="Demo District",
        )
        db.add_all([admin, officer])

        sample_products = [
            Product(name="Refined Sunflower Oil 1L", brand="SunGold", category=ProductCategory.FMCG_OTHER,
                    manufacturer_name="SunGold Foods Pvt Ltd", is_imported=False, source_channel="Retail Store"),
            Product(name="Wireless Earbuds Pro", brand="AudioMax", category=ProductCategory.ELECTRONICS,
                    manufacturer_name="AudioMax Electronics", is_imported=True, source_channel="Amazon.in"),
        ]
        db.add_all(sample_products)
        db.commit()

        print("Seed complete.")
        print("Admin login:   admin@legalmetrology.gov.in / ChangeMe@123")
        print("Officer login: officer@legalmetrology.gov.in / ChangeMe@123")
        print("!! CHANGE THESE PASSWORDS IMMEDIATELY IN ANY NON-LOCAL ENVIRONMENT !!")
    finally:
        db.close()


if __name__ == "__main__":
    run()
