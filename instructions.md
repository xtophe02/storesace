# StoreSace Database Context for AI Query Generation

## Database Information
- **Type:** PostgreSQL 16
- **Schema:** prod_515383678 (MUST use in all queries: `SET search_path TO prod_515383678;`)
- **Timezone:** Europe/Lisbon
- **Data Range:** August 2020 → December 2025
- **Partitioning:** da_stores_date (by year), da_items_stores_date (by month)

---

## Core Tables & Schema

### stores
```sql
CREATE TABLE stores (
    id integer PRIMARY KEY,
    name text,           -- Store Name (e.g. "Lisboa Chiado")
    code text,           -- Internal Store Code
    status integer,      -- 1 = Active, 0 = Inactive
    location text,       -- City/Location
    sector text          -- Retail Sector
);
```
**Key constraint:** Always filter `WHERE status = 1` unless explicitly asked for inactive stores.

### items
```sql
CREATE TABLE items (
    id integer PRIMARY KEY,
    pcode text,          -- Barcode / SKU (e.g. "501023...")
    description text,    -- Product Name
    status integer,      -- 1 = Active, 0 = Inactive
    family_id integer,
    group_id integer
);
```

### da_stores_date (Daily Sales by Store)
```sql
CREATE TABLE da_stores_date (
    store_id integer,        -- FK: stores.id
    date date,               -- Sales Date
    nr_sales integer,        -- Number of Tickets/Transactions
    nr_persons integer,      -- Footfall / Customers
    total_quantity numeric,  -- Total Items Sold
    total_net numeric,       -- Revenue ex-VAT (PRIMARY REVENUE METRIC)
    total_doc numeric,       -- Revenue inc-VAT
    total_discount numeric   -- Discounts Applied
);
```
**Partitioned:** By year (2020-2025)
**Primary Key:** (store_id, date)

### da_items_stores_date (Daily Sales by Item)
```sql
CREATE TABLE da_items_stores_date (
    item_id integer,         -- FK: items.id
    store_id integer,        -- FK: stores.id
    date date,
    total_quantity numeric,  -- Qty Sold
    total_net numeric,       -- Revenue ex-VAT
    total_price numeric,     -- Revenue inc-VAT
    total_discount numeric,
    latest_price_cost numeric -- Unit Cost Price
);
```
**Partitioned:** By month (85+ partitions)
**Primary Key:** (item_id, store_id, date)

---

## Table Relationships (JOIN Paths)

```
stores ↔ da_stores_date
   JOIN: stores.id = da_stores_date.store_id

items ↔ da_items_stores_date
   JOIN: items.id = da_items_stores_date.item_id

stores ↔ da_items_stores_date
   JOIN: stores.id = da_items_stores_date.store_id

items ↔ stores ↔ da_items_stores_date (full product-store-sales)
   JOIN items i ON i.id = d.item_id
   JOIN stores s ON s.id = d.store_id
```

---

## Business Logic & Formulas

### 1. Revenue (Vendas)
**ALWAYS use `total_net`** (value without VAT) for "sales" or "revenue".

### 2. Margin Calculation
```sql
-- Margin = Revenue - Cost
total_net - (total_quantity * latest_price_cost)
```

### 3. Average Selling Price
```sql
-- Per-unit price (handle division by zero)
total_net / NULLIF(total_quantity, 0)
```

### 4. Profit Margin %
```sql
-- Percentage margin
ROUND(
    (total_net - (total_quantity * latest_price_cost)) / NULLIF(total_net, 0) * 100,
    2
)
```

### 5. Active Records Only
**Default behavior:** Filter `WHERE stores.status = 1` (active stores only).
Only include inactive if explicitly requested.

---

## Portuguese Language Mapping

