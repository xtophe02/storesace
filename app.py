#!/usr/bin/env python3
"""
StoreSace Analytics - Text-to-SQL Interface
Supports both Claude API and Ollama (local LLM)
"""

import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime, date
import os
from typing import Optional, Dict, Any
import json

# ============================================================================
# Configuration
# ============================================================================

class Config:
    """App configuration from environment or defaults"""

    # Database
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "storesace")
    DB_USER = os.getenv("DB_USER", "storesace")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "storesace_dev")
    DB_SCHEMA = os.getenv("DB_SCHEMA", "prod_515383678")

    # LLM
    LLM_PROVIDER = os.getenv("LLM_PROVIDER", "claude")  # 'claude' or 'ollama'
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

    # App
    APP_TITLE = os.getenv("APP_TITLE", "StoreSace Analytics")
    APP_ICON = os.getenv("APP_ICON", "📊")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"


# ============================================================================
# Database Connection
# ============================================================================

@st.cache_resource
def get_db_connection():
    """Get PostgreSQL connection (cached)"""
    try:
        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD
        )
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {str(e)}")
        st.stop()


def execute_query(sql: str) -> pd.DataFrame:
    """Execute SQL query and return DataFrame"""
    conn = get_db_connection()

    try:
        # Ensure we're using the right schema
        if not sql.strip().upper().startswith("SET SEARCH_PATH"):
            sql = f"SET search_path TO {Config.DB_SCHEMA};\n{sql}"

        df = pd.read_sql_query(sql, conn)
        return df
    except Exception as e:
        raise Exception(f"Query execution failed: {str(e)}")


# ============================================================================
# LLM Integration - Claude via OpenRouter
# ============================================================================

def claude_text_to_sql(question: str) -> str:
    """Convert natural language to SQL using Claude via OpenRouter"""

    try:
        import requests
    except ImportError:
        st.error("requests package not installed. Run: pip install requests")
        st.stop()

    if not Config.OPENROUTER_API_KEY:
        st.error("OPENROUTER_API_KEY not set in environment")
        st.stop()

    # System prompt with schema context
    system_prompt = f"""You are a SQL expert for a Portuguese retail database.

Database Schema (search_path: {Config.DB_SCHEMA}):

**stores** - Store master data
- id (integer, primary key)
- name (text) - Store name
- code (text) - Store code
- status (integer) - 1=active, 0=inactive
- location (text)
- timezone (text)

**items** - Product catalog
- id (integer, primary key)
- pcode (text) - Product code/barcode
- description (text) - Product description
- short_description1 (text)
- type (integer)
- status (integer) - 1=active, 0=inactive

**da_stores_date** - Daily sales by store (partitioned by year)
- store_id (integer, FK → stores.id)
- date (date)
- nr_sales (integer) - Number of transactions
- nr_persons (integer) - Number of customers
- total_quantity (numeric) - Total items sold
- total_net (numeric) - Revenue without VAT
- total_doc (numeric) - Revenue with VAT
- total_discount (numeric) - Total discounts
- nr_credits (integer) - Number of returns
- credits_total_net (numeric) - Returns amount

**da_items_stores_date** - Daily sales by product+store (partitioned by month)
- item_id (integer, FK → items.id)
- store_id (integer, FK → stores.id)
- date (date)
- total_quantity (numeric) - Quantity sold
- total_net (numeric) - Revenue without VAT
- total_price (numeric) - Revenue with VAT
- total_discount (numeric) - Discounts
- latest_price_cost (numeric) - Unit cost
- price_average_cost (numeric) - Average cost

**CRITICAL RULES:**
1. ALWAYS start with: SET search_path TO {Config.DB_SCHEMA};
2. Only generate SELECT queries (read-only)
3. Join tables properly:
   - stores ↔ da_stores_date: stores.id = da_stores_date.store_id
   - stores ↔ da_items_stores_date: stores.id = da_items_stores_date.store_id
   - items ↔ da_items_stores_date: items.id = da_items_stores_date.item_id
4. Filter active stores: WHERE stores.status = 1
5. Current date reference: CURRENT_DATE
6. Portuguese context:
   - "hoje" = today = CURRENT_DATE
   - "ontem" = yesterday = CURRENT_DATE - INTERVAL '1 day'
   - "esta semana" = this week
   - "este mês" = this month
   - "este ano" = this year
7. Easter 2025: April 18-20 ('2025-04-18' to '2025-04-20')
8. Christmas: December 24-25
9. Margin calculation: total_net - (total_quantity * latest_price_cost)
10. Always use numeric precision for money (ROUND to 2 decimals)

Current date: {datetime.now().date()}

Return ONLY the SQL query, no explanations or markdown.
"""

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "anthropic/claude-sonnet-4.5",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Convert this question to SQL: {question}"}
                ],
                "max_tokens": 2048
            },
            timeout=30
        )

        if response.status_code != 200:
            raise Exception(f"OpenRouter API error: {response.status_code} - {response.text}")

        result = response.json()
        sql = result["choices"][0]["message"]["content"].strip()

        # Clean up markdown code blocks if present
        if sql.startswith("```sql"):
            sql = sql.replace("```sql", "").replace("```", "").strip()
        elif sql.startswith("```"):
            sql = sql.replace("```", "").strip()

        return sql

    except Exception as e:
        raise Exception(f"OpenRouter API error: {str(e)}")


# ============================================================================
# LLM Integration - Ollama (Local)
# ============================================================================

