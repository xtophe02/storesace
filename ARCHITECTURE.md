# StoreSace - Text-to-SQL Architecture

**Goal:** Online web interface where Ivo can ask questions in natural language and get SQL results from PostgreSQL.

---

## 🎯 Solution Overview

### What Ivo Sees
```
┌─────────────────────────────────────────┐
│  StoreSace Analytics (Web Interface)    │
│                                          │
│  Ask anything:                           │
│  ┌────────────────────────────────────┐ │
│  │ How much did I sell today?     [→]│ │
│  └────────────────────────────────────┘ │
│                                          │
│  Results:                                │
│  ┌────────────────────────────────────┐ │
│  │ Store         | Sales              │ │
│  │ Braga         | €2,340.50          │ │
│  │ Fafe          | €1,890.30          │ │
│  │ ...           | ...                │ │
│  └────────────────────────────────────┘ │
│                                          │
│  [View SQL] [Export CSV] [Chart View]   │
└─────────────────────────────────────────┘
```

### How It Works (Behind the Scenes)

```
User Question
    ↓
Web Frontend (Next.js or Streamlit)
    ↓
Backend API (FastAPI/Python)
    ↓
LLM (Claude API or Ollama)
    ↓
SQL Query Generated
    ↓
PostgreSQL Database
    ↓
Results Formatted
    ↓
User sees results + optional chart
```

---

## 🏗️ Architecture Options

### Option A: Streamlit (FASTEST - 2 hours)
**Best for:** Quick MVP, internal use, easy sharing

```python
# app.py
import streamlit as st
from anthropic import Anthropic
import psycopg2

st.title("StoreSace Analytics")
question = st.text_input("Ask anything about your sales:")

if question:
    # 1. Send to Claude
    sql = generate_sql(question)

    # 2. Execute on PostgreSQL
    results = execute_query(sql)

    # 3. Display
    st.dataframe(results)
    st.bar_chart(results)
```

**Pros:**
- ✅ 2-3 hours to working prototype
- ✅ Built-in UI components
- ✅ Easy deployment (Streamlit Cloud or Docker)
- ✅ Free hosting option

**Cons:**
- ❌ Less customizable
- ❌ Streamlit branding (free tier)

**Deployment:**
```bash
# Local
streamlit run app.py

# Docker (accessible on LAN)
docker run -p 8501:8501 storesace-app

# Cloud (free - public URL)
streamlit deploy app.py
# → https://storesace.streamlit.app
```

---

### Option B: Next.js + FastAPI (PROFESSIONAL - 8 hours)
**Best for:** Production-ready, custom design, scalable

**Frontend (Next.js 16):**
```typescript
// app/page.tsx
'use client'
import { useState } from 'react'

export default function Analytics() {
  const [question, setQuestion] = useState('')
  const [results, setResults] = useState(null)

  const handleAsk = async () => {
    const response = await fetch('/api/query', {
      method: 'POST',
      body: JSON.stringify({ question })
    })
    setResults(await response.json())
  }

  return (
    <div className="container">
      <h1>StoreSace Analytics</h1>
      <input
        type="text"
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Ask anything..."
      />
      <button onClick={handleAsk}>Ask</button>

      {results && (
        <ResultsTable data={results} />
      )}
    </div>
  )
}
```

**Backend (FastAPI):**
```python
# api/main.py
from fastapi import FastAPI
from anthropic import Anthropic
import psycopg2

app = FastAPI()

@app.post("/query")
async def query(question: str):
    # 1. Generate SQL with Claude
    sql = await nl_to_sql(question)

    # 2. Execute query
    results = execute_sql(sql)

    # 3. Return JSON
    return {
        "sql": sql,
        "results": results,
        "chart_suggestion": suggest_chart_type(results)
    }
```

**Pros:**
- ✅ Full control over design
- ✅ Production-ready
- ✅ Fast performance
- ✅ Can add authentication, caching, etc.

**Cons:**
- ❌ More development time
- ❌ More complexity

