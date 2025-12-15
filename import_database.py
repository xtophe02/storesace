#!/usr/bin/env python3
"""
StoreSace Database Import Script
Imports PostgreSQL dumps with proper schema handling and partition support
"""

import os
import re
import subprocess
import time
from pathlib import Path

# Configuration
DB_CONTAINER = "storesace_db"
DB_NAME = "storesace"
DB_USER = "storesace"
DB_SCHEMA = "prod_515383678"
DUMP_DIR = Path("./DUMP")

# Colors for terminal output
class Colors:
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'  # No Color

def log(message, color=Colors.GREEN):
    print(f"{color}{message}{Colors.NC}")

def exec_sql(sql, description=""):
    """Execute SQL command in PostgreSQL container"""
    if description:
        log(f"  {description}...", Colors.YELLOW)

    cmd = [
        "docker", "exec", "-i", DB_CONTAINER,
        "psql", "-U", DB_USER, "-d", DB_NAME,
        "-v", "ON_ERROR_STOP=1"
    ]

    result = subprocess.run(
        cmd,
        input=sql.encode(),
        capture_output=True
    )

    if result.returncode != 0:
        log(f"ERROR: {result.stderr.decode()}", Colors.RED)
        raise Exception(f"SQL execution failed: {description}")

    if description:
        log(f"  ✓ {description}", Colors.GREEN)

    return result.stdout.decode()

def wait_for_postgres():
    """Wait for PostgreSQL to be ready"""
    log("Waiting for PostgreSQL...", Colors.YELLOW)
    max_attempts = 30
    for i in range(max_attempts):
        result = subprocess.run(
            ["docker", "exec", DB_CONTAINER, "pg_isready", "-U", DB_USER, "-d", DB_NAME],
            capture_output=True
        )
        if result.returncode == 0:
            log("✓ PostgreSQL is ready!", Colors.GREEN)
            return
        time.sleep(1)
    raise Exception("PostgreSQL failed to start")

