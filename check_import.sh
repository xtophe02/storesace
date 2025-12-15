#!/bin/bash
# Check import progress

echo "=== StoreSace Import Progress ==="
echo ""

# Get current count
CURRENT=$(docker exec storesace_db psql -U storesace -d storesace -t -A -c "SET search_path TO prod_515383678; SELECT COUNT(*) FROM da_items_stores_date;" | tail -1)

# Get date range
RANGE=$(docker exec storesace_db psql -U storesace -d storesace -t -A -c "SET search_path TO prod_515383678; SELECT MIN(date) || ' → ' || MAX(date) FROM da_items_stores_date;" | tail -1)

echo "Current rows: $(printf "%'d" $CURRENT)"
echo "Date range:   $RANGE"
echo ""

# Estimate total (rough estimate based on avg rows per month)
ESTIMATED_TOTAL=2500000
PERCENT=$((CURRENT * 100 / ESTIMATED_TOTAL))

echo "Progress: ~${PERCENT}%"
echo ""

# Check if import still running
if ps aux | grep -q "[p]ython3 import_complete.py"; then
    echo "Status: ✅ Import running"
else
    echo "Status: ⏸️  Import completed or stopped"
fi
