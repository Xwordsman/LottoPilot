#!/usr/bin/env sh
set -eu

# Backup LottoPilot PostgreSQL from docker compose service.
# Usage:
#   ./scripts/backup_pg.sh [output_dir]
# Example:
#   ./scripts/backup_pg.sh ./backups

OUT_DIR=${1:-./backups}
STAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$OUT_DIR"
FILE="$OUT_DIR/lottopilot_${STAMP}.sql.gz"

echo "[backup] writing $FILE"
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB"' | gzip > "$FILE"
echo "[backup] done: $FILE"
