# Admin/catalog correction checkpoint — 2026-09-26

Base: published `production/admin-catalog-v1` commit `49ccfafc66ce53826f30fbc8ed54835d5c07fd20`. Do not merge until owner review. No payments, ACS, live domain, or Wix changes.

## Corrected

- Batch import now writes `chosen=None` for every view, including replacements, and unpublishes the product. Once any new photo is present, publication requires **three explicitly chosen** views. Original/processed endpoints remain admin-only; public media returns 404 until approval and publication.
- Processing uses actual source RGB at detected frame pixels and keeps only source-derived soft contact shadows near the detected subject. The canvas corners are #FFFFFF; no model reconstructs an object. Gold/pale edges have more contrast than v1; all nine proposals still require human acceptance. The original files remain intact.
- The private admin UI compares full-resolution original/processed images in a scrollable zoom dialog with one explicit choice per view. A separate offline pilot ZIP contains nine untouched originals, nine 1200×900 processed proposals and a review HTML with zoom/notes; the ZIP is shared privately and is **not** committed to the public Git repo. Offline notes do not publish images.
- Demo cart stores IDs independently of the current 24-item page and retrieves missing products from `/api/catalog/{id}`. A missing/unpublished item is shown for removal rather than silently dropped. The storefront reads both `availability` store counts separately.
- A GitHub Actions workflow runs Python tests and Node storefront/admin syntax and regression checks on branch pushes and PRs. A real GitHub run requires the corrected branch commit to be pushed.
- A standalone private staging recipe is in `deploy/staging`; it requires a host and non-live staging hostname. Nothing has been deployed by this commit.

## Local evidence and remaining verification

`python -m pytest -q tests` passes 8 tests with a third-party Starlette/httpx deprecation warning. `node tests/storefront.cjs` passes storefront JS syntax, admin JS syntax, cart/page transition and two-store count checks. Photo CI tests use a synthetic lightbox, while the separate nine-image pilot uses the real supplied JPEGs. `git diff --check` is clean.

The pilot's full-resolution images were generated and three representative views were visually inspected locally. Some soft edge halos and lens reflections remain visible; owner must inspect all nine at full size. Browser QA on real desktop/mobile, remote Postgres/S3 integration, container config, backup and restore, HTTPS and restart persistence still require installed staging. The available Vercel account inventory did not expose a team, and this workspace has no host, DNS staging hostname, Docker daemon, PostgreSQL service or S3 credentials. Do not report a staging URL or CI success before they exist.