**Deployment:**
```bash
# Development
npm run dev          # Frontend on :3000
uvicorn main:app     # Backend on :8000

# Production (Docker)
docker compose up -d
# → Frontend: https://storesace.yourdomain.com
# → API: https://api.storesace.yourdomain.com

# Or deploy to your server (192.168.0.160)
# → http://192.168.0.160:3000
```

---

### Option C: Hybrid - Streamlit + API (BALANCED - 4 hours)
**Best for:** Quick start + future flexibility

- Streamlit for UI (fast development)
- Separate FastAPI backend (reusable)
- Can replace Streamlit later without changing backend

```
Streamlit Frontend ──┐
Next.js Frontend ────┼──→ FastAPI Backend ──→ PostgreSQL
Mobile App ──────────┘
```

---

## 🤖 LLM Integration Options

### Option 1: Claude API (Anthropic) - RECOMMENDED
**Cost:** ~$10-20/month with caching

```python
from anthropic import Anthropic

client = Anthropic(api_key="sk-...")

def nl_to_sql(question: str) -> str:
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        system="""You are a SQL expert for a retail database.

Schema:
- stores (id, name, code, status)
- items (id, description, pcode)
- da_stores_date (store_id, date, total_net, nr_sales)
- da_items_stores_date (item_id, store_id, date, total_quantity, total_net)

Always SET search_path TO prod_515383678;
Only generate SELECT queries.
Today is {current_date}.
""",
        messages=[{
            "role": "user",
            "content": f"Convert to SQL: {question}"
        }]
    )
    return response.content[0].text
```

**Pros:**
- ✅ Best accuracy
- ✅ Handles complex queries
- ✅ Good at understanding context
- ✅ Fast (< 1s response)

**Cons:**
- ❌ Requires API key (cost)
- ❌ Internet dependency

---

### Option 2: Ollama (Local LLM) - FREE
**Cost:** $0/month, uses your RTX 3060

```python
import ollama

def nl_to_sql(question: str) -> str:
    response = ollama.generate(
        model='llama3.1:8b',
        prompt=f"""Convert to SQL for retail database:

Question: {question}

Schema: [same as above]

SQL:"""
    )
    return response['response']
```

**Setup:**
```bash
# On your server (192.168.0.160)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b

# Or use CodeLlama (specialized for code/SQL)
ollama pull codellama:13b
```

**Pros:**
- ✅ Free forever
- ✅ Privacy (data stays local)
- ✅ No internet needed
- ✅ Uses your GPU

**Cons:**
- ❌ Lower accuracy than Claude
- ❌ Slower (2-5s response)
- ❌ Requires GPU server

---

### Option 3: Hybrid Approach
- Claude API for production (accurate)
- Ollama as fallback (if API down)
- Cost optimization: cache frequent queries

```python
def nl_to_sql(question: str, use_local: bool = False):
    # Check cache first
    if cached := get_from_cache(question):
        return cached

    try:
        if use_local:
            sql = ollama_generate(question)
        else:
            sql = claude_generate(question)
    except Exception:
        # Fallback
        sql = ollama_generate(question)

    # Cache result
    save_to_cache(question, sql)
    return sql
```

---

## 🌐 Deployment Options (Make it Online)

### Option 1: Streamlit Cloud (EASIEST - FREE)
```bash
# Push to GitHub
git push origin main

# Deploy on Streamlit Cloud
# → Visit cloud.streamlit.io
# → Connect GitHub repo
# → Click Deploy

# Result: https://storesace.streamlit.app (public URL)
```

**Pros:**
- ✅ Free
- ✅ 5 minutes to deploy
- ✅ Public URL
- ✅ Auto-updates from GitHub

**Cons:**
- ❌ Database must be accessible from internet
- ❌ Streamlit branding

---

### Option 2: Your Server (192.168.0.160) + Tunnel
```bash
# On your server
docker compose up -d

# Expose to internet with Cloudflare Tunnel (free)
cloudflared tunnel --url http://localhost:8501

# Or use ngrok
ngrok http 8501
```

