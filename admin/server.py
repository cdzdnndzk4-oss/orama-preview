#!/usr/bin/env python3
"""Local product-entry prototype. Binds to loopback; never deploy this as-is."""
import base64
import io
import json
import re
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit
from PIL import Image
from description_library import OPENINGS, AUDIENCES, compose_description

ROOT = Path(__file__).resolve().parents[1]
ADMIN = Path(__file__).resolve().parent
DATA = ROOT / "data"
DB = DATA / "catalog.sqlite3"
UPLOADS = DATA / "uploads"
STORES = {"Αγία Παρασκευή", "Κυψέλη"}
MAX_BODY = 35 * 1024 * 1024
MAX_IMAGE = 9 * 1024 * 1024

def connect():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db


def initialize():
    DATA.mkdir(exist_ok=True)
    UPLOADS.mkdir(exist_ok=True)
    with connect() as db:
        db.execute("CREATE TABLE IF NOT EXISTS products (id TEXT PRIMARY KEY, body TEXT NOT NULL)")
        if db.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
            for item in json.loads((ROOT / "catalog/products.json").read_text(encoding="utf-8"))["products"]:
                db.execute("INSERT INTO products VALUES (?, ?)", (item["id"], json.dumps(item, ensure_ascii=False)))


def image_path(url):
    if not isinstance(url, str) or url.startswith("/") or "\\" in url or "?" in url or "#" in url:
        raise ValueError("Μη έγκυρη διαδρομή φωτογραφίας")
    path = (ROOT / url).resolve()
    if not any(path.is_relative_to(parent) for parent in (ROOT / "assets/products", UPLOADS)) or not path.is_file():
        raise ValueError("Η φωτογραφία δεν υπάρχει: " + str(url))
    return path


