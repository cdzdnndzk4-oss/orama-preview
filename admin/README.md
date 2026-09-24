# ORAMA local product entry

Run from the repository root:

```sh
python -m pip install -r admin/requirements.txt
python admin/server.py
```

Open `http://127.0.0.1:8765/admin` on the same computer. Five photo-approved products are copied into a local SQLite database on the first start. Later edits remain in `data/catalog.sqlite3`, outside Git. The form supports three JPEG/PNG photos per product with a local white-background/crop draft next to each original; the owner chooses each saved version, an editable 35–60-word description and material, one unit in a chosen store, edits, and CSV import with all rows validated before insertion. All five initial descriptions and materials have owner approval: four are steel and Yalea CHEN has a steel front with plastic temples. Material choices include steel, titanium, plastic and a mixed option; free-text editing remains available.

Open `http://127.0.0.1:8765/review` for a focused review of all products with their three photos, editable descriptions and materials. Each approval has its own checkbox. Editing either field clears its approval until the owner checks it again and saves that product. The local visitor view then shows approved fields after refresh; this does not publish them to GitHub Pages.

Open `http://127.0.0.1:8765/catalog-preview` to view the same database records as a read-only catalog with search, filtering and a three-photo gallery. Saving a product in the admin updates this local catalog after refresh. Unapproved copy and material have visible review labels. This is a local preview and has no purchase flow or automatic public publishing.

The main form lets the owner select three photos, choose the frame character and audience, and write one verified visual sentence. **Πρόταση από τη βιβλιοθήκη** assembles a 35–60-word draft from a local library of six moods × five openings × ten endings, with the product-specific detail sentence. This yields 300 curated wording paths before the individual details are considered. **Δημιουργία άλλης περιγραφής** cycles to another path. The owner can edit and approve the result separately. There is no external API, credential or per-use charge. The software does not read visual traits automatically from the three photographs: the operator must supply that checked sentence.

For many products, expand the **Μαζική εισαγωγή από πίνακα** section. CSV is a table file with one product per row. Import accepts an already written `short_description`; if empty, a row with `style`, `audience`, and `visual_note` receives a local library draft. Rows without enough detail stay in the editorial queue. Imported descriptions and materials remain pending review until their separate approval checkboxes are selected in the product form. Photo paths must refer to files already in `assets/products/` or `data/uploads/`.

This is an offline product-entry milestone. It has no remote sign-in, public deployment, checkout, payment processing, stock reservation. The local photo-cleaning preview is heuristic and requires visual review; the original stays available. Do not bind it to a public interface or upload it as a production server. Product changes in the local database are not automatically published to the GitHub Pages demo.

The local photo preview brightens the actual source pixels rather than generating new eyeglass geometry. It uses a fixed 800×600 canvas to avoid excessive enlargement of small objects in the original photos. A faint studio seam may remain; always inspect rimless frames at full size, and select the original if details are lost.

Open `http://127.0.0.1:8765/storefront-preview` for a customer-facing, read-only view of the same local records. Search, category filter and three-photo gallery work. Unapproved copy/material is hidden there, and there is no cart or checkout. The static fallback `catalog/storefront-preview.json` can be rebuilt with `python scripts/build-storefront-data.py` after updating the checked catalog JSON; local SQLite edits do not automatically change the static fallback.
