import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from service.app import HASHER, create_app
from service.manage import seed
from service.models import AdminUser, Base, Product
from service.storage import Storage
from tests.photo_fixture import lightbox_photo


def setup(tmp_path):
    app = create_app("sqlite:///" + str(tmp_path / "catalog.db"), storage=Storage(local=tmp_path / "media"), testing=True)
    Base.metadata.create_all(app.state.engine)
    with Session(app.state.engine) as db:
        db.add(AdminUser(id="owner", email="owner@example.test", password_hash=HASHER.hash("test-password-123456")))
        db.commit()
        assert len(seed(db)) == 5
        assert seed(db) == []
    return app, TestClient(app)


def auth(client):
    response = client.post("/admin/api/login", json={"email": "owner@example.test", "password": "test-password-123456"})
    assert response.status_code == 200
    return {"X-CSRF-Token": response.json()["csrf"]}


def test_seed_and_public_catalog(tmp_path):
    app, client = setup(tmp_path)
    data = client.get("/api/catalog").json()
    assert data["total"] == 5 and data["per_page"] == 24
    assert {p["id"] for p in data["products"]} == {"ceo-94", "furla-535", "furla-vfu773", "yalea-chen-vya001", "yalea-elisabeth-vya040"}
    assert all(len(p["images"]) == 3 for p in data["products"])
    assert client.get(data["products"][0]["images"][0]).status_code == 200
    assert client.get("/api/catalog?q=nonexistent").json()["total"] == 0
    with Session(app.state.engine) as db:
        assert all(p.audience is None for p in db.query(Product).all())
        assert db.get(Product, "ceo-94").description_review == "pending_review"


def test_auth_csrf_drafts_publish_and_pagination(tmp_path):
    app, client = setup(tmp_path)
    assert client.get("/admin/api/products").status_code == 401
    assert client.put("/admin/api/products/test-frame", json={}).status_code == 401
    headers = auth(client)
    assert client.get("/admin/api/products/furla-535").status_code == 200
    assert client.get("/admin/api/products/missing-product").status_code == 404
    assert client.put("/admin/api/products/test-frame", json={}, headers={}).status_code == 403
    with Session(app.state.engine) as db:
        source = db.get(Product, "furla-535")
        payload = dict(id=source.id, brand=source.brand, model=source.model, color_code=source.color_code,
                       category=source.category, price_eur=source.price_cents / 100,
                       lens=source.lens, bridge=source.bridge, temple=source.temple,
                       availability=source.availability, description=source.description,
                       description_verified=False, published=False)
    assert client.put("/admin/api/products/furla-535", json=payload, headers=headers).status_code == 200
    assert client.get("/api/catalog").json()["total"] == 4
    payload["published"] = True
    payload["description_verified"] = True
    assert client.put("/admin/api/products/furla-535", json=payload, headers=headers).status_code == 422  # unverified feminine claim
    payload["description"] = "Κλασική αντίθεση χρωμάτων και διακριτική γραμμή στον σκελετό."
    assert client.put("/admin/api/products/furla-535", json=payload, headers=headers).status_code == 200
    assert client.get("/api/catalog").json()["total"] == 5

    # 550 drafts demonstrate server-side pagination without loading all rows.
    with Session(app.state.engine) as db:
        template = db.get(Product, "furla-535")
        for i in range(550):
            db.add(Product(id=f"bulk-{i:04}", brand="Bulk", model=f"M{i}", category=template.category,
                           price_cents=10000, lens=50, bridge=20, temple=140, availability={},
                           description="", published=True, legacy_images=template.legacy_images))
        db.commit()
    first = client.get("/api/catalog?brand=Bulk&page=1").json()
    last = client.get("/api/catalog?brand=Bulk&page=23").json()
    assert first["total"] == 550 and first["pages"] == 23
    assert len(first["products"]) == 24 and len(last["products"]) == 22
    assert client.get("/api/catalog?q=M549").json()["total"] == 1


def test_import_is_atomic_and_private(tmp_path):
    _, client = setup(tmp_path)
    headers = auth(client)
    payload = dict(id="new-one", brand="Brand", model="Model", category="Γυαλιά Οράσεως", price_eur=120,
                   lens=52, bridge=18, temple=140, availability={"Αγία Παρασκευή": 1}, published=False)
    result = client.post("/admin/api/import", json=[payload, {**payload, "id": "new-two", "price_eur": -4}], headers=headers)
    assert result.status_code == 422
    assert client.get("/api/catalog/new-one").status_code == 404
    assert client.post("/admin/api/import", json=[payload], headers=headers).json() == {"imported": 1}
    assert client.get("/api/catalog/new-one").status_code == 404
    assert client.get("/admin/api/products?q=new-one").json()["total"] == 1


def test_photo_review_blocks_publication_until_choice(tmp_path):
    app, client = setup(tmp_path)
    headers = auth(client)
    response = client.post("/admin/api/products/furla-535/photos/front", files={"file": ("front.jpg", lightbox_photo(), "image/jpeg")}, headers=headers)
    assert response.status_code == 200, response.text
    draft = response.json()
    assert draft["status"] == "pending_review" and draft["analysis"]["method"] == "source-pixels-only"
    assert client.get("/api/catalog/furla-535").status_code == 404
    assert client.get(draft["original"]).status_code == 200
    assert client.get(draft["processed"]).status_code == 200
    assert client.get("/media/" + draft["photo_id"]).status_code == 404
    assert client.put("/admin/api/photos/" + draft["photo_id"] + "/choice", json={"chosen": "processed"}, headers=headers).status_code == 200
    with Session(app.state.engine) as db:
        p = db.get(Product, "furla-535")
        payload = dict(id=p.id, brand=p.brand, model=p.model, category=p.category,
                       price_eur=p.price_cents / 100, lens=p.lens, bridge=p.bridge,
                       temple=p.temple, availability=p.availability,
                       description="Καθαρή γραμμή και χρωματική αντίθεση σε καθημερινό σκελετό.",
                       description_verified=True, published=True)
    assert client.put("/admin/api/products/furla-535", json=payload, headers=headers).status_code == 422
    for view in ("three-quarter", "side"):
        draft_view = client.post(f"/admin/api/products/furla-535/photos/{view}", files={"file": ("view.jpg", lightbox_photo(), "image/jpeg")}, headers=headers).json()
        assert client.put("/admin/api/products/furla-535", json=payload, headers=headers).status_code == 422
        assert client.put("/admin/api/photos/" + draft_view["photo_id"] + "/choice", json={"chosen": "original"}, headers=headers).status_code == 200
    assert client.put("/admin/api/products/furla-535", json=payload, headers=headers).status_code == 200
    assert client.get("/media/" + draft["photo_id"]).status_code == 200
