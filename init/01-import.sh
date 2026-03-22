#!/bin/bash
set -e

# StoreSace: Data import (runs once on first docker compose up)
# Loads data from SQL dump files into the schema created by 00-schema.sql

DUMP_DIR="/dumps"
PSQL="psql -q -v ON_ERROR_STOP=1 --username $POSTGRES_USER --dbname $POSTGRES_DB"

echo "=== StoreSace: Importing data ==="

# Performance tuning for bulk import
$PSQL <<EOF
ALTER SYSTEM SET synchronous_commit = off;
ALTER SYSTEM SET full_page_writes = off;
ALTER SYSTEM SET max_wal_size = '2GB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
SELECT pg_reload_conf();
EOF
echo "Performance tuning applied"

# Import master tables (skip CREATE TABLE lines with 'unknown' types)
for table in stores items; do
    echo "Importing ${table}..."
    (echo "BEGIN;"; sed -n '/^INSERT/,$p' "${DUMP_DIR}/${table}.sql"; echo "COMMIT;") | $PSQL
    echo "Done: ${table}"
done

# Import da_stores_date partitions (yearly)
echo ""
echo "=== Importing store daily aggregates ==="
for file in "${DUMP_DIR}"/da_stores_date_p*.sql; do
    name=$(basename "$file" .sql)
    echo "Importing ${name}..."
    (echo "BEGIN;"; sed -n '/^INSERT/,$p' "$file"; echo "COMMIT;") | $PSQL
    echo "Done: ${name}"
done

# Import da_items_stores_date partitions (monthly - ~6.7M rows)
echo ""
echo "=== Importing item-store daily aggregates ==="
count=0
total=$(ls -1 "${DUMP_DIR}"/da_items_stores_date_p*.sql 2>/dev/null | wc -l)
for file in "${DUMP_DIR}"/da_items_stores_date_p*.sql; do
    count=$((count + 1))
    name=$(basename "$file" .sql)
    echo "Importing ${name} (${count}/${total})..."
    (echo "BEGIN;"; sed -n '/^INSERT/,$p' "$file"; echo "COMMIT;") | $PSQL
    echo "Done: ${name}"
done

# Restore safe defaults
$PSQL <<EOF
ALTER SYSTEM SET synchronous_commit = on;
ALTER SYSTEM SET full_page_writes = on;
SELECT pg_reload_conf();
EOF
echo "Safe defaults restored"

# Quick verification
echo ""
echo "=== Verification ==="
$PSQL -t <<EOF
SET search_path TO prod_515383678;
SELECT 'stores: ' || COUNT(*) FROM stores
UNION ALL
SELECT 'items: ' || COUNT(*) FROM items
UNION ALL
SELECT 'da_stores_date: ' || COUNT(*) FROM da_stores_date
UNION ALL
SELECT 'da_items_stores_date: ' || COUNT(*) FROM da_items_stores_date;
EOF

echo ""
echo "=== StoreSace: Import complete! ==="