def create_schema():
    """Create database schema with proper types"""
    log("\n=== Creating Schema ===", Colors.GREEN)

    schema_sql = f"""
-- Drop and recreate schema
DROP SCHEMA IF EXISTS {DB_SCHEMA} CASCADE;
CREATE SCHEMA {DB_SCHEMA};
SET search_path TO {DB_SCHEMA};

-- Items table
CREATE TABLE items (
    id INTEGER PRIMARY KEY,
    created_date TIMESTAMP WITH TIME ZONE,
    updated_date TIMESTAMP WITH TIME ZONE,
    synccounter INTEGER,
    syncflag INTEGER,
    deleted INTEGER,
    pcode VARCHAR(255),
    description TEXT,
    description_diacritic TEXT,
    name TEXT,
    short_description1 TEXT,
    short_description2 TEXT,
    type INTEGER,
    status INTEGER,
    external_code VARCHAR(255),
    barcode VARCHAR(255),
    barcode_type VARCHAR(10),
    stock_management INTEGER,
    saleprice_management INTEGER,
    saleprice_range VARCHAR(255),
    has_variants INTEGER,
    product_category VARCHAR(10),
    product_type VARCHAR(10),
    accounting_code VARCHAR(255),
    obs TEXT,
    info_ingredients TEXT,
    info_nutrition TEXT,
    long_description TEXT,
    tags TEXT,
    sale_markup NUMERIC(10,5),
    liquid_weight NUMERIC(10,5),
    gross_weight NUMERIC(10,5),
    valid_period INTEGER,
    valid_open INTEGER,
    purchases_exp_date INTEGER,
    sync_status INTEGER,
    accounting_group_id INTEGER,
    created_by_id INTEGER,
    default_tax_type_id INTEGER,
    default_unit_id INTEGER,
    extension_data_id INTEGER,
    family_id INTEGER,
    family_pos_id INTEGER,
    generic_item_id INTEGER,
    group_id INTEGER,
    intrastat_nc_id INTEGER,
    intrastat_region_id INTEGER,
    logistics_unit_id INTEGER,
    origin_country_id INTEGER,
    parent_item_id INTEGER,
    property_id INTEGER,
    purchase_unit_id INTEGER,
    stock_unit_id INTEGER,
    updated_by_id INTEGER,
    loyalty_campaign_id INTEGER,
    exclude_from_sales INTEGER
);

-- Stores table
CREATE TABLE stores (
    id INTEGER PRIMARY KEY,
    created_date TIMESTAMP WITH TIME ZONE,
    updated_date TIMESTAMP WITH TIME ZONE,
    deleted INTEGER,
    name VARCHAR(255),
    code VARCHAR(50),
    external_code VARCHAR(255),
    sector VARCHAR(255),
    accounting_code VARCHAR(255),
    status INTEGER,
    latitude VARCHAR(50),
    longitude VARCHAR(50),
    floor_area NUMERIC(10,2),
    address TEXT,
    postal_code VARCHAR(20),
    location VARCHAR(255),
    inherit_address INTEGER,
    phone VARCHAR(50),
    fax VARCHAR(50),
    mobilephone VARCHAR(50),
    email VARCHAR(255),
    schedule TEXT,
    obs TEXT,
    store_ip VARCHAR(50),
    year_budget NUMERIC(15,2),
    month_budget NUMERIC(15,2),
    sales_prices_ranges VARCHAR(10),
    pos_sw_type VARCHAR(50),
    sync_enabled INTEGER,
    sync_enabled_date TIMESTAMP WITH TIME ZONE,
    sync_disabled_date TIMESTAMP WITH TIME ZONE,
    sync_conf_op VARCHAR(255),
    contacts_responsible TEXT,
    clapp_available INTEGER,
    email_to_display VARCHAR(255),
    contact_to_display VARCHAR(255),
    suppliers_channels TEXT,
    company_id INTEGER,
    country_id INTEGER,
    created_by_id INTEGER,
    extension_data_id INTEGER,
    intrastat_region_id INTEGER,
    language_id INTEGER,
    location_repository_document_id INTEGER,
    repository_document_id INTEGER,
    sale_struct_id INTEGER,
    tax_region_id INTEGER,
    type_id INTEGER,
    updated_by_id INTEGER,
    timezone VARCHAR(100),
    online_store_config TEXT,
    work_time_periods JSONB,
    sales_or_persons_per_employee INTEGER
);

-- DA Stores Date (partitioned by year)
CREATE TABLE da_stores_date (
    store_id INTEGER,
    date DATE,
    last_sale TIMESTAMP WITH TIME ZONE,
    nr_sales INTEGER,
    nr_persons INTEGER,
    total_quantity NUMERIC(15,5),
    total_net NUMERIC(15,5),
    total_doc NUMERIC(15,5),
    nr_credits INTEGER,
    credits_total_quantity NUMERIC(15,5),
    credits_total_net NUMERIC(15,5),
    credits_total_doc NUMERIC(15,5),
    waste_total_net NUMERIC(15,5),
    unknown_break_total_net NUMERIC(15,5),
    acc_expenses_total_net NUMERIC(15,5),
    acc_credits_total_net NUMERIC(15,5),
    total_doc_excluded NUMERIC(15,5),
    total_net_excluded NUMERIC(15,5),
    total_discount NUMERIC(15,5),
    PRIMARY KEY (store_id, date)
) PARTITION BY RANGE (date);

-- DA Items Stores Date (partitioned by month)
CREATE TABLE da_items_stores_date (
    item_id INTEGER,
    date DATE,
    total_quantity NUMERIC(15,5),
    total_net NUMERIC(15,5),
    total_price NUMERIC(15,5),
    self_expenditure_total_quantity NUMERIC(15,5),
    latest_price_cost NUMERIC(15,5),
    price_average_cost NUMERIC(15,5),
    store_id INTEGER,
    total_discount NUMERIC(15,5),
    PRIMARY KEY (item_id, store_id, date)
) PARTITION BY RANGE (date);

-- Create indexes
CREATE INDEX idx_stores_name ON stores(name);
CREATE INDEX idx_stores_code ON stores(code);
CREATE INDEX idx_items_pcode ON items(pcode);
CREATE INDEX idx_items_description ON items(description);
"""

    exec_sql(schema_sql, "Schema creation")

def import_table_from_file(file_path, table_name):
    """Import data from SQL dump file"""
    log(f"\n=== Importing {table_name} ===", Colors.GREEN)

    if not file_path.exists():
        log(f"WARNING: File not found: {file_path}", Colors.YELLOW)
        return

    # Read and process the SQL file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract INSERT statements and modify them
    inserts = re.findall(r'INSERT INTO [^;]+;', content, re.DOTALL)

    if not inserts:
        log(f"WARNING: No INSERT statements found in {file_path}", Colors.YELLOW)
        return

    log(f"  Found {len(inserts)} INSERT statements", Colors.YELLOW)

    # Execute inserts in batches
    batch_size = 1000
    for i in range(0, len(inserts), batch_size):
        batch = inserts[i:i + batch_size]
        sql = f"SET search_path TO {DB_SCHEMA};\n" + "\n".join(batch)
        exec_sql(sql, f"Batch {i//batch_size + 1} ({min(i+batch_size, len(inserts))}/{len(inserts)})")

def create_and_import_partition(parent_table, partition_name, start_date, end_date, file_name):
    """Create partition and import data"""
    log(f"  Partition: {partition_name}", Colors.YELLOW)

    # Create partition
    partition_sql = f"""
SET search_path TO {DB_SCHEMA};
CREATE TABLE {partition_name} PARTITION OF {parent_table}
    FOR VALUES FROM ('{start_date}') TO ('{end_date}');
"""
    exec_sql(partition_sql, f"Created {partition_name}")

    # Import data if file exists
    file_path = DUMP_DIR / file_name
    if file_path.exists():
        import_table_from_file(file_path, partition_name)
    else:
        log(f"    WARNING: Partition file not found: {file_name}", Colors.YELLOW)

