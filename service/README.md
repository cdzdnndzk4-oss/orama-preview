# ORAMA catalog service (branch pilot)

This is the next layer for the existing `index.html`, not a replacement design. It is **not deployed**. See `deploy/staging/README.md` for the separate private staging recipe and prerequisites. The GitHub Pages preview remains the old independent prototype until that deployment uses this service. Checkout, real payments, ACS, account creation, domain and Wix are out of scope.

## Architecture and deployment prerequisites

- Same HTTPS origin serves the current storefront, `/admin`, `/api/catalog`, and media. No browser access to PostgreSQL or S3 credentials.
- Durable PostgreSQL (`DATABASE_URL=postgresql+psycopg://...`) stores products, sessions, approval state, availability and image choices. Set up backups and a private network before deployment. A local SQLite file is accepted **only** by the automated test fixture.
- A private S3 compatible bucket (`ORAMA_S3_BUCKET`) stores originals and deterministic processed drafts. The browser can retrieve drafts only after admin login. Published images are served through the service. Use bucket-level encryption, backups and lifecycle rules for superseded objects.
- `ORAMA_PUBLIC_ORIGIN=https://staging.example` sets the origin for the admin's write checks. A reverse proxy must terminate HTTPS, enforce a body size limit, provide logging, and expose only the service. The session cookie is Secure, HttpOnly, SameSite=Strict; CSRF tokens are required for all admin mutations. Passwords use Argon2id and five failed attempts lock a known account for 15 minutes. Provision the first admin interactively, never in Git.
- `/admin` has its own CSP; data APIs refuse unauthenticated requests. New products and batches start unpublished. Product photos and copy cannot publish until selected and verified.

Install `pip install -r service/requirements.txt`, then in a configured production-like environment run `python -m service.manage init`, `python -m service.manage seed`, and `python -m service.manage create-admin`. Start with `uvicorn service.app:app_from_env --factory --host 127.0.0.1 --port 8766` behind the HTTPS proxy. `init` creates schema v1; future schema changes need explicit migrations and a backup, not repeated blind table alterations.

`seed` imports the five approved records by ID and checks all 15 image files before writing. Repeated runs do not overwrite existing edits. The old `audience: γυναικείο` labels are **not** treated as verified; they remain only in the archival source JSON. A description that asserts gender stays pending and is withheld from the public API until explicitly checked along with the audience. Material approvals already recorded in the source remain.

The public catalog queries PostgreSQL for published products with search, filters and pages of 24. The current `index.html` keeps the blue/white design and now calls this API. A product route fetches its own record. The original static GitHub Pages preview cannot call this private API and is intentionally unchanged on `main`.

## Photo workflow

The worker reads source JPEG/PNG pixels, estimates the lightbox background, and creates a 1200×900 #FFFFFF draft with a faint source-derived shadow. It does **not** generate, inpaint, or redraw frames. The original and processed image are stored separately. Uploading a replacement unpublishes the product. The admin compares both and chooses one for each of front / three-quarter / side before publishing.

For volume, prepare a CSV with columns `product_id,view,path`; run `python -m service.batch_photos photos.csv` as a dry run and then `python -m service.batch_photos photos.csv --apply` in the trusted worker. Up to 3,000 rows per manifest can be processed without editing images one by one. Each imported view has **no selected image** (`chosen=None`); all three views must be explicitly approved in the private admin gallery before publication. Click “Σύγκριση σε πλήρη ανάλυση / zoom” for the full original and processed files, then select the preferred version per view. Rejected photos remain untouched and are reported for manual handling. Batch retries overwrite only the specified product/view and preserve other views.

## Still unverified or pending

No PostgreSQL instance, private S3 bucket, HTTPS hosting or staging URL was supplied in this phase, so remote persistence and deployment cannot be claimed as verified. No checkout, gateway, stock reservation, ACS, production domain, legal review or cookie consent is implemented. Before launch: verify deployment, accessibility and responsive UI on real desktop/mobile browsers; inspect all photo previews (especially pale or rimless frames); review GDPR/cookies/returns/legal copy; add the agreed muted 12–18-second ORAMA video. Production merge requires the owner's separate decision at the requested handoff.
