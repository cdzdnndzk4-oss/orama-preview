#!/usr/bin/env python3
"""Build a read-only product review page from local draft manifests."""
from html import escape
import json
from pathlib import Path
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[1]
ORDER = ["yalea-chen-vya001", "ceo-94", "yalea-elisabeth-vya040", "furla-vfu773", "furla-535"]
NOTES = {
    "yalea-chen-vya001": "Οι φωτογραφίες και η αντιστοίχιση της ετικέτας έχουν επιβεβαιωθεί.",
    "furla-vfu773": "Η εμφάνιση των τριών φωτογραφιών εγκρίθηκε.",
    "furla-535": "Η εμφάνιση των τριών φωτογραφιών εγκρίθηκε.",
}
# Keep the visible frame at the same share of every gallery viewport.
TARGET_VISIBLE_WIDTH = 0.85
FOREGROUND_DIFFERENCE = 32

def image_scale(path):
    image = Image.open(path).convert("RGB")
    difference = ImageChops.difference(image, Image.new("RGB", image.size, "white"))
    mask = difference.convert("L").point(lambda value: 255 if value > FOREGROUND_DIFFERENCE else 0)
    box = mask.getbbox() or (0, 0, image.width, image.height)
    return round(image.width / (box[2] - box[0]), 4)

def e(value):
    return escape(str(value), quote=True)

cards = []
for slug in ORDER:
    manifest = ROOT / "catalog-drafts" / f"{slug}.json"
    item = json.loads(manifest.read_text(encoding="utf-8"))
    photos = item.get("photos") or item.get("processed_photos")
    assert photos and [p["view"] for p in photos] == ["front", "three_quarter", "side"]
    paths = [((manifest.parent / p["file"]).resolve()) for p in photos]
    assert all(path.is_file() and path.is_relative_to(ROOT) for path in paths)
    assert all(item[k] is not None for k in ("brand", "model", "price_eur", "lens_mm", "bridge_mm", "temple_mm"))
    assert item["inventory"]["quantity"] == 1 and item["inventory"]["store"] in ("Αγία Παρασκευή", "Κυψέλη")
    urls = [e(path.relative_to(ROOT).as_posix()) for path in paths]
    scales = [image_scale(path) for path in paths]
    title = e(f'{item["brand"]} {item["model"]}')
    size = e(f'{item["lens_mm"]}–{item["bridge_mm"]}–{item["temple_mm"]}')
    color = e(item["color_code"] or "Δεν έχει δοθεί")
    price = e(f'{item["price_eur"]} €')
    store = e(item["inventory"]["store"])
    description = e(item.get("short_description") or "")
    material = e(item.get("material") or "Δεν έχει επιλεγεί")
    material_note = " (αρχική επιλογή προς επιβεβαίωση)" if item.get("material_review") != "approved_by_owner" else ""
    note = e(NOTES.get(slug, "Οι φωτογραφίες έχουν ελεγχθεί στο προηγούμενο δείγμα· αναμένουμε τελική επιβεβαίωση καταλόγου."))
    thumbs = "".join(f'<button type="button" class="thumb" aria-label="{label}" data-scale="{scale}" onclick="changeImage(this, \'{url}\')"><img src="{url}" alt="{title} — {label}" loading="lazy"></button>' for url, scale, label in zip(urls, scales, ("Μπροστά", "Τρία τέταρτα", "Πλάι")))
    cards.append(f'''<article class="card" data-search="{title.lower()} {color.lower()}">
      <div class="image"><img class="hero" src="{urls[0]}" style="--scale:{scales[0]}" alt="{title} μπροστινή όψη" loading="lazy"></div>
      <div class="thumbs">{thumbs}</div>
      <div class="details"><h2>{title}</h2><p class="meta">Χρώμα: {color} · Μέγεθος: {size}</p><strong>{price}</strong><p class="meta">Διαθεσιμότητα: 1 τεμάχιο · Κατάστημα: {store}</p><p>{description}</p><p class="meta">Υλικό: {material}{material_note}</p><p class="note">{note}</p></div>
    </article>''')

