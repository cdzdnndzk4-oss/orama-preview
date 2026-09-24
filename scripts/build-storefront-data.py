#!/usr/bin/env python3
"""Build a read-only catalog snapshot without unapproved editorial fields."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "catalog/products.json"
TARGET = ROOT / "catalog/storefront-preview.json"
data = json.loads(SOURCE.read_text(encoding="utf-8"))
result = []
for item in data["products"]:
    if len(item["images"]) != 3 or any(not (ROOT / image).is_file() for image in item["images"]):
        raise ValueError(f"Missing photos for {item['id']}")
    public = {key: item[key] for key in (
        "id", "brand", "model", "color_code", "category", "price_eur",
        "dimensions_mm", "images", "inventory"
    )}
    public["short_description"] = item.get("short_description") if item.get("description_review") == "approved_by_owner" else None
    public["material"] = item.get("material") if item.get("material_review") == "approved_by_owner" else None
    result.append(public)
TARGET.write_text(json.dumps({"products": result}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Wrote {len(result)} products to {TARGET}")
