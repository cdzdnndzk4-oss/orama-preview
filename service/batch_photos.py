"""Batch pipeline for hundreds of photos; leaves affected products unpublished.

CSV columns: product_id,view,path. Views: front,three-quarter,side.
Run on a trusted worker with DATABASE_URL and ORAMA_S3_BUCKET configured.
`--apply` is explicit; dry run reads and processes but writes nothing.
"""
import argparse
import csv
import uuid
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from service.models import Photo, Product
from service.photo import process_photo
from service.storage import Storage
from service.app import MAX_PHOTO, VIEWS


def run(manifest, engine, storage, apply=False):
    records = list(csv.DictReader(Path(manifest).open(newline="", encoding="utf-8-sig")))
    if not records or len(records) > 3000 or set(records[0]) != {"product_id", "view", "path"}:
        raise ValueError("CSV columns: product_id,view,path (1–3000 rows)")
    if len({(r["product_id"], r["view"]) for r in records}) != len(records):
        raise ValueError("Duplicate product/view in manifest")
    result = []
    with Session(engine) as db:
        for item in records:
            product = db.get(Product, item["product_id"])
            if not product or item["view"] not in VIEWS:
                result.append((item["product_id"], item["view"], "ERROR: unknown product/view"))
                continue
            path = Path(item["path"]).expanduser().resolve()
            if not path.is_file() or not 0 < path.stat().st_size <= MAX_PHOTO:
                result.append((item["product_id"], item["view"], "ERROR: missing/large file"))
                continue
            data = path.read_bytes()
            try:
                processed, info = process_photo(data)
            except ValueError as exc:
                result.append((item["product_id"], item["view"], "REVIEW: " + str(exc)))
                continue
            if apply:
                photo = db.scalar(select(Photo).where(Photo.product_id == product.id, Photo.view == item["view"]))
                if not photo:
                    photo = Photo(id=uuid.uuid4().hex, product_id=product.id, view=item["view"], original_key="")
                    db.add(photo)
                prefix = f"photos/{product.id}/{photo.id}/{uuid.uuid4().hex}"
                storage.put(prefix + "/original", data, "image/jpeg" if data[:2] == b"\xff\xd8" else "image/png")
                storage.put(prefix + "/processed", processed, "image/png")
                photo.original_key, photo.processed_key, photo.chosen = prefix + "/original", prefix + "/processed", None
                product.published = False
                db.commit()  # A failure does not roll back already imported photos.
            result.append((product.id, item["view"], "DRAFT: preview required" if apply else "DRY RUN: eligible"))
    return result


def main():
    import os
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    url = os.getenv("DATABASE_URL", "")
    if not url.startswith("postgresql+psycopg://"):
        parser.error("PostgreSQL DATABASE_URL required")
    storage = Storage.from_environment() if args.apply else None
    for entry in run(args.manifest, create_engine(url), storage, args.apply):
        print(*entry, sep=",")


if __name__ == "__main__":
    main()
