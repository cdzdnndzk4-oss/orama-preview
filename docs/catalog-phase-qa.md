# Catalog/admin phase QA — 2026-09-26

Base: fetched `origin/main` at `cdf8e43` (includes PR #1 and subsequent commits). Working branch: `production/admin-catalog-v1` (local until GitHub write access is available). No edits to Wix, DNS or `oramaoptical.gr`; no merge.

Verified with FastAPI TestClient and SQLite **test fixture**, not a deployed production service:

- Idempotent import of the five IDs; all 15 existing image paths resolve and no asset file changed. Existing materials retain recorded review state; `audience` labels are not migrated as confirmed facts. Gender claims in old descriptions remain pending and are hidden from the public API.
- Anonymous admin API access returns 401; writes without valid session CSRF return 403. Login, draft edits, publication gating, publication/unpublication and logout paths are exercised.
- Public catalog exposes published records; search and server-side pagination returned 24 items per page across 550 generated products. Batch import rejects invalid rows atomically and keeps new records unpublished.
- A photo upload keeps the original and processed versions private, unpublishes the affected product, and requires a selected variant before public media is available. The preview endpoint uses original image pixels without a generative model.
- `node --check` parsed the new admin JS and the existing storefront's revised inline JS without syntax errors.

Not verified: actual PostgreSQL and S3 integration (no credentials/resources), reverse proxy/HTTPS, real browser rendering on desktop/mobile, 1,500-image endurance under hosting constraints, production migration/backup, cross-browser CSS and remote preview. Local browser automation could not start because Chromium was unavailable, browser download returned an invalid zero-byte archive, and the cloud browser blocked loopback. These are release blockers, not pass results. The standalone GitHub Pages link still serves its own `main` and is not the new service.

Photo pilot: nine original lightbox JPEGs (`01/02/03-IMG_6530–6532`, `6536–6538`, `6539–6541`) cover three visually different frame types and all three views. All nine passed the deterministic process. Each is 1200×900 with #FFFFFF corners and an approximately 78% subject width; source files were not changed. [Side-by-side sheet](photo-pilot-3-frames.jpg) shows originals on the left of each pair and proposals on the right. The lightbox walls are removed in this sample. Pale/clear edges and tiny printed logos still need the owner's full-size visual approval; no processed proposal has been published.

No checkout/payment/ACS work starts at this handoff.