**Result:**
- `https://random-id.trycloudflare.com` → your app
- Works from anywhere

**Pros:**
- ✅ Free
- ✅ Full control
- ✅ PostgreSQL stays local

**Cons:**
- ❌ Temporary URL (with free tier)
- ❌ Server must stay on

---

### Option 3: VPS + Domain (PROFESSIONAL - ~€5/month)
```bash
# Buy domain: storesace.com (~€10/year)
# Rent VPS: Hetzner/DigitalOcean (~€5/month)

# Deploy with Docker
docker compose -f docker-compose.prod.yml up -d

# Setup Nginx + SSL
certbot --nginx -d storesace.com
```

**Result:** `https://storesace.com` (professional)

---

### Option 4: LAN Only (Internal) - FREE
```bash
# Deploy on 192.168.0.160
docker compose up -d

# Access from LAN
http://192.168.0.160:8501
```

**Pros:**
- ✅ Free
- ✅ Fast (local network)
- ✅ Secure (not exposed)

**Cons:**
- ❌ Ivo needs to be on same network
- ❌ Or use VPN

---

## 📋 My Concrete Proposal

### Phase 1: Quick MVP (TODAY - 3 hours)

**Goal:** Working demo you can show Ivo by end of day

**Stack:**
- Streamlit (UI)
- Claude API (text-to-SQL)
- PostgreSQL (existing data)
- Streamlit Cloud (deployment)

**What you'll have:**
```
URL: https://storesace.streamlit.app

Features:
✅ Text input for questions
✅ Auto-generate SQL
✅ Show results in table
✅ Export to CSV
✅ Show SQL query (transparency)
✅ Error handling

Works with current partial data (3 months)
```

**Time breakdown:**
- 1h: Streamlit app + Claude integration
- 1h: Query validation + error handling
- 1h: Deploy + test + polish

---

### Phase 2: Complete Data (TOMORROW - 2 hours)

**Goal:** Full 5 years of product-level data

**Tasks:**
- Import remaining 82 partitions
- Verify data integrity
- Add indexes for performance

**Result:** Can answer ANY question from 2020-2025

---

### Phase 3: Production Ready (NEXT WEEK - 8 hours)

**Upgrade to:**
- Next.js frontend (custom design)
- FastAPI backend (scalable)
- Authentication (login for Ivo)
- Query caching (Redis)
- Charts/visualizations
- Deploy to your server with SSL

**Result:** Professional tool, not just MVP

---

## 🎯 What I Recommend RIGHT NOW

**Let's build the Streamlit MVP today:**

1. **Complete data import** (1 hour)
   - Run script to import all 85 partitions
   - Verify we have 2020-2025 complete

2. **Build Streamlit app** (2 hours)
   - Text-to-SQL with Claude API
   - Results display
   - Export functionality

3. **Deploy online** (30 min)
   - Streamlit Cloud (free public URL)
   - Share with Ivo tonight

**Tomorrow:**
- Get feedback from Ivo
- Decide if Streamlit is enough or upgrade to Next.js

---

## 💭 Questions for You

1. **LLM preference?**
   - Claude API ($10-20/month, best quality) ← I recommend
   - Ollama local (free, good enough)
   - Both (Claude primary, Ollama fallback)

2. **Deployment?**
   - Streamlit Cloud (easiest, free, public URL) ← I recommend for MVP
   - Your server + tunnel (free, more control)
   - VPS + domain (professional, €5/month)

3. **Timeline?**
   - MVP today (3 hours, Streamlit)
   - Or wait for Next.js (8 hours, more professional)

4. **Data import?**
   - Do it now (complete database)
   - Or start with partial (demo faster)

**My vote:**
1. Complete data import NOW (running in background while we talk)
2. Build Streamlit MVP with Claude API
3. Deploy to Streamlit Cloud
4. Share with Ivo tonight
5. Upgrade to Next.js next week if needed

**What do you think?**
