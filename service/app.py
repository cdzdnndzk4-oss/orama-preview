"""ORAMA catalog service. Deploy behind HTTPS with PostgreSQL and private object storage."""
import hashlib
import io
import json
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, func, or_, select
from sqlalchemy.orm import Session as DBSession, sessionmaker

from service.models import AdminUser, Base, Photo, Product, Session
from service.storage import Storage

ROOT = Path(__file__).resolve().parents[1]
VIEWS = ("front", "three-quarter", "side")
STORES = ("Αγία Παρασκευή", "Κυψέλη")
HASHER = PasswordHasher()
MAX_PHOTO = 9 * 1024 * 1024
GENDER_TERMS = re.compile(r"γυναικ|ανδρικ|θηλυκ|αρρενωπ", re.I)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def utcnow():
    return datetime.now(timezone.utc)


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class ProductInput(BaseModel):
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,70}$")
    brand: str = Field(min_length=1, max_length=120)
    model: str = Field(min_length=1, max_length=120)
    color_code: str | None = Field(default=None, max_length=40)
    frame_color: str | None = Field(default=None, max_length=120)
    material: str | None = Field(default=None, max_length=120)
    material_verified: bool = False
    audience: str | None = Field(default=None, max_length=60)
    audience_verified: bool = False
    category: str
    selection: bool = False
    price_eur: float = Field(gt=0, lt=100000)
    lens: int = Field(ge=1, le=300)
    bridge: int = Field(ge=1, le=300)
    temple: int = Field(ge=1, le=300)
    availability: dict[str, int]
    description: str = Field(default="", max_length=1000)
    description_verified: bool = False
    published: bool = False


def validate_product(p: ProductInput):
    if p.category not in ("Γυαλιά Οράσεως", "Γυαλιά Ηλίου"):
        raise HTTPException(422, "Μη έγκυρη κατηγορία")
    if set(p.availability) - set(STORES) or any(type(n) is not int or n < 0 or n > 100000 for n in p.availability.values()):
        raise HTTPException(422, "Μη έγκυρη διαθεσιμότητα")
    if p.published and not p.description_verified:
        raise HTTPException(422, "Έλεγξε την περιγραφή πριν από τη δημοσίευση")
    if p.description_verified and GENDER_TERMS.search(p.description) and not p.audience_verified:
        raise HTTPException(422, "Η περιγραφή αναφέρει φύλο χωρίς επιβεβαίωση")
    if p.audience and not p.audience_verified and p.published:
        raise HTTPException(422, "Επιβεβαίωσε το κοινό ή άφησέ το κενό")


def apply_product(row: Product, p: ProductInput):
    validate_product(p)
    for field in ("brand", "model", "color_code", "frame_color", "category", "selection", "lens", "bridge", "temple", "availability", "description", "published"):
        setattr(row, field, getattr(p, field))
    row.price_cents = round(p.price_eur * 100)
    row.material = p.material or None
    row.material_review = "approved_by_owner" if p.material and p.material_verified else "pending_review"
    row.audience = p.audience if p.audience_verified else None
    row.audience_review = "approved_by_owner" if p.audience and p.audience_verified else "pending_review"
    row.description_review = "approved_by_owner" if p.description_verified else "pending_review"


def serialize(row: Product, public=False):
    photos = {p.view: p for p in row.photos}
    images = []
    for i, view in enumerate(VIEWS):
        if view in photos:
            photo = photos[view]
            images.append(f"/media/{photo.id}" if photo.chosen else None)
        else:
            images.append("/" + row.legacy_images[i] if i < len(row.legacy_images) else None)
    value = dict(id=row.id, brand=row.brand, model=row.model, color_code=row.color_code,
                 frame_color=row.frame_color, category=row.category, selection=row.selection,
                 price_eur=row.price_cents / 100,
                 dimensions_mm=dict(lens=row.lens, bridge=row.bridge, temple=row.temple),
                 inventory=dict(quantity=sum(row.availability.values()), store=" · ".join(k for k, n in row.availability.items() if n)),
                 availability=row.availability, images=images,
                 short_description=row.description if row.description_review == "approved_by_owner" else "",
                 material=row.material if row.material_review == "approved_by_owner" else None)
    if not public:
        value.update(description=row.description, material=row.material, audience=row.audience,
                     material_review=row.material_review, audience_review=row.audience_review,
                     description_review=row.description_review, published=row.published,
                     photos=[dict(id=p.id, view=p.view, chosen=p.chosen,
                                  original=f"/admin/api/photos/{p.id}/original",
                                  processed=f"/admin/api/photos/{p.id}/processed" if p.processed_key else None) for p in row.photos])
    return value


