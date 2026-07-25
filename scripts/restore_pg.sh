#!/usr/bin/env sh
set -eu

# Restore LottoPilot PostgreSQL dump created by backup_pg.sh.
# Usage:
#   ./scripts/restore_pg.sh ./backups/lottopilot_YYYYMMDD_HHMMSS.sql.gz
# WARNING: overwrites current database contents.

DUMP=${1:-}
if [ -z "$DUMP" ] || [ ! -f "$DUMP" ]; then
  echo "usage: $0 <backup.sql.gz>" >&2
  exit 1
fi

echo "[restore] restoring from $DUMP"
gzip -dc "$DUMP" | docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
echo "[restore] done"
