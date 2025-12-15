#!/bin/bash
# Quick query helper for StoreSace database

QUERY="$1"

if [ -z "$QUERY" ]; then
    echo "Usage: ./query.sh \"SELECT * FROM stores LIMIT 5;\""
    echo ""
    echo "Common queries:"
    echo "  ./query.sh \"SELECT name FROM stores;\""
    echo "  ./query.sh \"SELECT COUNT(*) FROM items;\""
    echo "  ./query.sh \"SELECT * FROM da_stores_date ORDER BY date DESC LIMIT 10;\""
    exit 1
fi

docker exec -i storesace_db psql -U storesace -d storesace << EOF
SET search_path TO prod_515383678;
$QUERY
EOF
