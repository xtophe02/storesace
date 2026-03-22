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

## Portuguese Calendar & Key Retail Dates

### National Holidays (Fixed)
| Date | Holiday |
|------|---------|
| Jan 1 | Ano Novo (New Year's Day) |
| Apr 25 | Dia da Liberdade (Freedom Day) |
| May 1 | Dia do Trabalhador (Labour Day) |
| Jun 10 | Dia de Portugal |
| Aug 15 | Assunção de Nossa Senhora (Assumption) |
| Oct 5 | Implantação da República |
| Nov 1 | Dia de Todos os Santos (All Saints) |
| Dec 1 | Restauração da Independência |
| Dec 8 | Imaculada Conceição |
| Dec 25 | Natal (Christmas) |

### Easter Dates (Moveable - with Carnival & Corpus Christi)
| Year | Carnival (47 days before Easter) | Good Friday | Easter Sunday | Corpus Christi (60 days after Easter) |
|------|----------------------------------|-------------|---------------|---------------------------------------|
| 2020 | Feb 25 | Apr 10 | Apr 12 | Jun 11 |
| 2021 | Feb 16 | Apr 2 | Apr 4 | Jun 3 |
| 2022 | Mar 1 | Apr 15 | Apr 17 | Jun 16 |
| 2023 | Feb 21 | Apr 7 | Apr 9 | Jun 8 |
| 2024 | Feb 13 | Mar 29 | Mar 31 | May 30 |
| 2025 | Mar 4 | Apr 18 | Apr 20 | Jun 19 |

### Regional Events (Northern Portugal — Poupeuro territory)
| Event | City | Typical Dates | Sales Impact |
|-------|------|---------------|-------------|
| São João | Porto, Braga | June 23-24 | HIGH — major street festival, peak foot traffic |
| Festas Gualterianas | Guimarães | First weekend of August | MEDIUM — regional fair |
| Romaria de São Bartolomeu | Ponte de Lima | August 19-24 | MEDIUM — attracts regional visitors |
| Feira de São Mateus | Viseu | August-September | LOW (outside core territory) |
| Back to School | All stores | September 1-15 | HIGH — school supplies spike |
| Black Friday | All stores | Last Friday of November | HIGH — discount retail peak |
| Christmas Season | All stores | December 1-24 | HIGHEST — peak sales period |

### Key Retail Periods for Analysis
```sql
-- Easter week (Good Friday to Easter Monday)
-- Use the Easter dates table above for each year

-- São João (Porto/Braga peak)
WHERE date BETWEEN 'YYYY-06-20' AND 'YYYY-06-25'

-- Back to School
WHERE date BETWEEN 'YYYY-09-01' AND 'YYYY-09-15'

-- Black Friday week
WHERE date BETWEEN 'YYYY-11-25' AND 'YYYY-12-01'

-- Christmas Season
WHERE date BETWEEN 'YYYY-12-01' AND 'YYYY-12-24'
```

---

## Competitor Context

Poupeuro operates in the discount variety retail segment in Northern Portugal. Key competitors:

| Competitor | Type | Presence in Portugal | Notes |
|-----------|------|---------------------|-------|
| **Action** | Dutch discount variety | Expanding aggressively since 2022, 50+ stores by 2025 | Direct competitor, very low prices, non-food focus |
| **PrimaPrix** | Spanish discount variety | ~20 stores, mostly Lisbon/Porto areas | Branded overstock model, food + non-food |
| **Mercadona** | Spanish supermarket | 50+ stores since 2019 entry | Food-focused but private label strategy overlaps |
| **Lidl** | German discount supermarket | 270+ stores nationwide | Non-food "Bazaar" aisle competes directly |
| **Pingo Doce** | Portuguese supermarket | 450+ stores | Jerónimo Martins group, aggressive promos |
| **Continente** | Portuguese hypermarket | 300+ stores (Sonae group) | Broad range, loyalty program |
| **IKEA** | Swedish home/furniture | 5 stores + online | Competes in home/decor segment |
| **Primark** | Irish fast fashion | 10+ stores | Competes in apparel/accessories segment |

### Competitive Analysis Queries
When users ask about competitors or competitive positioning:
1. Use **search_web** or **ask_perplexity** for current competitor news
2. Cross-reference with internal sales data for the same period/category
3. Look for correlation: did our sales dip when a competitor opened nearby?

---

## Like-for-Like (LFL) Comparison Rules

Like-for-Like (LFL / Comparable Store Sales) compares only stores that were active in BOTH periods. This is critical for fair YoY comparisons when stores open or close.

### LFL SQL Pattern
```sql
-- Step 1: Find stores active in BOTH periods using INTERSECT
-- Step 2: Filter both periods to only those stores

-- Example: LFL comparison December 2024 vs December 2025
SET search_path TO prod_515383678;

WITH lfl_stores AS (
    SELECT DISTINCT store_id FROM da_stores_date
    WHERE date >= '2024-12-01' AND date < '2025-01-01'
    INTERSECT
    SELECT DISTINCT store_id FROM da_stores_date
    WHERE date >= '2025-12-01' AND date < '2026-01-01'
)
SELECT
    s.name,
    SUM(CASE WHEN d.date >= '2024-12-01' AND d.date < '2025-01-01'
        THEN d.total_net ELSE 0 END) AS revenue_2024,
    SUM(CASE WHEN d.date >= '2025-12-01' AND d.date < '2026-01-01'
        THEN d.total_net ELSE 0 END) AS revenue_2025,
    ROUND(
        (SUM(CASE WHEN d.date >= '2025-12-01' AND d.date < '2026-01-01' THEN d.total_net ELSE 0 END) -
         SUM(CASE WHEN d.date >= '2024-12-01' AND d.date < '2025-01-01' THEN d.total_net ELSE 0 END)) /
        NULLIF(SUM(CASE WHEN d.date >= '2024-12-01' AND d.date < '2025-01-01' THEN d.total_net ELSE 0 END), 0) * 100,
        2
    ) AS lfl_growth_pct
FROM da_stores_date d
JOIN stores s ON s.id = d.store_id
WHERE d.store_id IN (SELECT store_id FROM lfl_stores)
  AND s.status = 1
GROUP BY s.name
ORDER BY lfl_growth_pct DESC;
```

### When to use LFL:
- Any year-over-year comparison
- Any period-over-period comparison where store count may differ
- User asks about "comparable", "like-for-like", "same-store", or "LFL"

---

## Temporal Correlation — Product Bundle Analysis

To find products frequently bought together (co-occurrence in daily aggregates):

### Pattern: Products sold together on the same day in the same store
```sql
SET search_path TO prod_515383678;

-- Find products that co-occur with a target product on same store/day
WITH target_days AS (
    SELECT store_id, date
    FROM da_items_stores_date
    WHERE item_id = :target_item_id
      AND date >= '2025-06-01' AND date < '2025-09-01'
      AND total_quantity > 0
)
SELECT
    i.description,
    COUNT(DISTINCT (d.store_id, d.date)) AS co_occurrence_days,
    SUM(d.total_quantity) AS total_qty,
    SUM(d.total_net) AS total_revenue
FROM da_items_stores_date d
JOIN items i ON i.id = d.item_id
JOIN target_days td ON td.store_id = d.store_id AND td.date = d.date
WHERE d.item_id != :target_item_id
  AND d.total_quantity > 0
GROUP BY i.id, i.description
ORDER BY co_occurrence_days DESC
LIMIT 20;
```

### Seasonal Bundle Discovery
For finding seasonal product bundles (e.g., summer products):
1. Identify products with strong seasonal peaks (high summer vs winter ratio)
2. Find co-occurring products in peak season
3. Suggest bundles based on co-occurrence frequency

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