| Portuguese Term | Database Column | Notes |
|----------------|----------------|-------|
| Vendas | `total_net` | Revenue ex-VAT (primary metric) |
| Receita | `total_net` | Same as "Vendas" |
| Margem | Formula | `total_net - (total_quantity * latest_price_cost)` |
| Quantidade | `total_quantity` | Units sold |
| Tiquets / Transações | `nr_sales` | Number of sales transactions |
| Clientes / Pessoas | `nr_persons` | Footfall count |
| Custo | `latest_price_cost` | Unit cost price |
| Desconto | `total_discount` | Discounts applied |

---

## Date & Time Handling (Portuguese)

### Common Date References
```sql
-- Today / Hoje
CURRENT_DATE

-- Yesterday / Ontem
CURRENT_DATE - INTERVAL '1 day'

-- This Week / Esta Semana
date >= DATE_TRUNC('week', CURRENT_DATE)

-- This Month / Este Mês
date >= DATE_TRUNC('month', CURRENT_DATE)

-- This Year / Este Ano
date >= DATE_TRUNC('year', CURRENT_DATE)

-- Last Month / Mês Passado
date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
AND date < DATE_TRUNC('month', CURRENT_DATE)

-- Last Year / Ano Passado
EXTRACT(YEAR FROM date) = EXTRACT(YEAR FROM CURRENT_DATE) - 1
```

### Important Dates (Portugal Retail Calendar)
```sql
-- Easter 2024: March 28-31
'2024-03-28' to '2024-03-31'

-- Easter 2025: April 18-20
'2025-04-18' to '2025-04-20'

-- Christmas: December 24-25
-- New Year: December 31 - January 1
```

---

## Query Patterns & Examples

### Pattern 1: Store-Level Aggregation
```sql
SET search_path TO prod_515383678;

SELECT
    s.name AS loja,
    SUM(d.total_net) AS vendas,
    SUM(d.nr_sales) AS num_transacoes
FROM da_stores_date d
JOIN stores s ON s.id = d.store_id
WHERE d.date = CURRENT_DATE
  AND s.status = 1
GROUP BY s.name
ORDER BY vendas DESC;
```

### Pattern 2: Product-Level Analysis
```sql
SET search_path TO prod_515383678;

SELECT
    i.description AS produto,
    i.pcode AS codigo,
    SUM(d.total_quantity) AS qtd_vendida,
    SUM(d.total_net) AS receita,
    ROUND(SUM(d.total_net - (d.total_quantity * d.latest_price_cost)), 2) AS margem
FROM da_items_stores_date d
JOIN items i ON i.id = d.item_id
WHERE d.date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY i.id, i.description, i.pcode
ORDER BY receita DESC
LIMIT 10;
```

### Pattern 3: Year-over-Year Comparison
```sql
SET search_path TO prod_515383678;

SELECT
    s.name,
    SUM(CASE WHEN EXTRACT(YEAR FROM d.date) = EXTRACT(YEAR FROM CURRENT_DATE)
        THEN d.total_net ELSE 0 END) AS vendas_este_ano,
    SUM(CASE WHEN EXTRACT(YEAR FROM d.date) = EXTRACT(YEAR FROM CURRENT_DATE) - 1
        THEN d.total_net ELSE 0 END) AS vendas_ano_passado,
    ROUND(
        (SUM(CASE WHEN EXTRACT(YEAR FROM d.date) = EXTRACT(YEAR FROM CURRENT_DATE) THEN d.total_net ELSE 0 END) -
         SUM(CASE WHEN EXTRACT(YEAR FROM d.date) = EXTRACT(YEAR FROM CURRENT_DATE) - 1 THEN d.total_net ELSE 0 END)) /
        NULLIF(SUM(CASE WHEN EXTRACT(YEAR FROM d.date) = EXTRACT(YEAR FROM CURRENT_DATE) - 1 THEN d.total_net ELSE 0 END), 0) * 100,
        2
    ) AS variacao_percentual
FROM da_stores_date d
JOIN stores s ON s.id = d.store_id
WHERE s.status = 1
GROUP BY s.name;
```

