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
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

    # App
    APP_TITLE = os.getenv("APP_TITLE", "StoreSace Analytics")
    APP_ICON = os.getenv("APP_ICON", "📊")
    APP_TITLE = os.getenv("APP_TITLE", "StoreSace Analytics")
    APP_ICON = os.getenv("APP_ICON", "📊")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"


def get_ai_instructions() -> str:
    """Load custom AI instructions from file"""
    try:
        with open("instructions.md", "r", encoding="utf-8") as f:
            content = f.read()
            if not content.strip():
                st.warning("instructions.md is empty. Using minimal defaults.")
                return "# Minimal Instructions\n- PostgreSQL database\n- Only SELECT queries\n- Use prod_515383678 schema"
            return content
    except FileNotFoundError:
        st.error("instructions.md not found. Create it with database schema documentation.")
        st.stop()


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

    # Load comprehensive instructions from file
    instructions = get_ai_instructions()

    system_prompt = f"""You are a PostgreSQL expert converting natural language to SQL queries.

{instructions}

**Context:**
- Current Date: {datetime.now().date()}
- Schema: {Config.DB_SCHEMA}

**Output Format:**
Return ONLY the SQL query. No explanations, no markdown, no code blocks.
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

def ollama_text_to_sql(question: str, model: str = None) -> str:
    """Convert natural language to SQL using Ollama (local LLM)"""

    try:
        import requests
    except ImportError:
        st.error("requests package not installed. Run: pip install requests")
        st.stop()
    
    # Use provided model or default from config
    model = model or Config.OLLAMA_MODEL
    # SIMPLIFIED PROMPT FOR LOCAL MODELS
    # Explicitly forbid CTEs to avoid scoping errors
    instructions = get_ai_instructions()
    
    prompt = f"""You are a PostgreSQL expert. Convert this question to SQL.

{instructions}

**Question:** {question}

**Additional Rules for Local Models:**
- DO NOT use WITH clauses (CTEs) - use simple JOINs instead
- DO NOT use complex subqueries - keep queries simple
- Use standard aggregation (SUM, COUNT, AVG)
- Current Date: {datetime.now().date()}
- Schema: {Config.DB_SCHEMA}

Return ONLY the SQL query. No explanations.

