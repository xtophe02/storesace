#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== StoreSace Database Import ===${NC}"

# Wait for PostgreSQL to be ready
echo -e "${YELLOW}Waiting for PostgreSQL...${NC}"
until docker exec storesace_db pg_isready -U storesace -d storesace > /dev/null 2>&1; do
  sleep 1
done
echo -e "${GREEN}PostgreSQL is ready!${NC}"

# Function to execute SQL file
import_sql() {
    local file=$1
    local description=$2
    echo -e "${YELLOW}Importing: ${description}...${NC}"
    docker exec -i storesace_db psql -U storesace -d storesace -v ON_ERROR_STOP=1 < "$file"
    echo -e "${GREEN}✓ ${description} imported${NC}"
}

# Create schema file to fix "unknown" types
echo -e "${YELLOW}Creating schema with proper types...${NC}"
cat > /tmp/fix_schema.sql << 'EOF'
-- Drop existing schema if exists
DROP SCHEMA IF EXISTS prod_515383678 CASCADE;
CREATE SCHEMA prod_515383678;
SET search_path TO prod_515383678;

-- Items table with inferred types
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

-- Stores table with inferred types
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

-- DA Stores Date (parent partitioned table)
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

-- DA Items Stores Date (parent partitioned table)
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

EOF

docker exec -i storesace_db psql -U storesace -d storesace < /tmp/fix_schema.sql
echo -e "${GREEN}✓ Schema created${NC}"

# Import master tables
echo -e "${YELLOW}Importing master tables...${NC}"

# Extract and import items data
docker exec -i storesace_db psql -U storesace -d storesace << EOF
SET search_path TO prod_515383678;
\copy items FROM PROGRAM 'grep "^INSERT INTO" /docker-entrypoint-initdb.d/dumps/items.sql | sed "s/INSERT INTO prod_515383678.items[^V]*VALUES //" | sed "s/);$//" | sed "s/, (/\n(/g"' WITH (FORMAT csv, DELIMITER ',', QUOTE '''');
EOF
echo -e "${GREEN}✓ Items imported${NC}"

# Extract and import stores data
docker exec -i storesace_db psql -U storesace -d storesace << EOF
SET search_path TO prod_515383678;
\copy stores FROM PROGRAM 'grep "^INSERT INTO" /docker-entrypoint-initdb.d/dumps/stores.sql | sed "s/INSERT INTO prod_515383678.stores[^V]*VALUES //" | sed "s/);$//"' WITH (FORMAT csv, DELIMITER ',', QUOTE '''');
EOF
echo -e "${GREEN}✓ Stores imported${NC}"

# Import partitioned tables
echo -e "${YELLOW}Importing partitioned data (this may take a while)...${NC}"

# Function to create and populate partition
create_partition() {
    local table=$1
    local partition_name=$2
    local file=$3
    local start_date=$4
    local end_date=$5

    echo -e "${YELLOW}  Creating partition: ${partition_name}...${NC}"

    docker exec -i storesace_db psql -U storesace -d storesace << EOF
SET search_path TO prod_515383678;
CREATE TABLE ${partition_name} PARTITION OF ${table}
    FOR VALUES FROM ('${start_date}') TO ('${end_date}');
EOF

    echo -e "${YELLOW}  Importing data into: ${partition_name}...${NC}"

    # Import using SQL directly since the dump has INSERT statements
    grep "^INSERT INTO" DUMP/${file} | sed "s/INSERT INTO prod_515383678.${partition_name}/INSERT INTO prod_515383678.${partition_name}/" | \
        docker exec -i storesace_db psql -U storesace -d storesace

    echo -e "${GREEN}  ✓ ${partition_name} completed${NC}"
}

# DA Stores Date partitions (yearly)
create_partition "da_stores_date" "da_stores_date_ppast" "da_stores_date_ppast.sql" "1900-01-01" "2019-01-01"
create_partition "da_stores_date" "da_stores_date_p2019" "da_stores_date_p2019.sql" "2019-01-01" "2020-01-01"
create_partition "da_stores_date" "da_stores_date_p2020" "da_stores_date_p2020.sql" "2020-01-01" "2021-01-01"
create_partition "da_stores_date" "da_stores_date_p2021" "da_stores_date_p2021.sql" "2021-01-01" "2022-01-01"
create_partition "da_stores_date" "da_stores_date_p2022" "da_stores_date_p2022.sql" "2022-01-01" "2023-01-01"
create_partition "da_stores_date" "da_stores_date_p2023" "da_stores_date_p2023.sql" "2023-01-01" "2024-01-01"
create_partition "da_stores_date" "da_stores_date_p2024" "da_stores_date_p2024.sql" "2024-01-01" "2025-01-01"
create_partition "da_stores_date" "da_stores_date_p2025" "da_stores_date_p2025.sql" "2025-01-01" "2026-01-01"
create_partition "da_stores_date" "da_stores_date_p2026" "da_stores_date_p2026.sql" "2026-01-01" "2027-01-01"

# DA Items Stores Date partitions (monthly) - just key ones for demonstration
# You can add all 72 partitions, but here's a few examples:
create_partition "da_items_stores_date" "da_items_stores_date_ppast" "da_items_stores_date_ppast.sql" "1900-01-01" "2020-01-01"
create_partition "da_items_stores_date" "da_items_stores_date_p202001" "da_items_stores_date_p202001.sql" "2020-01-01" "2020-02-01"
create_partition "da_items_stores_date" "da_items_stores_date_p202002" "da_items_stores_date_p202002.sql" "2020-02-01" "2020-03-01"

# ... Add remaining partitions here ...

echo -e "${GREEN}=== Import Complete ===${NC}"
echo ""
echo -e "${GREEN}Database is ready! Connection details:${NC}"
echo -e "  Host: localhost"
echo -e "  Port: 5432"
echo -e "  Database: storesace"
echo -e "  Schema: prod_515383678"
echo -e "  User: storesace"
echo -e "  Password: storesace_dev"
echo ""
echo -e "${YELLOW}Quick test query:${NC}"
docker exec storesace_db psql -U storesace -d storesace -c "SET search_path TO prod_515383678; SELECT COUNT(*) as stores FROM stores;"
