# StoreSace - AI-Powered Retail Analytics

**Client:** Ivo Marinho
**Goal:** Natural language interface to query retail sales data
**Stack:** PostgreSQL + Python + LLM + Web Interface

---

## 🎯 Project Vision

Transform raw SQL queries into conversational questions:

**Before:**
```sql
SELECT s.name, SUM(d.total_net)
FROM da_stores_date d
JOIN stores s ON s.id = d.store_id
WHERE d.date = CURRENT_DATE
GROUP BY s.name;
```

**After:**
```
User: "How much did I sell today?"
System: Shows results instantly
```

---

## 📊 Data Available

### Database
- **9 stores:** Braga, Fafe, Quintã, Silvares-Guimarães, Matosinhos, S. Francisco, Online, Warehouse
- **29,929 products** (items catalog)
- **Time range:** August 2020 → December 2025 (5+ years)

### Tables
1. **stores** - Store master data
2. **items** - Product catalog
3. **da_stores_date** - Daily sales by store (8,870 rows) ✅ COMPLETE
4. **da_items_stores_date** - Daily sales by product+store (90,666 rows) ⚠️ PARTIAL (3/85 months)

### Metrics
- Revenue (with/without VAT)
- Quantity sold
- Number of sales & customers
- Costs & margins
- Discounts & returns
- Waste & breakage

---

## 🎯 Business Questions (from Ivo)

Ivo wants to ask:

1. **"How much did I sell today?"**
2. **"How much did I sell during Easter this year?"**
3. **"How much did I sell in Store X?"**
4. **"How am I doing vs last year?"**
5. **"What's my best selling product?"** (by revenue/margin/quantity)
6. **"Do I have products losing money?"** (cost > selling price)

**Plus forecasting:**
- "What will I sell next month?"
- Sales predictions & trend analysis

---

## 🏗️ Solution Architecture

```
┌──────────────┐
│ User (Ivo)   │
│ Web Browser  │
└──────┬───────┘
       │
┌──────▼───────────────────────────────┐
│   Web Interface (Streamlit/Next.js)  │
│   - Text input for questions         │
│   - Results display (table/chart)    │
│   - Export (CSV/PDF)                 │
└──────┬───────────────────────────────┘
       │
┌──────▼───────────────────────────────┐
│   Backend API (Python/FastAPI)       │
│   - Text-to-SQL conversion           │
│   - Query validation                 │
│   - Result formatting                │
└──────┬───────────────────────────────┘
       │
┌──────▼───────────────────────────────┐
│   LLM (Claude API or Ollama)         │
│   - Natural language → SQL           │
│   - Context: database schema         │
│   - Smart date parsing               │
└──────┬───────────────────────────────┘
       │
┌──────▼───────────────────────────────┐
│   PostgreSQL Database (Docker)       │
│   - 5 years of sales data            │
│   - Partitioned for performance      │
└──────────────────────────────────────┘
```

---

## 📅 Implementation Phases

### ✅ Phase 0: Foundation (DONE)
- [x] PostgreSQL in Docker
- [x] Schema created with proper types
- [x] Master data imported (stores, items)
- [x] Store-level sales data complete (all years)
- [x] BI queries documented

### 🔲 Phase 1: Complete Data Import (1-2 hours)
**Goal:** Full 5 years of product-level data

**Tasks:**
- Import remaining 82 monthly partitions (da_items_stores_date)
- Verify data integrity (no gaps)
- Create performance indexes
- Automated backup script

**Success criteria:**
- Data from Aug 2020 to Dec 2025 complete
- Query performance < 2 seconds

---

### 🔲 Phase 2: Text-to-SQL MVP (3-4 hours)
**Goal:** Working web interface Ivo can access

**Features:**
- Web UI (Streamlit or Next.js)
- Text input: ask questions in English/Portuguese
- LLM converts to SQL (Claude API or Ollama)
- Execute query on PostgreSQL
- Display results in table
- Show generated SQL (transparency)
- Export to CSV
- Error handling

**Example:**
```
Input: "Top 5 stores last month"

Generated SQL:
SELECT s.name, SUM(d.total_net) as revenue
FROM da_stores_date d
JOIN stores s ON s.id = d.store_id
WHERE d.date >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
  AND d.date < DATE_TRUNC('month', CURRENT_DATE)
GROUP BY s.name
ORDER BY revenue DESC
LIMIT 5;

Results:
Silvares-Guimarães: €45,230
Matosinhos: €38,920
Braga: €25,410
...
```

**Deployment options:**
- Streamlit Cloud (free, public URL in 5 min)
- Your server + Cloudflare Tunnel (free, full control)
- VPS + domain (€5/month, professional)

---

### 🔲 Phase 3: Advanced Features (8-10 hours)
**Goal:** Production-ready analytics platform

**Features:**
- Authentication (login for Ivo)
- Query history & favorites
- Charts & visualizations
- Date range picker
- Store/product filters
- Comparison mode (YoY, MoM)
- Query caching (Redis)
- API for integrations

---

### 🔲 Phase 4: Forecasting (8-12 hours)
**Goal:** Predict future sales

**Features:**
- Time series forecasting (Prophet/ARIMA)
- Monthly predictions (1-3 months ahead)
- Seasonality detection (Easter, Christmas)
- Confidence intervals
- Alerts for negative trends
- "What if" scenarios

---

### 🔲 Phase 5: AI Recommendations (Future)
**Goal:** Actionable insights

**Features:**
- Stock optimization alerts
- Pricing recommendations
- Anomaly detection
- Cross-sell suggestions
- Automated reports (weekly email)

---