SQL:"""

    try:
        response = requests.post(
            f"{Config.OLLAMA_HOST}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()
        result = response.json()
        raw_sql = result.get("response", "").strip()

        # --- Robust SQL Extraction ---
        # 1. Try to find markdown code blocks first ( ```sql ... ``` or ``` ... ``` )
        # Using string methods for simplicity/safety without risking regex complexity issues on imports
        sql = raw_sql
        
        if "```" in raw_sql:
            parts = raw_sql.split("```")
            # Usually the SQL is in the first block (index 1)
            if len(parts) >= 3:
                block_content = parts[1]
                if block_content.lower().startswith("sql"):
                    sql = block_content[3:].strip()
                else:
                    sql = block_content.strip()
        
        # 2. If no valid SQL found in blocks (or if block was just "sql"), 
        # look for explicit start commands in the raw or extracted text
        # Because local models chatter: "Here is the query: SELECT ..."
        
        # We look for "SELECT" or "SET" (case insensitive)
        sql_upper = sql.upper()
        if "SET SEARCH_PATH" in sql_upper:
            # Take everything from SET onwards
            idx = sql_upper.find("SET SEARCH_PATH")
            sql = sql[idx:]
        elif "SELECT " in sql_upper:
            # Take everything from SELECT onwards
            idx = sql_upper.find("SELECT ")
            sql = sql[idx:]
            
        # 3. Clean up any trailing text (stop at the last semicolon if present)
        if ";" in sql:
            last_semi = sql.rfind(";")
            sql = sql[:last_semi+1]

        return sql.strip()

    except requests.exceptions.ConnectionError:
        raise Exception(f"Cannot connect to Ollama at {Config.OLLAMA_HOST}. Is it running?")
    except Exception as e:
        raise Exception(f"Ollama error: {str(e)}")


def display_results(df: pd.DataFrame):
    """Display DataFrame with currency formatting and Chart"""
    
    # Define currency columns format
    column_config = {}
    for col in df.columns:
        col_lower = col.lower()
        if any(x in col_lower for x in ['net', 'price', 'cost', 'margin', 'total', 'revenue']):
            # It's likely a monetary value
            if 'quantity' not in col_lower and 'nr_' not in col_lower:
                column_config[col] = st.column_config.NumberColumn(
                    col,
                    format="%.2f €"
                )
    
    # Display Table with formatting
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config=column_config
    )
    
    # Display Chart
    if len(df) > 0 and len(df) <= 50:
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            with st.expander("📈 Chart", expanded=True):
                if len(df.columns) >= 2 and df.iloc[:, 0].dtype == 'object':
                    st.bar_chart(df.set_index(df.columns[0]))
                else:
                    st.line_chart(df[numeric_cols])


# ============================================================================
# Main Text-to-SQL Function
# ============================================================================

@st.cache_data(ttl=3600, show_spinner=False)
def text_to_sql(question: str, provider: str = None, model: str = None) -> str:
    """Convert natural language to SQL using selected provider"""

    provider = provider or Config.LLM_PROVIDER

    if provider == "claude":
        return claude_text_to_sql(question)
    elif provider == "ollama":
        return ollama_text_to_sql(question, model=model)
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

        # Mode Selection
        mode = st.radio(
            "Mode",
            options=["Single Provider", "Compare (Cloud vs Local)"],
            index=0,
            help="Compare results between Claude (Cloud) and Ollama (Local)"
        )

        provider = "claude" # Default for single mode
        ollama_model = Config.OLLAMA_MODEL

        if mode == "Single Provider":
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
                
                # Ollama Model Selection (for Single Mode)
                ollama_model = st.selectbox(
                    "Ollama Model",
                    options=["qwen3-textsql", "qwen3:14b", "deepseek-r1:14b", Config.OLLAMA_MODEL],
                    index=2
                )
        else:
            # Compare Mode Settings
            st.info("⚔️ Comparing Claude Sonnet 4.5 vs Local Model")
            
            # Ollama Model Selection (for Compare Mode)
            ollama_model = st.selectbox(
                "Select Local Model",
                options=["qwen3-textsql", "qwen3:14b", "deepseek-r1:14b", Config.OLLAMA_MODEL],
                index=0
            )

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
        with st.expander("🧠 AI Context / Instructions"):
            st.caption("Edit the 'Brain' (Schema & Rules). Changes apply instantly.")
            
            # Load current instructions
            current_instructions = get_ai_instructions()
            
            # Text Area for editing
            new_instructions = st.text_area(
                "Instructions",
                value=current_instructions,
                height=300,
                key="ai_instructions_editor",
                help="Define tables, business logic (margin formula), and terms here."
            )
            
            if st.button("💾 Save Instructions"):
                with open("instructions.md", "w") as f:
                    f.write(new_instructions)
                st.success("Saved!")
                # Force reload of cache to pick up new instructions
                text_to_sql.clear()

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

    # Session State Initialization
    if "question_input" not in st.session_state:
        st.session_state.question_input = ""
    if "processing" not in st.session_state:
        st.session_state.processing = False

    # Example buttons (Update session state via callback)
    def set_question(q):
        st.session_state.question_input = q
        st.session_state.processing = True

    col1, col2, col3 = st.columns(3)
    with col1:
        st.button("📅 Today's Sales", on_click=set_question, args=("How much did I sell today by store?",))
    with col2:
        st.button("🏆 Top Products", on_click=set_question, args=("Top 10 products by revenue this month",))
    with col3:
        st.button("📊 YoY Comparison", on_click=set_question, args=("Sales comparison this year vs last year by month",))

    # Main Input Form
    with st.form("query_form"):
        # Key 'question_input' binds directly to st.session_state.question_input
        st.text_input(
            "Your question:",
            key="question_input",
            placeholder="e.g., How much did I sell today?",
            help="Ask in English or Portuguese"
        )
        submitted = st.form_submit_button("🚀 Run Analysis")
    
    # Execution Logic
    # Run if submitted OR if 'processing' flag was set by a button
    if submitted or st.session_state.processing:
        # Reset processing flag so it doesn't loop forever
        st.session_state.processing = False
        
        question = st.session_state.question_input
        
        # ... logic continues below (uses 'question' variable)
        if mode == "Single Provider":
            # Existing Single Provider Logic
            with st.spinner("Thinking..."):
                try:
                    # Generate SQL
                    sql = text_to_sql(question, provider=provider, model=ollama_model)  # Pass model

                    # Display generated SQL
                    with st.expander("🔍 Generated SQL", expanded=False):
                        st.code(sql, language="sql")

                    # Execute query
                    df = execute_query(sql)

                    # Display results
                    st.success(f"Found {len(df)} results")

                    # Show as table and chart
                    display_results(df)

                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
                    if Config.DEBUG:
                        st.exception(e)
        
        else:
            # Compare Mode Logic
            st.write("---")
            col_claude, col_ollama = st.columns(2)
            
            with col_claude:
                st.subheader("🌐 Claude (Cloud)")
                st.caption("Sonnet 4.5")
                with st.spinner("Claude is thinking..."):
                    try:
                        sql_c = text_to_sql(question, provider="claude")
                        st.code(sql_c, language="sql")
                        df_c = execute_query(sql_c)
                        st.success(f"✓ {len(df_c)} rows")
                        display_results(df_c)
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                
            with col_ollama:
                st.subheader("🏠 Ollama (Local)")
                st.caption(f"Model: {ollama_model}")
                with st.spinner(f"Local {ollama_model} is thinking..."):
                    try:
                        sql_o = text_to_sql(question, provider="ollama", model=ollama_model)
                        st.code(sql_o, language="sql")
                        df_o = execute_query(sql_o)
                        st.success(f"✓ {len(df_o)} rows")
                        display_results(df_o)
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

    # Footer
    st.markdown("---")
    st.caption(f"Powered by StoreSace Analytics • {datetime.now().year}")


if __name__ == "__main__":
    main()
