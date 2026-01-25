**Client:** Ivo Marinho
**Project Status:** Ready for V2 Development
**Core Philosophy:** From "Reporting" (SQL) to "Advisory" (Multi-Agent System)
**Tech Stack:** Python, LangGraph, Streamlit, PostgreSQL

---

## 🎯 Vision & Objectives

The goal is to build an AI "Board of Advisors" for a retail chain. The system must not only answer "How much did I sell?" but also "Why did sales drop?" and "What should I do?".

**Key Shifts from V1:**
1.  **Contextual Intelligence:** Cross-reference internal sales data with external events (weather, strikes, holidays).
2.  **Smart Comparisons:** Use "Like-for-Like" (LFL) logic instead of raw totals.
3.  **Proactive Strategy:** Suggest product bundles based on sales correlations.

---

## 🏗️ Multi-Agent Architecture (LangGraph)

The system uses a **Router** to delegate user intents to three specialized agents.

### 1. 👮 The Router (Orchestrator)
- **Role:** Classifies the user's intent.
- **Logic:**
  - *Data Question* ("How much...", "Top stores...") → **Analyst**
  - *Explanation/Context* ("Why...", "What happened in...") → **Researcher**
  - *Strategy/Product* ("Suggest...", "Bundles for...") → **Strategist**

### 2. 📊 The Analyst (Internal Data Specialist)
- **Role:** The rigorous source of numerical truth.
- **Tools:**
  - `sql_executor`: Read-only access to PostgreSQL.
  - `lfl_calculator`: Python logic to compare periods filtering out stores that weren't active in both.
- **Data Constraints (Crucial):**
  - **Schema:** `prod_515383678` (MUST use `SET search_path` in every query).
  - **Active Stores:** Always filter `WHERE stores.status = 1` unless specified.
  - **Metric:** Revenue = `total_net` (ex-VAT). Margin = `total_net - (total_quantity * latest_price_cost)`.
  - **Dates:** Data available from Aug 2020 to Dec 2025.

### 3. 🕵️ The Researcher (External Context Specialist)
- **Role:** The connection to the outside world.
- **Tools:**
  - `web_search`: A unified interface using the **Strategy Pattern**.
    - **Strategy A (Tavily):** For retrieving raw context and news snippets.
    - **Strategy B (Perplexity):** For synthesized answers and summaries.
    - *Implementation:* Allow hot-swapping or parallel execution to compare results during dev.
- **Use Cases:**
  - Explaining anomalies (e.g., "Sales dropped in Braga due to a transport strike").
  - Competitor analysis (e.g., "New Mercadona opening near Store X").

### 4. 🛒 The Strategist (Product & Patterns)
- **Role:** Optimization engine.
- **Tools:**
  - `correlation_engine`: Python (Pandas) analysis.
- **Logic Constraint:**
  - We do NOT have receipt-level data, only daily aggregates (`da_items_stores_date`).
  - **Algorithm:** Use Temporal Correlation (products selling high volumes on the same days) rather than Basket Analysis.

---