def create_partitions():
    """Create all partitions for fact tables"""
    log("\n=== Creating Partitions ===", Colors.GREEN)

    # DA Stores Date partitions (yearly)
    log("\nDA Stores Date Partitions:", Colors.GREEN)
    yearly_partitions = [
        ("da_stores_date_ppast", "1900-01-01", "2019-01-01", "da_stores_date_ppast.sql"),
        ("da_stores_date_p2019", "2019-01-01", "2020-01-01", "da_stores_date_p2019.sql"),
        ("da_stores_date_p2020", "2020-01-01", "2021-01-01", "da_stores_date_p2020.sql"),
        ("da_stores_date_p2021", "2021-01-01", "2022-01-01", "da_stores_date_p2021.sql"),
        ("da_stores_date_p2022", "2022-01-01", "2023-01-01", "da_stores_date_p2022.sql"),
        ("da_stores_date_p2023", "2023-01-01", "2024-01-01", "da_stores_date_p2023.sql"),
        ("da_stores_date_p2024", "2024-01-01", "2025-01-01", "da_stores_date_p2024.sql"),
        ("da_stores_date_p2025", "2025-01-01", "2026-01-01", "da_stores_date_p2025.sql"),
        ("da_stores_date_p2026", "2026-01-01", "2027-01-01", "da_stores_date_p2026.sql"),
    ]

    for part_name, start, end, filename in yearly_partitions:
        create_and_import_partition("da_stores_date", part_name, start, end, filename)

    # DA Items Stores Date partitions (monthly)
    log("\nDA Items Stores Date Partitions:", Colors.GREEN)

    # Generate all monthly partitions from 2020-01 to 2026-12
    monthly_partitions = []

    # Past partition
    monthly_partitions.append(("da_items_stores_date_ppast", "1900-01-01", "2020-01-01", "da_items_stores_date_ppast.sql"))

    # Monthly partitions
    for year in range(2020, 2027):
        for month in range(1, 13):
            if year == 2026 and month > 12:  # Stop at 2026-12
                break

            part_name = f"da_items_stores_date_p{year}{month:02d}"
            start_date = f"{year}-{month:02d}-01"

            # Calculate end date (first day of next month)
            if month == 12:
                end_date = f"{year + 1}-01-01"
            else:
                end_date = f"{year}-{month + 1:02d}-01"

            filename = f"{part_name}.sql"
            monthly_partitions.append((part_name, start_date, end_date, filename))

    for part_name, start, end, filename in monthly_partitions:
        create_and_import_partition("da_items_stores_date", part_name, start, end, filename)

def verify_import():
    """Verify the import was successful"""
    log("\n=== Verification ===", Colors.GREEN)

    queries = [
        ("Stores count", f"SET search_path TO {DB_SCHEMA}; SELECT COUNT(*) FROM stores;"),
        ("Items count", f"SET search_path TO {DB_SCHEMA}; SELECT COUNT(*) FROM items;"),
        ("Sales data (da_stores_date)", f"SET search_path TO {DB_SCHEMA}; SELECT COUNT(*) FROM da_stores_date;"),
        ("Item sales data (da_items_stores_date)", f"SET search_path TO {DB_SCHEMA}; SELECT COUNT(*) FROM da_items_stores_date;"),
        ("Stores list", f"SET search_path TO {DB_SCHEMA}; SELECT id, name, code FROM stores ORDER BY id;"),
    ]

    for desc, query in queries:
        log(f"\n{desc}:", Colors.YELLOW)
        result = exec_sql(query, "")
        print(result)

def main():
    """Main import process"""
    log("\n" + "="*50, Colors.GREEN)
    log("StoreSace Database Import", Colors.GREEN)
    log("="*50, Colors.GREEN)

    try:
        # Wait for database
        wait_for_postgres()

        # Create schema
        create_schema()

        # Import master tables
        import_table_from_file(DUMP_DIR / "stores.sql", "stores")
        import_table_from_file(DUMP_DIR / "items.sql", "items")

        # Create and import partitions
        create_partitions()

        # Verify
        verify_import()

        log("\n" + "="*50, Colors.GREEN)
        log("✓ Import completed successfully!", Colors.GREEN)
        log("="*50, Colors.GREEN)

        log("\nConnection details:", Colors.YELLOW)
        log(f"  Host: localhost", Colors.NC)
        log(f"  Port: 5432", Colors.NC)
        log(f"  Database: {DB_NAME}", Colors.NC)
        log(f"  Schema: {DB_SCHEMA}", Colors.NC)
        log(f"  User: {DB_USER}", Colors.NC)
        log(f"  Password: storesace_dev", Colors.NC)

    except Exception as e:
        log(f"\n✗ Import failed: {str(e)}", Colors.RED)
        raise

if __name__ == "__main__":
    main()
