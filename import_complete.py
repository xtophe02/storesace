#!/usr/bin/env python3
"""
Complete data import - imports ALL 85 partitions
Run this to get full 2020-2026 data
"""

import subprocess
import sys
from pathlib import Path

DB_CONTAINER = "storesace_db"
DB_NAME = "storesace"
DB_USER = "storesace"
DB_SCHEMA = "prod_515383678"
DUMP_DIR = Path("./DUMP")

def exec_sql(sql):
    """Execute SQL in container"""
    cmd = ["docker", "exec", "-i", DB_CONTAINER, "psql", "-U", DB_USER, "-d", DB_NAME]
    result = subprocess.run(cmd, input=sql.encode(), capture_output=True)
    if result.returncode != 0:
        print(f"ERROR: {result.stderr.decode()}")
        return False
    return True

def import_partition(table, partition_name, start_date, end_date, sql_file):
    """Create partition and import data"""
    print(f"  Creating {partition_name}...")

    # Create partition
    create_sql = f"""
    SET search_path TO {DB_SCHEMA};
    CREATE TABLE IF NOT EXISTS {partition_name} PARTITION OF {table}
        FOR VALUES FROM ('{start_date}') TO ('{end_date}');
    """

    if not exec_sql(create_sql):
        print(f"    Failed to create partition {partition_name}")
        return False

    # Import data if file exists
    file_path = DUMP_DIR / sql_file
    if not file_path.exists():
        print(f"    WARNING: File not found: {sql_file}")
        return True

    print(f"  Importing data from {sql_file}...")

    # Read INSERT statements and execute
    with open(file_path, 'r') as f:
        content = f.read()

    # Extract INSERT statements
    import re
    inserts = re.findall(r'INSERT INTO [^;]+;', content, re.DOTALL)

    if not inserts:
        print(f"    No data in {sql_file}")
        return True

    # Execute in batches
    batch_size = 1000
    total = len(inserts)
    print(f"    Found {total} INSERT statements")

    for i in range(0, total, batch_size):
        batch = inserts[i:i + batch_size]
        sql = f"SET search_path TO {DB_SCHEMA};\n" + "\n".join(batch)
        if not exec_sql(sql):
            print(f"    Failed at batch {i//batch_size + 1}")
            return False
        print(f"    Batch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}")

    print(f"  ✓ {partition_name} complete")
    return True

def main():
    print("="*60)
    print("StoreSace - Complete Data Import")
    print("="*60)

    # Check if partitions already exist
    check_sql = f"SET search_path TO {DB_SCHEMA}; SELECT COUNT(*) FROM da_items_stores_date;"

    print("\nChecking current data...")
    result = subprocess.run(
        ["docker", "exec", "-i", DB_CONTAINER, "psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-A", "-c", check_sql],
        capture_output=True
    )
    # Parse output - skip "SET" line, get the count
    output = result.stdout.decode().strip()
    current_rows = int(output.split('\n')[-1])
    print(f"Current rows in da_items_stores_date: {current_rows}")

    # DA Items Stores Date - Monthly partitions (2020-2026)
    print("\n" + "="*60)
    print("Importing DA Items Stores Date (monthly partitions)")
    print("="*60)

    partitions = []

    # Generate all monthly partitions
    for year in range(2020, 2027):
        for month in range(1, 13):
            if year == 2020 and month < 8:  # Data starts Aug 2020
                continue
            if year == 2026 and month > 12:  # Stop at Dec 2026
                continue

            part_name = f"da_items_stores_date_p{year}{month:02d}"
            start_date = f"{year}-{month:02d}-01"

            # Calculate end date
            if month == 12:
                end_date = f"{year + 1}-01-01"
            else:
                end_date = f"{year}-{month + 1:02d}-01"

            filename = f"{part_name}.sql"
            partitions.append((part_name, start_date, end_date, filename))

    total_partitions = len(partitions)
    print(f"\nTotal partitions to import: {total_partitions}")

    success_count = 0
    for i, (part_name, start, end, filename) in enumerate(partitions, 1):
        print(f"\n[{i}/{total_partitions}] Processing {part_name}")
        if import_partition("da_items_stores_date", part_name, start, end, filename):
            success_count += 1
        else:
            print(f"  ✗ Failed: {part_name}")

    # Final verification
    print("\n" + "="*60)
    print("Verification")
    print("="*60)

    result = subprocess.run(
        ["docker", "exec", "-i", DB_CONTAINER, "psql", "-U", DB_USER, "-d", DB_NAME, "-t", "-A", "-c", check_sql],
        capture_output=True
    )
    output = result.stdout.decode().strip()
    final_rows = int(output.split('\n')[-1])

    print(f"Initial rows: {current_rows:,}")
    print(f"Final rows:   {final_rows:,}")
    print(f"Imported:     {final_rows - current_rows:,} new rows")
    print(f"Partitions:   {success_count}/{total_partitions} successful")

    # Show date range
    range_sql = f"""
    SET search_path TO {DB_SCHEMA};
    SELECT MIN(date) as first_date, MAX(date) as last_date, COUNT(*) as total_rows
    FROM da_items_stores_date;
    """

    print("\nData coverage:")
    subprocess.run(
        ["docker", "exec", "-i", DB_CONTAINER, "psql", "-U", DB_USER, "-d", DB_NAME, "-c", range_sql],
    )

    print("\n" + "="*60)
    print("✓ Import complete!")
    print("="*60)

if __name__ == "__main__":
    main()
