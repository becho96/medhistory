#!/usr/bin/env bash
#
# Apply pending SQL migrations, tracking applied ones in the schema_migrations
# table. Each NNN_*.sql file is applied at most once, in numeric order.
#
# Usage:
#   PSQL="docker exec -i medhistory-postgres-1 psql -U medhistory_user medhistory" \
#     bash backend/migrations/apply.sh
#
# PSQL defaults to a bare `psql` (expects PG* env vars / a reachable server).
#
set -euo pipefail

MIGRATIONS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PSQL="${PSQL:-psql}"

run_sql() { $PSQL -v ON_ERROR_STOP=1 -tA "$@"; }

# Ledger table — created once, harmless if it already exists.
run_sql -c "CREATE TABLE IF NOT EXISTS schema_migrations (
  version    TEXT PRIMARY KEY,
  applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);"

applied=0
for file in "$MIGRATIONS_DIR"/[0-9]*.sql; do
  version="$(basename "$file")"
  if [ -n "$(run_sql -c "SELECT 1 FROM schema_migrations WHERE version = '$version';")" ]; then
    continue
  fi
  echo "→ applying $version"
  run_sql < "$file"
  run_sql -c "INSERT INTO schema_migrations (version) VALUES ('$version');"
  applied=$((applied + 1))
done

if [ "$applied" -eq 0 ]; then
  echo "✓ no pending migrations"
else
  echo "✓ applied $applied migration(s)"
fi