## 🛠️ Technology Stack

### Core
- **Database:** PostgreSQL 16 (Docker)
- **Backend:** Python 3.12 + FastAPI
- **LLM:** Claude Sonnet 4.5 (or Ollama local)
- **Frontend:** Streamlit (MVP) → Next.js 16 (production)

### Libraries
```python
# Data & DB
psycopg2-binary  # PostgreSQL driver
pandas           # Data manipulation
sqlparse         # SQL validation

# LLM
anthropic        # Claude API
# or ollama      # Local LLM

# API
fastapi          # REST API
uvicorn          # ASGI server
pydantic         # Data validation

# Frontend (Streamlit)
streamlit        # Quick UI
plotly           # Charts

# Frontend (Next.js - later)
# React, TypeScript, shadcn/ui
```

### Deployment
- **Docker Compose** (PostgreSQL + backend + frontend)
- **Nginx** (reverse proxy)
- **Cloudflare Tunnel** or **ngrok** (expose to internet)
- **Your server:** 192.168.0.160 (RTX 3060 for local LLM)

---

## 💰 Cost Analysis

### Option A: Claude API (Recommended for MVP)
- **LLM:** ~€10-20/month (with caching)
- **Hosting:** €0 (Streamlit Cloud free tier)
- **Domain:** Optional (€10/year)
- **Total:** ~€10-20/month

### Option B: Fully Local (Zero Cost)
- **LLM:** Ollama (free, uses RTX 3060)
- **Hosting:** Your server (free)
- **Tunnel:** Cloudflare (free)
- **Total:** €0/month

**Recommendation:** Start with Claude API (faster, better accuracy), can switch to Ollama later.

---

## 📈 Success Metrics

### Business Metrics
- Ivo uses the system 3+ times per week
- 80% reduction in time to get insights
- All 6 initial questions answered correctly

### Technical Metrics
- Query response time < 2 seconds (p95)
- 95%+ SQL accuracy (correct queries)
- Zero data corruption
- 99%+ uptime (after deployment)

---

## ⚡ Quick Start Plan (TODAY)

### Step 1: Complete Data Import (30 min)
```bash
# Update import_database.py to load all 85 partitions
# Run import (in background)
python import_database.py
```

### Step 2: Build Streamlit MVP (2 hours)
```python
# app.py
import streamlit as st
import anthropic
import psycopg2

st.title("StoreSace Analytics")
question = st.text_input("Ask anything:")

if question:
    sql = generate_sql_with_claude(question)
    results = execute_query(sql)
    st.dataframe(results)
    st.download_button("Export CSV", results.to_csv())
```

### Step 3: Deploy (30 min)
```bash
# Push to GitHub
git add . && git commit -m "MVP" && git push

# Deploy to Streamlit Cloud
# Visit: cloud.streamlit.io
# Result: https://storesace.streamlit.app
```

### Step 4: Share with Ivo (5 min)
Send link + brief instructions

---

## 🤔 Decision Points

### 1. Frontend Framework
- **Streamlit:** 3 hours to MVP, good enough for now
- **Next.js:** 8 hours, more professional, better UX

**Recommendation:** Streamlit now, Next.js later if needed

### 2. LLM Provider
- **Claude API:** Best accuracy, $10-20/month
- **Ollama (local):** Free, slightly worse, requires GPU

**Recommendation:** Claude API, can switch to Ollama if costs are issue

### 3. Deployment
- **Streamlit Cloud:** Free, public URL in 5 min
- **Your server:** Free, more control, requires tunnel

**Recommendation:** Streamlit Cloud for MVP, migrate to server later

### 4. Data Import
- **Now:** Complete all 85 partitions (1 hour)
- **Later:** Start with partial data, demo faster

**Recommendation:** Do it now (running in background)

---

## 📁 File Structure

```
storesace/
├── README.md              # User guide
├── PROJECT.md             # This file
├── ARCHITECTURE.md        # Technical details
├── docker-compose.yml     # PostgreSQL setup
│
├── DUMP/                  # SQL files (85 partitions)
│
├── scripts/
│   ├── import_database.py # Data import
│   └── query.sh           # Quick queries
│
├── sql/
│   └── queries_bi.sql     # Example queries
│
├── src/
│   ├── app.py             # Streamlit app (MVP)
│   ├── nl2sql.py          # Text-to-SQL engine
│   ├── database.py        # PostgreSQL connection
│   └── config.py          # Configuration
│
└── tests/
    └── test_queries.py    # Test cases
```

---

## 🚀 Next Steps

**RIGHT NOW:**
1. Decide: Claude API or Ollama?
2. Decide: Complete data import first or start with partial?
3. Build Streamlit MVP (3 hours)
4. Deploy & share with Ivo

**THIS WEEK:**
- Get Ivo's feedback
- Refine queries based on usage
- Add charts/visualizations

**NEXT WEEK:**
- Consider upgrading to Next.js
- Add forecasting (Prophet)
- Production deployment on your server

---

## 💬 What I Recommend

**My vote for fastest path to value:**

1. ✅ Complete data import NOW (run script, takes 1 hour)
2. ✅ Build Streamlit app with Claude API (2-3 hours)
3. ✅ Deploy to Streamlit Cloud (5 minutes)
4. ✅ Share with Ivo tonight

**Total time:** ~4 hours
**Cost:** €10-20/month
**Result:** Working product Ivo can use from anywhere

Then next week, based on feedback:
- Upgrade to Next.js if UI needs improvement
- Add forecasting if predictions are valuable
- Switch to Ollama if costs are a concern

**Ready to start?** Let me know which approach you prefer!
