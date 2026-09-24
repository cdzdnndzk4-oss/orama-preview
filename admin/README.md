# ORAMA local product entry

Run from the repository root:

```sh
python admin/server.py
```

Open `http://127.0.0.1:8765/admin` on the same computer. Five photo-approved products are copied into a local SQLite database on the first start. Later edits remain in `data/catalog.sqlite3`, outside Git. The form supports three JPEG/PNG photos per product, an editable 35–60-word description and material, one unit in a chosen store, edits, and CSV import with all rows validated before insertion. These five descriptions and materials remain suggestions pending owner review.

Open `http://127.0.0.1:8765/catalog-preview` to view the same database records as a read-only catalog with search, filtering and a three-photo gallery. Saving a product in the admin updates this local catalog after refresh. Unapproved copy and material have visible review labels. This is a local preview and has no purchase flow or automatic public publishing.

The main form lets the owner select three photos, choose the frame character and audience, and write one verified visual sentence. **Πρόταση από τη βιβλιοθήκη** assembles a 35–60-word draft from a local library of six moods × five openings × ten endings, with the product-specific detail sentence. This yields 300 curated wording paths before the individual details are considered. **Δημιουργία άλλης περιγραφής** cycles to another path. The owner can edit and approve the result separately. There is no external API, credential or per-use charge. The software does not read visual traits automatically from the three photographs: the operator must supply that checked sentence.

For many products, expand the **Μαζική εισαγωγή από πίνακα** section. CSV is a table file with one product per row. Import accepts an already written `short_description`; if empty, a row with `style`, `audience`, and `visual_note` receives a local library draft. Rows without enough detail stay in the editorial queue. Imported descriptions and materials remain pending review until their separate approval checkboxes are selected in the product form. Photo paths must refer to files already in `assets/products/` or `data/uploads/`.

This is an offline product-entry milestone. It has no remote sign-in, public deployment, checkout, payment processing, stock reservation, or automatic photo cleaning. Do not bind it to a public interface or upload it as a production server. Product changes in the local database are not automatically published to the GitHub Pages demo.