def ollama_text_to_sql(question: str) -> str:
    """Convert natural language to SQL using Ollama (local LLM)"""

    try:
        import requests
    except ImportError:
        st.error("requests package not installed. Run: pip install requests")
        st.stop()

    # Simplified prompt for local LLM
    prompt = f"""You are a SQL expert. Convert this question to a PostgreSQL query.

Database has these tables:
- stores (id, name, status)
- items (id, pcode, description)
- da_stores_date (store_id, date, total_net, nr_sales)
- da_items_stores_date (item_id, store_id, date, total_quantity, total_net, latest_price_cost)

Question: {question}

Rules:
- Start with: SET search_path TO {Config.DB_SCHEMA};
- Only SELECT queries
- Use CURRENT_DATE for "today"
- Join stores.id = da_stores_date.store_id
- Return ONLY the SQL, no explanation

SQL:"""

    try:
        response = requests.post(
            f"{Config.OLLAMA_HOST}/api/generate",
            json={
                "model": Config.OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=30
        )

        if response.status_code != 200:
            raise Exception(f"Ollama API error: {response.status_code}")

        result = response.json()
        sql = result.get("response", "").strip()

        # Clean up
        if sql.startswith("```sql"):
            sql = sql.replace("```sql", "").replace("```", "").strip()
        elif sql.startswith("```"):
            sql = sql.replace("```", "").strip()

        return sql

    except requests.exceptions.ConnectionError:
        raise Exception(f"Cannot connect to Ollama at {Config.OLLAMA_HOST}. Is it running?")
    except Exception as e:
        raise Exception(f"Ollama error: {str(e)}")


# ============================================================================
# Main Text-to-SQL Function
# ============================================================================

def text_to_sql(question: str, provider: str = None) -> str:
    """Convert natural language to SQL using selected provider"""

    provider = provider or Config.LLM_PROVIDER

    if provider == "claude":
        return claude_text_to_sql(question)
    elif provider == "ollama":
        return ollama_text_to_sql(question)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


# ============================================================================
# Streamlit UI
# ============================================================================

def main():
    """Main Streamlit app"""

    st.set_page_config(
        page_title=Config.APP_TITLE,
        page_icon=Config.APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Sidebar
    with st.sidebar:
        st.title(f"{Config.APP_ICON} {Config.APP_TITLE}")

        st.markdown("---")
        st.markdown("### Settings")

        # LLM Provider Selection
        provider = st.radio(
            "LLM Provider",
            options=["claude", "ollama"],
            index=0 if Config.LLM_PROVIDER == "claude" else 1,
            help="Claude API (cloud, best) or Ollama (local, private)"
        )

        if provider == "claude":
            st.info("🌐 Using Claude Sonnet 4.5 via OpenRouter")
        else:
            st.info(f"🏠 Using Ollama local at {Config.OLLAMA_HOST}")

        st.markdown("---")
        st.markdown("### Example Questions")
        st.markdown("""
        - How much did I sell today?
        - Top 5 stores last month
        - Best selling products this year
        - Products losing money
        - Sales comparison vs last year
        - How much during Easter?
        """)

        st.markdown("---")
        st.markdown("### Database Info")
        st.caption(f"Host: {Config.DB_HOST}:{Config.DB_PORT}")
        st.caption(f"Database: {Config.DB_NAME}")
        st.caption(f"Schema: {Config.DB_SCHEMA}")

        # Connection test
        try:
            conn = get_db_connection()
            st.success("✓ Connected")
        except:
            st.error("✗ Connection failed")

    # Main content
    st.title("Ask Anything About Your Sales")

    # Question input
    question = st.text_input(
        "Your question:",
        placeholder="e.g., How much did I sell today?",
        help="Ask in English or Portuguese"
    )

    # Example buttons
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📅 Today's Sales"):
            question = "How much did I sell today by store?"
    with col2:
        if st.button("🏆 Top Products"):
            question = "Top 10 products by revenue this month"
    with col3:
        if st.button("📊 YoY Comparison"):
            question = "Sales comparison this year vs last year by month"

    if question:
        with st.spinner("Thinking..."):
            try:
                # Generate SQL
                sql = text_to_sql(question, provider=provider)

                # Display generated SQL
                with st.expander("🔍 Generated SQL", expanded=False):
                    st.code(sql, language="sql")

                # Execute query
                df = execute_query(sql)

                # Display results
                st.success(f"Found {len(df)} results")

                # Show as table
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True
                )

                # Download button
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"storesace_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )

                # Try to show chart if numeric data
                if len(df) > 0 and len(df) <= 50:  # Don't chart huge datasets
                    numeric_cols = df.select_dtypes(include=['number']).columns
                    if len(numeric_cols) > 0:
                        with st.expander("📈 Chart", expanded=True):
                            # Auto-detect best chart type
                            if len(df.columns) >= 2:
                                # Bar chart if first col is text, second is numeric
                                if df.iloc[:, 0].dtype == 'object' and df.iloc[:, 1].dtype in ['int64', 'float64']:
                                    st.bar_chart(df.set_index(df.columns[0]))
                                else:
                                    st.line_chart(df[numeric_cols])
                            else:
                                st.line_chart(df[numeric_cols])

            except Exception as e:
                st.error(f"❌ Error: {str(e)}")

                if Config.DEBUG:
                    st.exception(e)

    # Footer
    st.markdown("---")
    st.caption(f"Powered by {provider.title()} • {datetime.now().year}")


if __name__ == "__main__":
    main()
