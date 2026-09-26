"""Build a private, offline full-resolution review folder from a trusted CSV.

CSV: product_id,view,path. Original photographs are copied only to output;
never add the output folder or its ZIP to the public repository.
Selections in the gallery are notes for review, not publication approvals.
"""
import argparse
import csv
import html
import json
from pathlib import Path

from service.photo import process_photo


def build(manifest: Path, output: Path):
    records = list(csv.DictReader(manifest.open(newline="", encoding="utf-8-sig")))
    if not 1 <= len(records) <= 3000 or set(records[0]) != {"product_id", "view", "path"}:
        raise ValueError("CSV columns: product_id,view,path (1–3000 rows)")
    output.mkdir(parents=True, exist_ok=True)
    items = []
    for i, entry in enumerate(records):
        source = Path(entry["path"]).expanduser().resolve()
        if not source.is_file() or source.suffix.lower() not in (".jpeg", ".jpg", ".png"):
            raise ValueError(f"Missing JPEG/PNG at row {i + 1}")
        data = source.read_bytes()
        processed, analysis = process_photo(data)
        original_name = f"{i + 1:04d}-original{source.suffix.lower()}"
        processed_name = f"{i + 1:04d}-processed.png"
        (output / original_name).write_bytes(data)
        (output / processed_name).write_bytes(processed)
        items.append(dict(product_id=entry["product_id"], view=entry["view"], original=original_name,
                          processed=processed_name, analysis=analysis))
    cards = []
    for i, item in enumerate(items):
        title = html.escape(item["product_id"] + " · " + item["view"])
        cards.append(f'<article><h2>{title}</h2><div class="pair"><figure><figcaption>Πρωτότυπο · πλήρης ανάλυση</figcaption><img src="{item["original"]}" alt="Πρωτότυπο" loading="lazy"></figure><figure><figcaption>Πρόταση · 1200 × 900</figcaption><img src="{item["processed"]}" alt="Επεξεργασμένο" loading="lazy"></figure></div><label><input type="radio" name="choice-{i}" value="original"> Πρωτότυπο</label> <label><input type="radio" name="choice-{i}" value="processed"> Επεξεργασμένο</label> <label><input type="radio" name="choice-{i}" value="pending" checked> Εκκρεμεί</label></article>')
    page = '''<!doctype html><html lang="el"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ORAMA · ιδιωτικός έλεγχος φωτογραφιών</title><style>body{font:16px system-ui;color:#123b60;background:white;max-width:1400px;margin:auto;padding:20px}article{border:1px solid #ccdce6;border-radius:8px;padding:18px;margin:24px 0}.pair{display:grid;grid-template-columns:1fr 1fr;gap:12px;max-height:850px;overflow:auto}.pair img{width:100%;height:auto}.zoom .pair img{width:auto;max-width:none}figure{margin:0;min-width:0}figcaption{font-weight:bold;margin-bottom:8px}label{display:inline-block;padding:12px}button{padding:12px;border:0;background:#073f72;color:#fff;cursor:pointer}@media(max-width:700px){.pair{grid-template-columns:1fr}} </style><h1>ORAMA · ιδιωτικός έλεγχος</h1><p>Οι επιλογές είναι σημειώσεις σε αυτόν τον browser. Δεν δημοσιεύουν φωτογραφίες. Κάνε τον τελικό έλεγχο στον προστατευμένο admin.</p><button id="zoom">Μεγέθυνση 100%</button> <button id="export">Λήψη επιλογών JSON</button>'''+''.join(cards)+'''<script>const items=__ITEMS__;document.querySelector('#zoom').onclick=()=>{const active=document.body.classList.toggle('zoom');document.querySelector('#zoom').textContent=active?'Προσαρμογή στο παράθυρο':'Μεγέθυνση 100%'};document.querySelector('#export').onclick=()=>{const choices=items.map((item,i)=>({product_id:item.product_id,view:item.view,chosen:document.querySelector('input[name="choice-'+i+'"]:checked').value}));const link=document.createElement('a');link.href=URL.createObjectURL(new Blob([JSON.stringify(choices,null,2)],{type:'application/json'}));link.download='orama-photo-review-choices.json';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000)};</script></html>'''
    (output / "review.html").write_text(page.replace("__ITEMS__", json.dumps(items, ensure_ascii=False).replace("<", "\\u003c")), encoding="utf-8")
    return items


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(f"Prepared {len(build(args.manifest, args.output))} photos for private review at {args.output / 'review.html'}")


if __name__ == "__main__":
    main()
