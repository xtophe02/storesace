# StoreSace - Quick Start (Tonight's Demo)

Get from zero to working demo in < 1 hour.

---

## ⚡ Complete Checklist

### Step 1: Complete Data Import (30 min)

```bash
cd /home/chris/projects/storesace

# Run complete import (imports all 85 partitions)
python3 import_complete.py
```

**What this does:**
- Imports 82 remaining monthly partitions
- You'll have Aug 2020 → Dec 2026 data
- ~2M+ rows of product-level sales data

**Expected output:**
```
Importing DA Items Stores Date (monthly partitions)
Total partitions to import: 82
[1/82] Processing da_items_stores_date_p202011
  Found 12,345 INSERT statements
  Batch 1/13
  ...
✓ Import complete!
Final rows: 2,450,000
```

---

### Step 2: Install Ollama (On Server - Optional)

If you want to demo **local LLM** (data privacy):

```bash
# On your server (192.168.0.160)
ssh chris@192.168.0.160

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull model (uses RTX 3060)
ollama pull llama3.1:8b
# Or for better SQL: ollama pull codellama:13b

# Test
ollama run llama3.1:8b "Write SQL to get today's sales"
```

**Skip this if** you only want to use Claude API.

---

### Step 3: Setup Application (10 min)

```bash
cd /home/chris/projects/storesace

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env
```

**In .env file:**

**For Claude API:**
```bash
LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-api03-your-actual-key-here
DB_HOST=localhost
DB_PASSWORD=storesace_dev
```

**For Ollama (local):**
```bash
LLM_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.1:8b
DB_HOST=localhost
DB_PASSWORD=storesace_dev
```

---

### Step 4: Run Locally (Test)

```bash
# Activate venv (if not already)
source venv/bin/activate

# Run Streamlit
streamlit run app.py

# Opens browser automatically at http://localhost:8501
```

**Test queries:**
1. "How much did I sell today?"
2. "Top 5 stores last month"
3. "Best selling products"

**If it works:** ✅ Local test successful!

---

### Step 5: Deploy for Ivo (Choose ONE)

#### Option A: Your Server + Cloudflare Tunnel (RECOMMENDED)

**Why:** Free, uses Ollama, data stays local

```bash
# On server (if running there)
ssh chris@192.168.0.160
cd ~/apps/storesace

# Start app
source venv/bin/activate
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &

# Expose to internet
cloudflared tunnel --url http://localhost:8501

# Output example:
# Your quick Tunnel has been created! Visit it at:
# https://random-abc-123.trycloudflare.com
```

**Share that URL with Ivo!**

---

#### Option B: Streamlit Cloud (If you want Claude API)

**Why:** Simplest cloud deployment, free

```bash
# 1. Push to GitHub
git init
git add .
git commit -m "StoreSace v1"
git remote add origin https://github.com/xtophe02/storesace.git
git push -u origin main

# 2. Deploy
# Visit: https://share.streamlit.io
# Login → New app → Select repo → app.py
# Secrets: Add ANTHROPIC_API_KEY

# 3. Database access
# Problem: Can't connect to localhost from cloud

# Solution: Use Cloudflare Tunnel for PostgreSQL
cloudflared tunnel --url tcp://localhost:5432
# Copy the URL, add to Streamlit secrets as DB_HOST
```

**Result:** `https://storesace.streamlit.app`

---

## 📱 Share with Ivo

Send him:

```
Hi Ivo,

Here's the StoreSace Analytics demo:

🔗 https://random-abc-123.trycloudflare.com

Try asking:
• "How much did I sell today?"
• "Top 5 stores last month"
• "Best selling products this year"
• "Products losing money"

You can ask in English or Portuguese!

Features:
✅ Natural language → SQL (powered by AI)
✅ All your sales data (2020-2025)
✅ Export results to CSV
✅ See the generated SQL (transparency)

Let me know what you think!
```

---

## 🎯 Expected Timeline

```
30 min → Data import complete
10 min → Python setup
 5 min → Local testing
10 min → Deployment
 5 min → Share with Ivo
────────
60 min total
```

---

## 🐛 Common Issues

### "Import taking too long"
The import processes 82 partition files. Takes 20-40 minutes depending on hardware.

**Solution:** Let it run in background:
```bash
nohup python3 import_complete.py > import.log 2>&1 &
tail -f import.log
```

### "Can't connect to database"
```bash
# Check PostgreSQL
docker ps | grep storesace_db

# Restart if needed
docker compose restart
```

### "Ollama not responding"
```bash
# Check Ollama service
curl http://localhost:11434/api/tags

# Restart Ollama
sudo systemctl restart ollama
```

### "Cloudflare tunnel stopped"
Free tunnels expire after inactivity. Just re-run:
```bash
cloudflared tunnel --url http://localhost:8501
```

For permanent tunnel, use authenticated cloudflare tunnel (see DEPLOYMENT.md).

---

## ✅ Success Criteria

**You're done when:**
1. ✅ Import shows "2,000,000+" rows
2. ✅ Streamlit app runs locally
3. ✅ Can ask "How much did I sell today?" and get results
4. ✅ Public URL works (tunnel or Streamlit Cloud)
5. ✅ Ivo can access it

---

## 🎁 Bonus: Demo Script

When showing Ivo:

1. **Simple question:** "How much did I sell today?"
   - Shows current day sales by store
   - Export CSV feature
   - SQL transparency

2. **Complex question:** "Top 10 products by revenue this month"
   - Shows it handles joins (items + sales)
   - Aggregation (SUM)
   - Ordering and limiting

3. **Business question:** "Products losing money"
   - Shows margin calculation
   - Filters (cost > price)
   - Actionable insights

4. **Time series:** "Sales comparison this year vs last year"
   - Shows year-over-year analysis
   - Multiple aggregations
   - Business intelligence

5. **Toggle LLM:** Switch between Claude and Ollama
   - Shows data privacy option
   - Compare response quality
   - Demonstrate local capability

---

## 📞 Need Help?

If stuck, check:
1. `docker compose logs` for PostgreSQL issues
2. `streamlit.log` for app issues
3. Browser console for frontend errors
4. DEPLOYMENT.md for detailed troubleshooting

---

**Ready?** Start with Step 1 (data import) and work through sequentially. You've got this! 🚀