def validate(item, owner_reviewed=True, generate_missing=False, existing_descriptions=()):
    if not isinstance(item, dict):
        raise ValueError("Μη έγκυρο προϊόν")
    ident = str(item.get("id", ""))
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,70}", ident):
        raise ValueError("Ο κωδικός περιέχει μόνο λατινικά πεζά, αριθμούς και παύλες")
    for key in ("brand", "model", "category"):
        if not isinstance(item.get(key), str) or not item[key].strip() or len(item[key]) > 120:
            raise ValueError("Συμπλήρωσε " + key)
    if item["category"] not in ("Γυαλιά Οράσεως", "Γυαλιά Ηλίου"):
        raise ValueError("Μη έγκυρη κατηγορία")
    price = item.get("price_eur")
    if isinstance(price, bool) or not isinstance(price, (int, float)) or not 0 < price < 100000:
        raise ValueError("Η τιμή πρέπει να είναι θετικός αριθμός")
    dimensions = item.get("dimensions_mm")
    if not isinstance(dimensions, dict) or any(type(dimensions.get(k)) is not int or not 1 <= dimensions[k] <= 300 for k in ("lens", "bridge", "temple")):
        raise ValueError("Συμπλήρωσε χωριστά φακό, γέφυρα και βραχίονα")
    inventory = item.get("inventory")
    if not isinstance(inventory, dict) or inventory.get("store") not in STORES or inventory.get("quantity") != 1:
        raise ValueError("Επίλεξε κατάστημα. Η διαθεσιμότητα είναι 1 τεμάχιο")
    images = item.get("images")
    if not isinstance(images, list) or len(images) != 3:
        raise ValueError("Χρειάζονται τρεις φωτογραφίες με τη σειρά: μπροστά, τρία τέταρτα, πλάι")
    for url in images:
        image_path(url)
    color = item.get("color_code")
    if color is not None and (not isinstance(color, str) or len(color) > 40):
        raise ValueError("Μη έγκυρο χρώμα")
    style, audience = item.get("style") or None, item.get("audience") or None
    note = str(item.get("visual_note") or "").strip()
    if (style is not None and style not in OPENINGS) or (audience is not None and audience not in AUDIENCES) or len(note) > 300:
        raise ValueError("Μη έγκυρα στοιχεία για τη βιβλιοθήκη περιγραφών")
    description = item.get("short_description") or ""
    if generate_missing and not description and style and audience and note:
        description = compose_description(item, existing=existing_descriptions)
    if not isinstance(description, str) or (description.strip() and not 35 <= len(description.strip().split()) <= 60) or len(description) > 600:
        raise ValueError("Η περιγραφή, όταν συμπληρωθεί, πρέπει να έχει 35–60 λέξεις")
    material = item.get("material")
    if material is not None and (not isinstance(material, str) or len(material) > 80):
        raise ValueError("Μη έγκυρο υλικό σκελετού")
    product = {key: item[key] for key in ("id", "brand", "model", "color_code", "category", "price_eur", "dimensions_mm", "images", "inventory")}
    product.update(style=style, audience=audience, visual_note=note, short_description=description.strip(), material=material.strip() if material else None,
                   description_review="needs_description" if not description.strip() else "approved_by_owner" if owner_reviewed and item.get("description_confirmed") is True else "suggested_pending_owner_review",
                   material_review="approved_by_owner" if material and owner_reviewed and item.get("material_confirmed") is True else "pending_owner_review")
    return product


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, value):
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        size = int(self.headers.get("Content-Length", "0"))
        if not 0 < size <= MAX_BODY:
            raise ValueError("Το αρχείο είναι πολύ μεγάλο")
        return json.loads(self.rfile.read(size).decode("utf-8"))

    def serve_file(self, path):
        suffix = path.suffix.lower()
        content_type = {".html": "text/html", ".js": "text/javascript", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}.get(suffix)
        if not content_type or not path.is_file():
            self.send_error(404)
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type + ("; charset=utf-8" if suffix in (".html", ".js") else ""))
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        if path == "/api/products":
            with connect() as db:
                rows = db.execute("SELECT body FROM products ORDER BY id").fetchall()
            return self.send_json(200, {"products": [json.loads(row[0]) for row in rows]})
        if path in ("/", "/admin"):
            return self.serve_file(ADMIN / "index.html")
        if path == "/admin.js":
            return self.serve_file(ADMIN / "admin.js")
        file = (ROOT / path.lstrip("/")).resolve()
        if file.is_relative_to(ROOT / "assets/products") or file.is_relative_to(UPLOADS):
            return self.serve_file(file)
        self.send_error(404)

    def do_POST(self):
        try:
            path = urlsplit(self.path).path
            payload = self.read_json()
            if path == "/api/products":
                product = validate(payload)
                with connect() as db:
                    db.execute("INSERT INTO products VALUES (?, ?)", (product["id"], json.dumps(product, ensure_ascii=False)))
                return self.send_json(201, product)
            if path == "/api/draft-description":
                with connect() as db:
                    existing = [json.loads(row[0]).get("short_description", "") for row in db.execute("SELECT body FROM products ORDER BY rowid DESC LIMIT 50")]
                excluded = payload.get("exclude", [])
                if not isinstance(excluded, list) or len(excluded) > 50 or any(not isinstance(x, str) or len(x) > 600 for x in excluded):
                    raise ValueError("Μη έγκυρη λίστα προηγούμενων περιγραφών")
                existing.extend(excluded)
                return self.send_json(200, {"description": compose_description(payload, payload.get("variant", 0), existing), "review": "suggested_pending_owner_review"})
            if path == "/api/upload":
                data = base64.b64decode(payload["data"], validate=True)
                if not 0 < len(data) <= MAX_IMAGE:
                    raise ValueError("Κάθε φωτογραφία πρέπει να είναι έως 9 MB")
                with Image.open(io.BytesIO(data)) as image:
                    image.verify()
                    fmt = image.format
                if fmt not in ("JPEG", "PNG"):
                    raise ValueError("Επίλεξε JPEG ή PNG")
                name = re.sub(r"[^a-z0-9-]", "-", str(payload.get("name", "photo")).lower()).strip("-")[:60] or "photo"
                import secrets
                file = UPLOADS / f"{name}-{secrets.token_hex(5)}.{ 'jpg' if fmt == 'JPEG' else 'png' }"
                file.write_bytes(data)
                return self.send_json(201, {"url": file.relative_to(ROOT).as_posix()})
            if path == "/api/import":
                rows = payload.get("products")
                if not isinstance(rows, list) or not rows or len(rows) > 500:
                    raise ValueError("Δώσε 1 έως 500 προϊόντα")
                with connect() as db:
                    existing_rows = [json.loads(row[0]) for row in db.execute("SELECT body FROM products")]
                seen_descriptions = [row.get("short_description", "") for row in existing_rows]
                products = []
                for item in rows:
                    product = validate(item, owner_reviewed=False, generate_missing=True, existing_descriptions=seen_descriptions)
                    products.append(product)
                    seen_descriptions.append(product["short_description"])
                if len({p["id"] for p in products}) != len(products):
                    raise ValueError("Υπάρχουν διπλοί κωδικοί στο αρχείο")
                with connect() as db:
                    existing = {r[0] for r in db.execute("SELECT id FROM products")}
                    if existing.intersection(p["id"] for p in products):
                        raise ValueError("Υπάρχει ήδη προϊόν με έναν από τους κωδικούς")
                    db.executemany("INSERT INTO products VALUES (?, ?)", [(p["id"], json.dumps(p, ensure_ascii=False)) for p in products])
                return self.send_json(201, {"imported": len(products)})
            self.send_error(404)
        except sqlite3.IntegrityError:
            self.send_json(409, {"error": "Υπάρχει ήδη προϊόν με αυτόν τον κωδικό"})
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})

    def do_PUT(self):
        try:
            match = re.fullmatch(r"/api/products/([a-z0-9-]+)", urlsplit(self.path).path)
            if not match:
                return self.send_error(404)
            product = validate(self.read_json())
            if product["id"] != match.group(1):
                raise ValueError("Ο κωδικός δεν αλλάζει κατά την επεξεργασία")
            with connect() as db:
                row = db.execute("UPDATE products SET body=? WHERE id=?", (json.dumps(product, ensure_ascii=False), product["id"]))
                if not row.rowcount:
                    return self.send_json(404, {"error": "Το προϊόν δεν βρέθηκε"})
            self.send_json(200, product)
        except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})


if __name__ == "__main__":
    initialize()
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    print("Local ORAMA product admin: http://127.0.0.1:8765/admin", flush=True)
    server.serve_forever()
