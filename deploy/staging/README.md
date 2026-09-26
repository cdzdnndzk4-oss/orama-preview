# Private staging deployment (not yet installed)

This directory is a deployment recipe for a **separate staging host**, not the live domain. It starts PostgreSQL, a private S3-compatible MinIO bucket, the existing FastAPI service, and a TLS reverse proxy with an additional site password. PostgreSQL/MinIO are not exposed through host ports. HTTPS requires a staging hostname under the owner's control pointing to the host; `oramaoptical.gr` is not used or changed.

## Prerequisites and setup

1. Supply a separate VPS with Docker Compose, a staging hostname, firewall allowing 80/443 and restricted SSH, and encrypted off-host backup storage. Do not expose database or object-storage ports. Inspect and pin container image digests before deploying; the included MinIO and Caddy tags are not immutable.
2. On the host, copy `.env.example` to `.env`, set permissions to 600, generate distinct long random secrets, and URL-encode the database password in `DATABASE_URL`. Hash a separate site password using `docker run --rm -it caddy:2.10 caddy hash-password` and put the result in `STAGING_BASIC_HASH` **inside single quotes** so Compose does not interpolate its `$` characters. Keep `.env` outside Git and secret managers' access controlled. The Basic password and the admin password must be different.
3. From `deploy/staging`, validate `docker compose --env-file .env config` locally without pasting the output (it contains secrets). Run `docker compose --env-file .env up -d --build`, then `docker compose --env-file .env exec app python -m service.manage init` and `docker compose --env-file .env exec app python -m service.manage seed`. The seed imports the five approved products with the existing 15 files. Create the first admin using an interactive terminal: `docker compose --env-file .env exec app python -m service.manage create-admin --email YOUR_EMAIL`. The password is entered at the prompt and is never committed.
4. Verify the private URL over HTTPS. Basic authentication protects the whole staging site, and `/admin` additionally requires its own account. The actual host and password must be conveyed privately to the owner. Do not create public bypass links.

## Backups and restore

Set up daily `backup.sh /private/backups` on the host. It writes a PostgreSQL custom-format dump and mirrors private objects. Transfer each set to encrypted **off-host** storage with a retention policy and access separate from the staging server; a copy on the same server is not a complete backup. The MinIO bucket is versioned. Before every schema change, take a backup and test restoring into an isolated staging clone: `pg_restore --clean --if-exists -U orama -d orama catalog.dump`, restore the mirrored object keys to the private bucket, and verify the five catalog IDs, all 15 legacy assets and an uploaded draft. Record the restore drill and monitor failures. The backup script and restore have **not** run against a real host yet.

## Acceptance tests on the installed URL

- Basic gate and admin login/logout, session expiry, CSRF and cross-origin write rejection.
- Restart all containers and verify persisted product, stock in each store, pending approvals and original/processed private media.
- Upload front / three-quarter / side, compare full size, select one per view; verify publish fails until all three are explicitly chosen, and unpublish removes it from public API and media.
- Import 550 staging records, verify 24 per page, search, cart page navigation, mobile and desktop browser views. Remove synthetic records after verification.
- Run `backup.sh`, restore into an isolated clone, verify counts and objects. Do not use actual customer data.

This is **not** evidence of a live staging service. It still requires host access, a staging hostname, secret provisioning, backup target and actual end-to-end QA.
