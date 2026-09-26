# ORAMA local development

This folder is for running the ORAMA catalog/admin locally on one Windows computer with Docker Desktop.

It deliberately does **not** use MinIO, Caddy, a public hostname, TLS, or the staging secrets. Those remain in `deploy/staging` for a future real staging server.

## Start

From the repository root:

```cmd
docker compose -f deploy\local\compose.yaml up -d --build
```

Then open:

- Storefront: http://localhost:8766
- Admin: http://localhost:8766/admin

Local admin defaults:

- Email: `local@orama.test`
- Password: `OramaLocalAdmin2026!`

The port is bound to `127.0.0.1`, so this local instance is not exposed to other computers on the network.

## Stop

```cmd
docker compose -f deploy\local\compose.yaml down
```

Database and uploaded local photos persist in Docker volumes. To completely reset only the local data:

```cmd
docker compose -f deploy\local\compose.yaml down -v
```

Do not use this local recipe for public/staging/production deployment.
