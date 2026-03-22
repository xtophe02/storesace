-- StoreSace: Schema creation (runs once on first docker compose up)
-- Creates schema, tables with proper types, partitions, and indexes

-- Schema
DROP SCHEMA IF EXISTS prod_515383678 CASCADE;
CREATE SCHEMA prod_515383678;
SET search_path TO prod_515383678;

-- ============================================================
-- Master tables
-- ============================================================

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
    floor_area NUMERIC(10,3),
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

-- ============================================================
-- Partitioned fact tables
-- ============================================================

-- Daily store aggregates (partitioned by year)
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

-- Yearly partitions for da_stores_date
CREATE TABLE da_stores_date_ppast PARTITION OF da_stores_date FOR VALUES FROM (MINVALUE) TO ('2019-01-01');
CREATE TABLE da_stores_date_p2019 PARTITION OF da_stores_date FOR VALUES FROM ('2019-01-01') TO ('2020-01-01');
CREATE TABLE da_stores_date_p2020 PARTITION OF da_stores_date FOR VALUES FROM ('2020-01-01') TO ('2021-01-01');
CREATE TABLE da_stores_date_p2021 PARTITION OF da_stores_date FOR VALUES FROM ('2021-01-01') TO ('2022-01-01');
CREATE TABLE da_stores_date_p2022 PARTITION OF da_stores_date FOR VALUES FROM ('2022-01-01') TO ('2023-01-01');
CREATE TABLE da_stores_date_p2023 PARTITION OF da_stores_date FOR VALUES FROM ('2023-01-01') TO ('2024-01-01');
CREATE TABLE da_stores_date_p2024 PARTITION OF da_stores_date FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
CREATE TABLE da_stores_date_p2025 PARTITION OF da_stores_date FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
CREATE TABLE da_stores_date_p2026 PARTITION OF da_stores_date FOR VALUES FROM ('2026-01-01') TO ('2027-01-01');

-- Daily item-store aggregates (partitioned by month)
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