### Pattern 4: Unprofitable Products
```sql
SET search_path TO prod_515383678;

SELECT
    i.description,
    i.pcode,
    ROUND(AVG(d.latest_price_cost), 2) AS custo_medio,
    ROUND(AVG(d.total_net / NULLIF(d.total_quantity, 0)), 2) AS preco_venda_medio,
    SUM(d.total_quantity) AS qtd_vendida
FROM da_items_stores_date d
JOIN items i ON i.id = d.item_id
WHERE d.date >= CURRENT_DATE - INTERVAL '30 days'
  AND d.total_quantity > 0
GROUP BY i.id, i.description, i.pcode
HAVING AVG(d.latest_price_cost) > AVG(d.total_net / NULLIF(d.total_quantity, 0))
ORDER BY qtd_vendida DESC;
```

---

## Critical SQL Rules

### 1. Always Start Queries With
```sql
SET search_path TO prod_515383678;
```

### 2. Read-Only Queries
Only generate SELECT statements. No INSERT, UPDATE, DELETE, DROP, etc.

### 3. NULL Safety
Always use `NULLIF()` for division:
```sql
-- CORRECT
total_net / NULLIF(total_quantity, 0)

-- WRONG (will error on zero quantity)
total_net / total_quantity
```

### 4. Rounding Monetary Values
```sql
ROUND(total_net, 2)  -- Always 2 decimal places for money
```

### 5. Active Stores Filter
**Default:** `WHERE stores.status = 1`
Only omit if user explicitly asks for inactive stores.

### 6. Date Ranges
Use PostgreSQL INTERVAL syntax:
```sql
-- CORRECT
date >= CURRENT_DATE - INTERVAL '7 days'

-- WRONG
date >= CURRENT_DATE - 7
```

---

## Performance Guidelines

### 1. Use Specific Date Ranges
```sql
-- GOOD (uses partition pruning)
WHERE date >= '2025-01-01' AND date < '2025-02-01'

-- BAD (full table scan)
WHERE EXTRACT(YEAR FROM date) = 2025 AND EXTRACT(MONTH FROM date) = 1
```

### 2. Avoid SELECT *
Always specify required columns:
```sql
-- GOOD
SELECT s.name, SUM(d.total_net)

-- BAD
SELECT *
```

### 3. Use Indexes Wisely
Primary lookups are already indexed:
- stores: id
- items: id
- da_stores_date: (store_id, date)
- da_items_stores_date: (item_id, store_id, date)

---

## Common Pitfalls to Avoid

1. **Forgetting schema prefix** → Always use `SET search_path TO prod_515383678;`
2. **Using total_doc instead of total_net** → Revenue should be ex-VAT (`total_net`)
3. **Not filtering inactive stores** → Add `stores.status = 1`
4. **Division by zero** → Use `NULLIF(denominator, 0)`
5. **Incorrect date arithmetic** → Use PostgreSQL `INTERVAL '1 day'` syntax
6. **Missing JOINs** → da_stores_date has no store names, must JOIN stores
7. **Incorrect margin formula** → `total_net - (total_quantity * latest_price_cost)`
8. **Not rounding money** → Always `ROUND(value, 2)` for currency

---

## Data Quality Notes

- **Data Range:** August 2020 → December 2025 (5+ years)
- **Completeness:** da_stores_date is 100% complete; da_items_stores_date is complete
- **Gaps:** None expected, but always verify date ranges in results
- **Timezone:** All dates are in Europe/Lisbon timezone

---

## Query Validation Checklist

Before returning a query, verify:
- [ ] Starts with `SET search_path TO prod_515383678;`
- [ ] Uses `total_net` for revenue (not total_doc)
- [ ] Filters `stores.status = 1` (unless inactive requested)
- [ ] Uses `NULLIF()` for any division
- [ ] Rounds monetary values to 2 decimals
- [ ] Uses proper JOIN syntax with explicit ON clauses
- [ ] Uses PostgreSQL-specific date functions (INTERVAL, DATE_TRUNC, EXTRACT)
- [ ] Only contains SELECT (read-only)
