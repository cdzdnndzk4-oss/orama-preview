import csv
import io

from PIL import Image
from sqlalchemy.orm import Session

from service.batch_photos import run
from service.models import Photo, Product
from service.photo import process_photo
from service.pilot_review import build
from tests.photo_fixture import lightbox_photo
from tests.test_catalog import auth, setup


def test_batch_keeps_all_views_pending_and_blocks_publication(tmp_path):
    app, client = setup(tmp_path)
    headers = auth(client)
    source = tmp_path / "lightbox.jpg"
    source.write_bytes(lightbox_photo())
    manifest = tmp_path / "batch.csv"
    with manifest.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["product_id", "view", "path"])
        writer.writeheader()
        for view in ("front", "three-quarter", "side"):
            writer.writerow({"product_id": "furla-535", "view": view, "path": source})
    assert len(run(manifest, app.state.engine, app.state.storage, apply=False)) == 3
    with Session(app.state.engine) as db:
        assert db.query(Photo).count() == 0
    assert len(run(manifest, app.state.engine, app.state.storage, apply=True)) == 3
    with Session(app.state.engine) as db:
        product = db.get(Product, "furla-535")
        assert not product.published
        assert len(product.photos) == 3 and all(photo.chosen is None for photo in product.photos)
        payload = dict(id=product.id, brand=product.brand, model=product.model, category=product.category,
                       price_eur=product.price_cents / 100, lens=product.lens, bridge=product.bridge,
                       temple=product.temple, availability=product.availability,
                       description="Ελεγμένη περιγραφή.", description_verified=True, published=True)
        ids = [photo.id for photo in product.photos]
    assert client.put("/admin/api/products/furla-535", json=payload, headers=headers).status_code == 422
    for photo_id in ids:
        assert client.put(f"/admin/api/photos/{photo_id}/choice", json={"chosen": "processed"}, headers=headers).status_code == 200
        if photo_id != ids[-1]:
            assert client.put("/admin/api/products/furla-535", json=payload, headers=headers).status_code == 422
    assert client.put("/admin/api/products/furla-535", json=payload, headers=headers).status_code == 200
    assert client.get("/api/catalog/furla-535").status_code == 200


def test_two_stores_remain_distinct_in_public_catalog(tmp_path):
    app, client = setup(tmp_path)
    headers = auth(client)
    with Session(app.state.engine) as db:
        p = db.get(Product, "furla-535")
        payload = dict(id=p.id, brand=p.brand, model=p.model, category=p.category,
                       price_eur=p.price_cents / 100, lens=p.lens, bridge=p.bridge,
                       temple=p.temple, availability={"Αγία Παρασκευή": 2, "Κυψέλη": 3},
                       description="Ελεγμένη περιγραφή.", description_verified=True, published=True)
    assert client.put("/admin/api/products/furla-535", json=payload, headers=headers).status_code == 200
    item = client.get("/api/catalog/furla-535").json()
    assert item["availability"] == {"Αγία Παρασκευή": 2, "Κυψέλη": 3}
    assert item["inventory"]["quantity"] == 5


def test_photo_preserves_source_color_and_white_corners():
    output, info = process_photo(lightbox_photo())
    image = Image.open(io.BytesIO(output))
    assert image.size == (1200, 900) and image.getpixel((0, 0)) == (255, 255, 255)
    assert info["review_required"] is True
    assert image.crop((150, 250, 1050, 650)).convert("L").getextrema()[0] < 100


def test_private_review_gallery_uses_full_original_and_pending_choices(tmp_path):
    source = tmp_path / "source.jpg"
    source.write_bytes(lightbox_photo())
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(f"product_id,view,path\nframe-a,front,{source}\n", encoding="utf-8")
    output = tmp_path / "private"
    assert len(build(manifest, output)) == 1
    assert (output / "0001-original.jpg").read_bytes() == source.read_bytes()
    assert Image.open(output / "0001-processed.png").size == (1200, 900)
    page = (output / "review.html").read_text()
    assert 'value="pending" checked' in page and 'id="zoom"' in page
