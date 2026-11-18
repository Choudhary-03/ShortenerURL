#!/bin/sh
# Back up the PostgreSQL database to backups/*.sql.gz
# Run from the project root on the server:  sh scripts/backup_db.sh
set -e
mkdir -p backups
FILE="backups/shortener_$(date +%Y%m%d_%H%M%S).sql.gz"
docker compose -f deployment/docker-compose.yml --env-file .env exec -T db \
  sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$FILE"
echo "Saved $FILE"
