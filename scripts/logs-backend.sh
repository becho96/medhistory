#!/bin/bash
# Просмотр логов backend (использует .env.local как deploy)
cd "$(dirname "$0")/.."
docker compose -p medhistory --env-file .env.local logs backend --tail 200 "$@"