def create_app(database_url=None, storage=None, testing=False):
    url = database_url or os.getenv("DATABASE_URL")
    if not url or (not testing and not url.startswith("postgresql+psycopg://")):
        raise RuntimeError("Production requires DATABASE_URL=postgresql+psycopg://...")
    if not testing and (not os.getenv("ORAMA_S3_BUCKET") or not os.getenv("ORAMA_PUBLIC_ORIGIN", "").startswith("https://")):
        raise RuntimeError("Production requires ORAMA_S3_BUCKET and HTTPS ORAMA_PUBLIC_ORIGIN")
    kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {"pool_pre_ping": True}
    engine = create_engine(url, **kwargs)
    db_factory = sessionmaker(engine, expire_on_commit=False)
    files = storage or Storage.from_environment(testing)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    def db():
        with db_factory() as connection:
            yield connection

    def require_admin(request: Request, conn: DBSession = Depends(db)):
        token = request.cookies.get("orama_admin")
        session = conn.get(Session, digest(token)) if token else None
        if not session or aware(session.expires_at) <= utcnow():
            raise HTTPException(401, "Απαιτείται σύνδεση διαχειριστή")
        if request.method not in ("GET", "HEAD"):
            csrf = request.headers.get("X-CSRF-Token", "")
            origin = request.headers.get("Origin")
            expected = os.getenv("ORAMA_PUBLIC_ORIGIN")
            if not csrf or not secrets.compare_digest(digest(csrf), session.csrf_hash) or (origin and expected and origin != expected):
                raise HTTPException(403, "Μη έγκυρο αίτημα ασφαλείας")
        return session

    @app.get("/api/catalog")
    def catalog(q: str = "", category: str = "", selection: bool = False, brand: str = "", material: str = "", page: int = 1, conn: DBSession = Depends(db)):
        if not 1 <= page <= 10000 or len(q) > 120:
            raise HTTPException(422, "Μη έγκυρη αναζήτηση")
        stmt = select(Product).where(Product.published.is_(True))
        if category:
            stmt = stmt.where(Product.category == category)
        if selection:
            stmt = stmt.where(Product.selection.is_(True))
        if brand:
            stmt = stmt.where(Product.brand == brand)
        if material:
            stmt = stmt.where(Product.material == material, Product.material_review == "approved_by_owner")
        if q.strip():
            term = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            stmt = stmt.where(or_(Product.brand.ilike(term, escape="\\"), Product.model.ilike(term, escape="\\"), Product.color_code.ilike(term, escape="\\"), Product.id.ilike(term, escape="\\")))
        total = conn.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = conn.scalars(stmt.order_by(Product.brand, Product.model, Product.id).offset((page - 1) * 24).limit(24)).all()
        return {"products": [serialize(p, public=True) for p in rows], "page": page, "per_page": 24, "total": total, "pages": (total + 23) // 24}

    @app.get("/api/catalog-facets")
    def facets(category: str = "", conn: DBSession = Depends(db)):
        stmt = select(Product).where(Product.published.is_(True))
        if category:
            stmt = stmt.where(Product.category == category)
        rows = conn.scalars(stmt).all()
        return {"brands": sorted({p.brand for p in rows}),
                "materials": sorted({p.material for p in rows if p.material and p.material_review == "approved_by_owner"})}

    @app.get("/api/catalog/{product_id}")
    def public_product(product_id: str, conn: DBSession = Depends(db)):
        row = conn.get(Product, product_id)
        if not row or not row.published:
            raise HTTPException(404)
        return serialize(row, public=True)

    @app.post("/admin/api/login")
    def login(request: Request, response: Response, credentials: dict, conn: DBSession = Depends(db)):
        origin = request.headers.get("Origin")
        expected = os.getenv("ORAMA_PUBLIC_ORIGIN")
        if origin and expected and origin != expected:
            raise HTTPException(403)
        email = str(credentials.get("email", "")).strip().lower()
        password = str(credentials.get("password", ""))
        user = conn.scalar(select(AdminUser).where(AdminUser.email == email)) if len(email) <= 254 else None
        if not user or user.disabled or (user.locked_until and aware(user.locked_until) > utcnow()):
            raise HTTPException(401, "Λανθασμένα στοιχεία ή προσωρινό κλείδωμα")
        try:
            HASHER.verify(user.password_hash, password)
        except (VerifyMismatchError, ValueError):
            user.failed_attempts += 1
            if user.failed_attempts >= 5:
                user.locked_until = utcnow() + timedelta(minutes=15)
                user.failed_attempts = 0
            conn.commit()
            raise HTTPException(401, "Λανθασμένα στοιχεία ή προσωρινό κλείδωμα")
        user.failed_attempts = 0
        user.locked_until = None
        token, csrf = secrets.token_urlsafe(48), secrets.token_urlsafe(32)
        conn.add(Session(token_hash=digest(token), user_id=user.id, csrf_hash=digest(csrf), expires_at=utcnow() + timedelta(hours=8)))
        conn.commit()
        response.set_cookie("orama_admin", token, max_age=28800, secure=not testing, httponly=True, samesite="strict", path="/")
        response.headers["Cache-Control"] = "no-store"
        return {"csrf": csrf}

    @app.post("/admin/api/logout")
    def logout(response: Response, session: Session = Depends(require_admin), conn: DBSession = Depends(db)):
        conn.delete(session)
        conn.commit()
        response.delete_cookie("orama_admin", path="/")
        return {"ok": True}

    @app.get("/admin/api/products")
    def admin_products(q: str = "", page: int = 1, _: Session = Depends(require_admin), conn: DBSession = Depends(db)):
        if page < 1 or len(q) > 120:
            raise HTTPException(422)
        stmt = select(Product)
        if q:
            stmt = stmt.where(or_(Product.brand.ilike(f"%{q}%"), Product.model.ilike(f"%{q}%"), Product.id.ilike(f"%{q}%")))
        total = conn.scalar(select(func.count()).select_from(stmt.subquery()))
        rows = conn.scalars(stmt.order_by(Product.id).offset((page - 1) * 24).limit(24)).all()
        return {"products": [serialize(p) for p in rows], "total": total, "page": page}

    @app.put("/admin/api/products/{product_id}")
    def save_product(product_id: str, payload: ProductInput, _: Session = Depends(require_admin), conn: DBSession = Depends(db)):
        if payload.id != product_id:
            raise HTTPException(422, "Ο κωδικός δεν αλλάζει")
        row = conn.get(Product, product_id)
        if not row:
            row = Product(id=product_id, legacy_images=[])
            conn.add(row)
        approved = {p.view for p in row.photos if p.chosen}
        if payload.published and ((row.photos and approved != set(VIEWS)) or
                                  (not row.photos and len(row.legacy_images) != len(VIEWS))):
            raise HTTPException(422, "Χρειάζονται τρεις εγκεκριμένες εικόνες")
        apply_product(row, payload)
        conn.commit()
        conn.refresh(row)
        return serialize(row)

    @app.post("/admin/api/import")
    def import_products(payload: list[ProductInput], _: Session = Depends(require_admin), conn: DBSession = Depends(db)):
        if not 1 <= len(payload) <= 500 or len({p.id for p in payload}) != len(payload):
            raise HTTPException(422, "Δώσε 1–500 διαφορετικά προϊόντα")
        if any(conn.get(Product, p.id) for p in payload):
            raise HTTPException(409, "Υπάρχει ήδη προϊόν στο αρχείο")
        for p in payload:
            if p.published:
                raise HTTPException(422, "Η μαζική εισαγωγή δημιουργεί μόνο πρόχειρα")
            row = Product(id=p.id, legacy_images=[])
            apply_product(row, p)
            conn.add(row)
        conn.commit()
        return {"imported": len(payload)}

    @app.post("/admin/api/products/{product_id}/photos/{view}")
    async def photo_draft(product_id: str, view: str, file: UploadFile = File(), _: Session = Depends(require_admin), conn: DBSession = Depends(db)):
        if view not in VIEWS or not (row := conn.get(Product, product_id)):
            raise HTTPException(404)
        data = await file.read(MAX_PHOTO + 1)
        if not 0 < len(data) <= MAX_PHOTO:
            raise HTTPException(413, "Φωτογραφία έως 9 MB")
        from service.photo import process_photo
        try:
            processed, info = process_photo(data)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        photo = conn.scalar(select(Photo).where(Photo.product_id == product_id, Photo.view == view))
        if not photo:
            photo = Photo(id=uuid.uuid4().hex, product_id=product_id, view=view, original_key="")
            conn.add(photo)
        # Each replacement gets new immutable keys; the prior media remains until cleanup.
        prefix = f"photos/{product_id}/{photo.id}/{uuid.uuid4().hex}"
        files.put(prefix + "/original", data, "image/jpeg" if data[:2] == b"\xff\xd8" else "image/png")
        files.put(prefix + "/processed", processed, "image/png")
        photo.original_key, photo.processed_key, photo.chosen = prefix + "/original", prefix + "/processed", None
        row.published = False  # A changed photograph must be reviewed again.
        conn.commit()
        return {"photo_id": photo.id, "original": f"/admin/api/photos/{photo.id}/original", "processed": f"/admin/api/photos/{photo.id}/processed", "analysis": info, "status": "pending_review"}

    @app.put("/admin/api/photos/{photo_id}/choice")
    def choose_photo(photo_id: str, choice: dict, _: Session = Depends(require_admin), conn: DBSession = Depends(db)):
        photo = conn.get(Photo, photo_id)
        if not photo:
            raise HTTPException(404)
        selected = choice.get("chosen")
        if selected not in ("original", "processed") or (selected == "processed" and not photo.processed_key):
            raise HTTPException(422)
        photo.chosen = selected
        conn.commit()
        return {"chosen": selected}

    @app.get("/admin/api/photos/{photo_id}/{kind}")
    def private_photo(photo_id: str, kind: str, _: Session = Depends(require_admin), conn: DBSession = Depends(db)):
        photo = conn.get(Photo, photo_id)
        if not photo or kind not in ("original", "processed") or not (key := getattr(photo, kind + "_key")):
            raise HTTPException(404)
        content = files.get(key)
        return StreamingResponse(io.BytesIO(content), media_type="image/png" if content.startswith(b"\x89PNG") else "image/jpeg", headers={"Cache-Control": "no-store"})

    @app.get("/media/{photo_id}")
    def public_photo(photo_id: str, conn: DBSession = Depends(db)):
        photo = conn.get(Photo, photo_id)
        if not photo or not photo.chosen or not photo.product.published:
            raise HTTPException(404)
        content = files.get(getattr(photo, photo.chosen + "_key"))
        return StreamingResponse(io.BytesIO(content), media_type="image/png" if content.startswith(b"\x89PNG") else "image/jpeg", headers={"Cache-Control": "public, max-age=3600"})

    @app.get("/assets/products/{product_id}/{view}.png")
    def legacy_photo(product_id: str, view: str):
        if not re.fullmatch(r"[a-z0-9-]{2,72}", product_id) or view not in VIEWS:
            raise HTTPException(404)
        path = ROOT / "assets/products" / product_id / (view + ".png")
        if not path.is_file():
            raise HTTPException(404)
        return FileResponse(path)

    @app.get("/admin")
    def admin_page():
        return FileResponse(ROOT / "service/admin.html", headers={"Cache-Control": "no-store", "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' blob:; connect-src 'self'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"})

    @app.get("/service/admin.js")
    def admin_script():
        return FileResponse(ROOT / "service/admin.js", media_type="text/javascript")

    @app.get("/")
    def home():
        return FileResponse(ROOT / "index.html", headers={"Cache-Control": "no-store"})

    app.state.engine = engine
    app.state.db_factory = db_factory
    app.state.storage = files
    return app


def app_from_env():
    return create_app()


app = None  # Use `uvicorn service.app:app_from_env --factory` to fail closed on missing configuration.
