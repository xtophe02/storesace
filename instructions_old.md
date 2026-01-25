# Database Schema (Auto-Generated)
-- Core Analytics Tables

CREATE TABLE stores (
    id integer PRIMARY KEY,
    name text, -- Store Name (e.g. "Lisboa Chiado")
    code text, -- Internal Store Code
    status integer, -- 1 = Active, 0 = Inactive
    location text, -- City/Location
    sector text -- Retail Sector
);

CREATE TABLE items (
    id integer PRIMARY KEY,
    pcode text, -- Barcode / SKU (e.g. "501023...")
    description text, -- Product Name
    status integer, -- 1 = Active, 0 = Inactive
    family_id integer,
    group_id integer
);

-- Daily Sales by Store (High Level)
CREATE TABLE da_stores_date (
    store_id integer, -- Join: stores.id
    date date, -- Sales Date
    nr_sales integer, -- Number of Tickets/Transactions
    nr_persons integer, -- Footfall / Customers
    total_quantity numeric, -- Total Items Sold
    total_net numeric, -- Revenue ex-VAT (Use this for "Sales/Revenue")
    total_doc numeric, -- Revenue inc-VAT
    total_discount numeric -- Discounts applied
);

-- Daily Sales by Item (Granular)
CREATE TABLE da_items_stores_date (
    item_id integer, -- Join: items.id
    store_id integer, -- Join: stores.id
    date date,
    total_quantity numeric, -- Qty Sold
    total_net numeric, -- Revenue ex-VAT
    total_price numeric, -- Revenue inc-VAT
    total_discount numeric,
    latest_price_cost numeric -- Unit Cost Price
);

# Business Logic & Rules
1. **Margin Formula**: `total_net - (total_quantity * latest_price_cost)`
2. **"Sales" or "Revenue"**: Always use `total_net` (Value without VAT).
3. **Active Stores Only**: Always filter `WHERE stores.status = 1` unless asked otherwise.
4. **Data Range**: Data available from 2020 to 2025.
5. **Precision**: Round monetary values to 2 decimal places.

# Language Mapping (Portuguese)
- "Vendas" = `total_net`
- "Margem" = Margin Formula (see above)
- "Quantidade" = `total_quantity`
- "Tiquets" / "Transações" = `nr_sales`
- "Hoje" = `CURRENT_DATE`
- "Ontem" = `CURRENT_DATE - INTERVAL '1 day'`
