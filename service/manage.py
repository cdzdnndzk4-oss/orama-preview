"""Explicit, idempotent schema/seed and interactive admin provisioning."""
import argparse
import getpass
import json
import os
import re
import uuid
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from service.app import HASHER, GENDER_TERMS, ROOT
from service.models import AdminUser, Base, Product


def seed(conn, source=ROOT / "catalog/products.json"):
    created = []
    for item in json.loads(Path(source).read_text(encoding="utf-8"))["products"]:
        description = item.get("short_description") or ""
        existing = conn.get(Product, item["id"])
        if existing:
            # Preserve owner edits. If the stored copy is still exactly the checked
            # seed copy, keep the approval state recorded in catalog/products.json.
            if existing.description == description and item.get("description_review") == "approved_by_owner":
                existing.description_review = "approved_by_owner"
            if existing.material == item.get("material") and item.get("material_review") == "approved_by_owner":
                existing.material_review = "approved_by_owner"
            continue
        if len(item["images"]) != 3 or not all((ROOT / path).is_file() for path in item["images"]):
            raise ValueError("Missing original approved photos: " + item["id"])
        inv = item["inventory"]
        # Audience metadata remains unverified unless explicitly confirmed in admin.
        # Approved product copy/material from the checked source remains approved.
        row = Product(id=item["id"], brand=item["brand"], model=item["model"],
                      color_code=item.get("color_code"), frame_color=None,
                      material=item.get("material"), material_review=item.get("material_review", "pending_review"),
                      audience=None, audience_review="pending_review", category=item["category"], selection=False,
                      price_cents=round(item["price_eur"] * 100), lens=item["dimensions_mm"]["lens"],
                      bridge=item["dimensions_mm"]["bridge"], temple=item["dimensions_mm"]["temple"],
                      availability={inv["store"]: inv["quantity"]}, description=description,
                      description_review=item.get("description_review", "pending_review"),
                      published=True, legacy_images=item["images"])
        conn.add(row)
        created.append(row.id)
    conn.commit()
    return created


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("init", "seed", "create-admin", "ensure-local-admin", "sync-local-catalog"))
    parser.add_argument("--email")
    args = parser.parse_args()
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgresql+psycopg://"):
        parser.error("DATABASE_URL must be postgresql+psycopg://...")
    engine = create_engine(url, pool_pre_ping=True)
    if args.action == "init":
        Base.metadata.create_all(engine)
        print("Schema ready. Back up PostgreSQL before migrations in production.")
    elif args.action == "seed":
        with Session(engine) as conn:
            print("Imported:", ", ".join(seed(conn)) or "none (already present)")
    elif args.action == "create-admin":
        email = (args.email or input("Admin email: ")).strip().lower()
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            parser.error("Invalid email")
        password = getpass.getpass("New password (at least 16 characters): ")
        if len(password) < 16 or password != getpass.getpass("Confirm password: "):
            parser.error("Passwords differ or are shorter than 16 characters")
        with Session(engine) as conn:
            if conn.scalar(select(AdminUser).where(AdminUser.email == email)):
                parser.error("Admin already exists")
            conn.add(AdminUser(id=uuid.uuid4().hex, email=email, password_hash=HASHER.hash(password)))
            conn.commit()
        print("Admin created")
    elif args.action == "ensure-local-admin":
        if os.getenv("ORAMA_LOCAL_MODE") != "1":
            parser.error("ensure-local-admin is allowed only with ORAMA_LOCAL_MODE=1")
        email = os.getenv("ORAMA_LOCAL_ADMIN_EMAIL", "local@orama.test").strip().lower()
        password = os.getenv("ORAMA_LOCAL_ADMIN_PASSWORD", "")
        if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            parser.error("Invalid ORAMA_LOCAL_ADMIN_EMAIL")
        if len(password) < 16:
            parser.error("ORAMA_LOCAL_ADMIN_PASSWORD must be at least 16 characters")
        with Session(engine) as conn:
            existing = conn.scalar(select(AdminUser).where(AdminUser.email == email))
            if existing:
                print("Local admin already exists:", email)
            else:
                conn.add(AdminUser(id=uuid.uuid4().hex, email=email, password_hash=HASHER.hash(password)))
                conn.commit()
                print("Local admin created:", email)
    else:
        if os.getenv("ORAMA_LOCAL_MODE") != "1":
            parser.error("sync-local-catalog is allowed only with ORAMA_LOCAL_MODE=1")
        source = json.loads((ROOT / "catalog/products.json").read_text(encoding="utf-8"))["products"]
        changed = 0
        with Session(engine) as conn:
            for item in source:
                row = conn.get(Product, item["id"])
                if not row:
                    continue
                row.description = item.get("short_description") or ""
                row.description_review = item.get("description_review", "pending_review")
                if item.get("material_review") == "approved_by_owner":
                    row.material = item.get("material")
                    row.material_review = "approved_by_owner"
                changed += 1
            conn.commit()
        print("Local catalog synchronized:", changed)


if __name__ == "__main__":
    main()