-- Monthly partitions for da_items_stores_date
CREATE TABLE da_items_stores_date_ppast PARTITION OF da_items_stores_date FOR VALUES FROM (MINVALUE) TO ('2020-01-01');
-- 2020
CREATE TABLE da_items_stores_date_p202001 PARTITION OF da_items_stores_date FOR VALUES FROM ('2020-01-01') TO ('2020-02-01');
CREATE TABLE da_items_stores_date_p202002 PARTITION OF da_items_stores_date FOR VALUES FROM ('2020-02-01') TO ('2020-03-01');
CREATE TABLE da_items_stores_date_p202003 PARTITION OF da_items_stores_date FOR VALUES FROM ('2020-03-01') TO ('2020-04-01');
CREATE TABLE da_items_stores_date_p202004 PARTITION OF da_items_stores_date FOR VALUES FROM ('2020-04-01') TO ('2020-05-01');
CREATE TABLE da_items_stores_date_p202005 PARTITION OF da_items_stores_date FOR VALUES FROM ('2020-05-01') TO ('2020-06-01');
CREATE TABLE da_items_stores_date_p202006 PARTITION OF da_items_stores_date FOR VALUES FROM ('2020-06-01') TO ('2020-07-01');
CREATE TABLE da_items_stores_date_p202007 PARTITION OF da_items_stores_date FOR VALUES FROM ('2020-07-01') TO ('2020-08-01');
CREATE TABLE da_items_stores_date_p202008 PARTITION OF da_items_stores_date FOR VALUES FROM ('2020-08-01') TO ('2020-09-01');
CREATE TABLE da_items_stores_date_p202009 PARTITION OF da_items_stores_date FOR VALUES FROM ('2020-09-01') TO ('2020-10-01');
CREATE TABLE da_items_stores_date_p202010 PARTITION OF da_items_stores_date FOR VALUES FROM ('2020-10-01') TO ('2020-11-01');
CREATE TABLE da_items_stores_date_p202011 PARTITION OF da_items_stores_date FOR VALUES FROM ('2020-11-01') TO ('2020-12-01');
CREATE TABLE da_items_stores_date_p202012 PARTITION OF da_items_stores_date FOR VALUES FROM ('2020-12-01') TO ('2021-01-01');
-- 2021
CREATE TABLE da_items_stores_date_p202101 PARTITION OF da_items_stores_date FOR VALUES FROM ('2021-01-01') TO ('2021-02-01');
CREATE TABLE da_items_stores_date_p202102 PARTITION OF da_items_stores_date FOR VALUES FROM ('2021-02-01') TO ('2021-03-01');
CREATE TABLE da_items_stores_date_p202103 PARTITION OF da_items_stores_date FOR VALUES FROM ('2021-03-01') TO ('2021-04-01');
CREATE TABLE da_items_stores_date_p202104 PARTITION OF da_items_stores_date FOR VALUES FROM ('2021-04-01') TO ('2021-05-01');
CREATE TABLE da_items_stores_date_p202105 PARTITION OF da_items_stores_date FOR VALUES FROM ('2021-05-01') TO ('2021-06-01');
CREATE TABLE da_items_stores_date_p202106 PARTITION OF da_items_stores_date FOR VALUES FROM ('2021-06-01') TO ('2021-07-01');
CREATE TABLE da_items_stores_date_p202107 PARTITION OF da_items_stores_date FOR VALUES FROM ('2021-07-01') TO ('2021-08-01');
CREATE TABLE da_items_stores_date_p202108 PARTITION OF da_items_stores_date FOR VALUES FROM ('2021-08-01') TO ('2021-09-01');
CREATE TABLE da_items_stores_date_p202109 PARTITION OF da_items_stores_date FOR VALUES FROM ('2021-09-01') TO ('2021-10-01');
CREATE TABLE da_items_stores_date_p202110 PARTITION OF da_items_stores_date FOR VALUES FROM ('2021-10-01') TO ('2021-11-01');
CREATE TABLE da_items_stores_date_p202111 PARTITION OF da_items_stores_date FOR VALUES FROM ('2021-11-01') TO ('2021-12-01');
CREATE TABLE da_items_stores_date_p202112 PARTITION OF da_items_stores_date FOR VALUES FROM ('2021-12-01') TO ('2022-01-01');
-- 2022
CREATE TABLE da_items_stores_date_p202201 PARTITION OF da_items_stores_date FOR VALUES FROM ('2022-01-01') TO ('2022-02-01');
CREATE TABLE da_items_stores_date_p202202 PARTITION OF da_items_stores_date FOR VALUES FROM ('2022-02-01') TO ('2022-03-01');
CREATE TABLE da_items_stores_date_p202203 PARTITION OF da_items_stores_date FOR VALUES FROM ('2022-03-01') TO ('2022-04-01');
CREATE TABLE da_items_stores_date_p202204 PARTITION OF da_items_stores_date FOR VALUES FROM ('2022-04-01') TO ('2022-05-01');
CREATE TABLE da_items_stores_date_p202205 PARTITION OF da_items_stores_date FOR VALUES FROM ('2022-05-01') TO ('2022-06-01');
CREATE TABLE da_items_stores_date_p202206 PARTITION OF da_items_stores_date FOR VALUES FROM ('2022-06-01') TO ('2022-07-01');
CREATE TABLE da_items_stores_date_p202207 PARTITION OF da_items_stores_date FOR VALUES FROM ('2022-07-01') TO ('2022-08-01');
CREATE TABLE da_items_stores_date_p202208 PARTITION OF da_items_stores_date FOR VALUES FROM ('2022-08-01') TO ('2022-09-01');
CREATE TABLE da_items_stores_date_p202209 PARTITION OF da_items_stores_date FOR VALUES FROM ('2022-09-01') TO ('2022-10-01');
CREATE TABLE da_items_stores_date_p202210 PARTITION OF da_items_stores_date FOR VALUES FROM ('2022-10-01') TO ('2022-11-01');
CREATE TABLE da_items_stores_date_p202211 PARTITION OF da_items_stores_date FOR VALUES FROM ('2022-11-01') TO ('2022-12-01');
CREATE TABLE da_items_stores_date_p202212 PARTITION OF da_items_stores_date FOR VALUES FROM ('2022-12-01') TO ('2023-01-01');
-- 2023
CREATE TABLE da_items_stores_date_p202301 PARTITION OF da_items_stores_date FOR VALUES FROM ('2023-01-01') TO ('2023-02-01');
CREATE TABLE da_items_stores_date_p202302 PARTITION OF da_items_stores_date FOR VALUES FROM ('2023-02-01') TO ('2023-03-01');
CREATE TABLE da_items_stores_date_p202303 PARTITION OF da_items_stores_date FOR VALUES FROM ('2023-03-01') TO ('2023-04-01');
CREATE TABLE da_items_stores_date_p202304 PARTITION OF da_items_stores_date FOR VALUES FROM ('2023-04-01') TO ('2023-05-01');
CREATE TABLE da_items_stores_date_p202305 PARTITION OF da_items_stores_date FOR VALUES FROM ('2023-05-01') TO ('2023-06-01');
CREATE TABLE da_items_stores_date_p202306 PARTITION OF da_items_stores_date FOR VALUES FROM ('2023-06-01') TO ('2023-07-01');
CREATE TABLE da_items_stores_date_p202307 PARTITION OF da_items_stores_date FOR VALUES FROM ('2023-07-01') TO ('2023-08-01');
CREATE TABLE da_items_stores_date_p202308 PARTITION OF da_items_stores_date FOR VALUES FROM ('2023-08-01') TO ('2023-09-01');
CREATE TABLE da_items_stores_date_p202309 PARTITION OF da_items_stores_date FOR VALUES FROM ('2023-09-01') TO ('2023-10-01');
CREATE TABLE da_items_stores_date_p202310 PARTITION OF da_items_stores_date FOR VALUES FROM ('2023-10-01') TO ('2023-11-01');
CREATE TABLE da_items_stores_date_p202311 PARTITION OF da_items_stores_date FOR VALUES FROM ('2023-11-01') TO ('2023-12-01');
CREATE TABLE da_items_stores_date_p202312 PARTITION OF da_items_stores_date FOR VALUES FROM ('2023-12-01') TO ('2024-01-01');
-- 2024
CREATE TABLE da_items_stores_date_p202401 PARTITION OF da_items_stores_date FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
CREATE TABLE da_items_stores_date_p202402 PARTITION OF da_items_stores_date FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');
CREATE TABLE da_items_stores_date_p202403 PARTITION OF da_items_stores_date FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');
CREATE TABLE da_items_stores_date_p202404 PARTITION OF da_items_stores_date FOR VALUES FROM ('2024-04-01') TO ('2024-05-01');
CREATE TABLE da_items_stores_date_p202405 PARTITION OF da_items_stores_date FOR VALUES FROM ('2024-05-01') TO ('2024-06-01');
CREATE TABLE da_items_stores_date_p202406 PARTITION OF da_items_stores_date FOR VALUES FROM ('2024-06-01') TO ('2024-07-01');
CREATE TABLE da_items_stores_date_p202407 PARTITION OF da_items_stores_date FOR VALUES FROM ('2024-07-01') TO ('2024-08-01');
CREATE TABLE da_items_stores_date_p202408 PARTITION OF da_items_stores_date FOR VALUES FROM ('2024-08-01') TO ('2024-09-01');
CREATE TABLE da_items_stores_date_p202409 PARTITION OF da_items_stores_date FOR VALUES FROM ('2024-09-01') TO ('2024-10-01');
CREATE TABLE da_items_stores_date_p202410 PARTITION OF da_items_stores_date FOR VALUES FROM ('2024-10-01') TO ('2024-11-01');
CREATE TABLE da_items_stores_date_p202411 PARTITION OF da_items_stores_date FOR VALUES FROM ('2024-11-01') TO ('2024-12-01');
CREATE TABLE da_items_stores_date_p202412 PARTITION OF da_items_stores_date FOR VALUES FROM ('2024-12-01') TO ('2025-01-01');
-- 2025
CREATE TABLE da_items_stores_date_p202501 PARTITION OF da_items_stores_date FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
CREATE TABLE da_items_stores_date_p202502 PARTITION OF da_items_stores_date FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');
CREATE TABLE da_items_stores_date_p202503 PARTITION OF da_items_stores_date FOR VALUES FROM ('2025-03-01') TO ('2025-04-01');
CREATE TABLE da_items_stores_date_p202504 PARTITION OF da_items_stores_date FOR VALUES FROM ('2025-04-01') TO ('2025-05-01');
CREATE TABLE da_items_stores_date_p202505 PARTITION OF da_items_stores_date FOR VALUES FROM ('2025-05-01') TO ('2025-06-01');
CREATE TABLE da_items_stores_date_p202506 PARTITION OF da_items_stores_date FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');
CREATE TABLE da_items_stores_date_p202507 PARTITION OF da_items_stores_date FOR VALUES FROM ('2025-07-01') TO ('2025-08-01');
CREATE TABLE da_items_stores_date_p202508 PARTITION OF da_items_stores_date FOR VALUES FROM ('2025-08-01') TO ('2025-09-01');
CREATE TABLE da_items_stores_date_p202509 PARTITION OF da_items_stores_date FOR VALUES FROM ('2025-09-01') TO ('2025-10-01');
CREATE TABLE da_items_stores_date_p202510 PARTITION OF da_items_stores_date FOR VALUES FROM ('2025-10-01') TO ('2025-11-01');
CREATE TABLE da_items_stores_date_p202511 PARTITION OF da_items_stores_date FOR VALUES FROM ('2025-11-01') TO ('2025-12-01');
CREATE TABLE da_items_stores_date_p202512 PARTITION OF da_items_stores_date FOR VALUES FROM ('2025-12-01') TO ('2026-01-01');
-- 2026
CREATE TABLE da_items_stores_date_p202601 PARTITION OF da_items_stores_date FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');
CREATE TABLE da_items_stores_date_p202602 PARTITION OF da_items_stores_date FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
CREATE TABLE da_items_stores_date_p202603 PARTITION OF da_items_stores_date FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');
CREATE TABLE da_items_stores_date_p202604 PARTITION OF da_items_stores_date FOR VALUES FROM ('2026-04-01') TO ('2026-05-01');
CREATE TABLE da_items_stores_date_p202605 PARTITION OF da_items_stores_date FOR VALUES FROM ('2026-05-01') TO ('2026-06-01');
CREATE TABLE da_items_stores_date_p202606 PARTITION OF da_items_stores_date FOR VALUES FROM ('2026-06-01') TO ('2026-07-01');
CREATE TABLE da_items_stores_date_p202607 PARTITION OF da_items_stores_date FOR VALUES FROM ('2026-07-01') TO ('2026-08-01');
CREATE TABLE da_items_stores_date_p202608 PARTITION OF da_items_stores_date FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
CREATE TABLE da_items_stores_date_p202609 PARTITION OF da_items_stores_date FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
CREATE TABLE da_items_stores_date_p202610 PARTITION OF da_items_stores_date FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
CREATE TABLE da_items_stores_date_p202611 PARTITION OF da_items_stores_date FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE da_items_stores_date_p202612 PARTITION OF da_items_stores_date FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');

-- ============================================================
-- Indexes
-- ============================================================

CREATE INDEX idx_stores_name ON stores(name);
CREATE INDEX idx_stores_code ON stores(code);
CREATE INDEX idx_items_pcode ON items(pcode);
CREATE INDEX idx_items_description ON items(description);
CREATE INDEX idx_items_barcode ON items(barcode);
