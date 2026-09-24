#!/usr/bin/env python3
"""Export owner-approved product drafts into a checked catalog data file."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "catalog-drafts"
DESTINATION = ROOT / "catalog" / "products.json"
VIEWS = ["front", "three_quarter", "side"]
STORES = {"Αγία Παρασκευή", "Κυψέλη"}

products = []
for manifest in sorted(SOURCE.glob("*.json")):
    item = json.loads(manifest.read_text(encoding="utf-8"))
    if item["publication_status"] != "approved_for_catalog":
        continue
    if item["photo_review"] != "approved_by_owner":
        raise ValueError(f"Unapproved photos: {manifest.name}")
    if item.get("label_association_review") not in (None, "confirmed_by_owner"):
        raise ValueError(f"Unconfirmed label: {manifest.name}")
    inventory = item["inventory"]
    if inventory["quantity"] != 1 or inventory["store"] not in STORES:
        raise ValueError(f"Invalid stock or store: {manifest.name}")
    photos = item.get("photos") or item.get("processed_photos")
    if [photo["view"] for photo in photos] != VIEWS:
        raise ValueError(f"Expected front, three-quarter and side: {manifest.name}")
    image_urls = []
    for photo in photos:
        path = (manifest.parent / photo["file"]).resolve()
        if not path.is_relative_to(ROOT / "assets" / "products") or not path.is_file():
            raise ValueError(f"Missing or invalid image path: {manifest.name}")
        image_urls.append(path.relative_to(ROOT).as_posix())
    if not isinstance(item["price_eur"], (int, float)) or item["price_eur"] <= 0:
        raise ValueError(f"Invalid price: {manifest.name}")
    if not all(isinstance(item[k], int) and item[k] > 0 for k in ("lens_mm", "bridge_mm", "temple_mm")):
        raise ValueError(f"Invalid dimensions: {manifest.name}")
    products.append({
        "id": manifest.stem,
        "brand": item["brand"],
        "model": item["model"],
        "color_code": item["color_code"],
        "category": item["category"],
        "price_eur": item["price_eur"],
        "short_description": item.get("short_description"),
        "style": item.get("style"),
        "audience": item.get("audience"),
        "visual_note": item.get("visual_note", ""),
        "description_review": item.get("description_review", "pending_owner_review"),
        "material": item.get("material"),
        "material_review": item.get("material_review", "pending_owner_review"),
        "dimensions_mm": {"lens": item["lens_mm"], "bridge": item["bridge_mm"], "temple": item["temple_mm"]},
        "images": image_urls,
        "inventory": {"quantity": 1, "store": inventory["store"]},
    })

if not products:
    raise ValueError("No approved products to export")
DESTINATION.parent.mkdir(parents=True, exist_ok=True)
DESTINATION.write_text(json.dumps({"products": products}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Exported {len(products)} products to {DESTINATION}")