html = '''<!doctype html><html lang="el"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow,noarchive"><title>ORAMA — Έλεγχος προϊόντων</title>
<style>*{box-sizing:border-box}body{margin:0;background:#f3f8fb;color:#103653;font:16px/1.5 system-ui,-apple-system,Arial,sans-serif}header{background:#063e72;color:#fff;padding:22px max(20px,calc((100vw - 1200px)/2))}header b{font-size:28px;letter-spacing:.2em}header small{display:block;letter-spacing:.14em;font-size:10px}main{max-width:1200px;margin:auto;padding:30px 20px 70px}h1{font:normal 38px Georgia,serif;margin:0 0 10px}.intro{max-width:770px}.notice{background:#fff8e9;border:1px solid #efcf8d;padding:15px 18px;border-radius:8px;margin:24px 0}input{width:100%;max-width:420px;padding:12px 14px;border:1px solid #9eb5c8;border-radius:7px;font:inherit;margin:8px 0 20px}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px}.card{background:#fff;border:1px solid #dae6ef;border-radius:12px;overflow:hidden}.image{height:360px;position:relative;overflow:hidden;background:#fff}.hero{position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:calc(85% * var(--scale));max-width:none;height:auto}.thumbs{display:flex;gap:8px;padding:0 16px}.thumb{border:1px solid #d5e1ea;background:#fff;padding:2px;width:80px;height:62px;border-radius:5px;cursor:pointer}.thumb:focus-visible{outline:3px solid #0d6da8}.thumb img{width:100%;height:100%;object-fit:contain}.details{padding:16px 20px 22px}h2{font:normal 26px Georgia,serif;margin:0}.meta{color:#405a70;margin:7px 0}strong{font-size:24px}.note{background:#edf6fb;color:#254968;padding:10px;border-radius:6px;font-size:14px}footer{padding:25px;text-align:center;color:#526a7d}@media(max-width:700px){.grid{grid-template-columns:1fr}.image{height:260px}h1{font-size:32px}}</style></head><body>
<header><b>ORAMA</b><small>OPTIC STORES · ΕΣΩΤΕΡΙΚΟΣ ΕΛΕΓΧΟΣ</small></header><main><h1>Έλεγχος πέντε σκελετών</h1><p class="intro">Επίλεξε τις μικρές φωτογραφίες για να δεις μπροστά, τρία τέταρτα και πλάι. Έλεγξε ότι ο ίδιος σκελετός εμφανίζεται και στις τρεις.</p><div class="notice">Τα στοιχεία των πέντε σκελετών έχουν επιβεβαιωθεί για τον κατάλογο: 1 τεμάχιο ανά σκελετό στην Αγία Παρασκευή. Δεν γίνονται αγορές από αυτή τη σελίδα.</div><label for="search">Αναζήτηση προϊόντος</label><br><input id="search" type="search" placeholder="Μάρκα, μοντέλο ή χρώμα" oninput="filterCards(this.value)"><div class="grid">''' + "\n".join(cards) + '''</div></main><footer>ORAMA · Δοκιμαστική καταχώριση, όχι δημόσιο κατάστημα</footer><script>function changeImage(button,url){const hero=button.closest('.card').querySelector('.hero');hero.src=url;hero.style.setProperty('--scale',button.dataset.scale)}function filterCards(query){const q=query.toLocaleLowerCase('el');document.querySelectorAll('.card').forEach(card=>card.hidden=!card.dataset.search.includes(q))}</script></body></html>'''
html = html.replace("width:calc(85% * var(--scale))", f"width:calc({TARGET_VISIBLE_WIDTH*100:.0f}% * var(--scale))")
(ROOT / "catalog-review.html").write_text(html, encoding="utf-8")
print(f"Wrote catalog-review.html with {len(cards)} products")
