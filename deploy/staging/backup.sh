#!/usr/bin/env bash
set -euo pipefail

# Run on the staging host with .env beside compose.yaml. Never put archives in Git.
cd "$(dirname "$0")"
umask 077
backup_dir="${1:?usage: backup.sh /absolute/private/backup-directory}"
mkdir -p "$backup_dir"
backup_dir="$(realpath "$backup_dir")"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
docker compose --env-file .env exec -T postgres pg_dump -U orama -d orama -Fc > "$backup_dir/catalog-$stamp.dump"
docker compose --env-file .env run --rm -v "$backup_dir:/backup" --entrypoint /bin/sh bucket -c \
  'mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" && mc mirror local/orama-private /backup/objects'
echo "Backup saved: $backup_dir/catalog-$stamp.dump and $backup_dir/objects"
echo "Copy these to encrypted off-host storage and regularly rehearse a restore."
