#!/usr/bin/env python3
"""
StoreSace V2 — Multi-Agent Advisory System
Chat-based Streamlit UI with Claude tool use + Ollama V1 fallback.
"""

import streamlit as st
import psycopg2
import pandas as pd
from datetime import datetime, date
import os
import json
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

class Config:
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", "5432"))
    DB_NAME = os.getenv("DB_NAME", "storesace")
    DB_USER = os.getenv("DB_USER", "storesace")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "storesace_dev")
    DB_SCHEMA = os.getenv("DB_SCHEMA", "prod_515383678")

    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
    AGENT_MODEL = os.getenv("AGENT_MODEL", "anthropic/claude-opus-4-6")
    OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")

    APP_TITLE = "StoreSace"
    APP_ICON = "📊"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

@st.cache_resource
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=Config.DB_HOST,
            port=Config.DB_PORT,
            database=Config.DB_NAME,
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
        )
        return conn
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        st.stop()


def execute_query(sql: str) -> pd.DataFrame:
    conn = get_db_connection()
    try:
        if not sql.strip().upper().startswith("SET SEARCH_PATH"):
            sql = f"SET search_path TO {Config.DB_SCHEMA};\n{sql}"
        return pd.read_sql_query(sql, conn)
    except Exception as e:
        raise Exception(f"Query failed: {e}")


# ---------------------------------------------------------------------------
# AI Instructions
# ---------------------------------------------------------------------------

def get_ai_instructions() -> str:
    try:
        with open("instructions.md", "r", encoding="utf-8") as f:
            content = f.read()
            return content if content.strip() else "# Minimal Instructions\n- PostgreSQL database\n- Only SELECT queries"
    except FileNotFoundError:
        st.error("instructions.md not found.")
        st.stop()


# ---------------------------------------------------------------------------
# Cached Sidebar Counts
# ---------------------------------------------------------------------------

@st.cache_data(ttl=3600)
def _get_sidebar_counts() -> tuple:
    """Return (store_count, product_count) cached for 1 hour."""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(f"SET search_path TO {Config.DB_SCHEMA}; SELECT COUNT(*) FROM stores WHERE status = 1;")
        store_count = cur.fetchone()[0]
        cur.execute(f"SET search_path TO {Config.DB_SCHEMA}; SELECT COUNT(*) FROM items WHERE status = 1;")
        product_count = cur.fetchone()[0]
        cur.close()
        conn.rollback()
        return store_count, product_count
    except Exception:
        return None, None


# ---------------------------------------------------------------------------
# Ollama V1 — Text-to-SQL (preserved from V1)
# ---------------------------------------------------------------------------

@st.cache_data(ttl=60)
def get_ollama_models() -> list[str]:
    try:
        resp = requests.get(f"{Config.OLLAMA_HOST}/api/tags", timeout=5)
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]
    except Exception:
        return [Config.OLLAMA_MODEL]


def ollama_text_to_sql(question: str, model: str = None) -> str:
    model = model or Config.OLLAMA_MODEL
    instructions = get_ai_instructions()

    prompt = f"""You are a PostgreSQL expert. Convert this question to SQL.

{instructions}

**Question:** {question}

**Additional Rules for Local Models:**
- DO NOT use WITH clauses (CTEs) - use simple JOINs instead
- DO NOT use complex subqueries - keep queries simple
- Current Date: {datetime.now().date()}
- Schema: {Config.DB_SCHEMA}

Return ONLY the SQL query. No explanations.

SQL:"""

    try:
        resp = requests.post(
            f"{Config.OLLAMA_HOST}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=300,
        )
        resp.raise_for_status()
        raw_sql = resp.json().get("response", "").strip()

        sql = raw_sql
        if "```" in raw_sql:
            parts = raw_sql.split("```")
            if len(parts) >= 3:
                block = parts[1]
                sql = block[3:].strip() if block.lower().startswith("sql") else block.strip()

        sql_upper = sql.upper()
        if "SET SEARCH_PATH" in sql_upper:
            sql = sql[sql_upper.find("SET SEARCH_PATH"):]
        elif "SELECT " in sql_upper:
            sql = sql[sql_upper.find("SELECT "):]

        if ";" in sql:
            sql = sql[:sql.rfind(";") + 1]

        return sql.strip()

    except requests.exceptions.ConnectionError:
        raise Exception(f"Cannot connect to Ollama at {Config.OLLAMA_HOST}")
    except Exception as e:
        raise Exception(f"Ollama error: {e}")


# ---------------------------------------------------------------------------
# Display Helpers
# ---------------------------------------------------------------------------

def display_results(df: pd.DataFrame):
    """Display DataFrame with currency formatting and charts."""
    column_config = {}
    for col in df.columns:
        col_lower = col.lower()
        if any(x in col_lower for x in ["net", "price", "cost", "margin", "total", "revenue", "vendas", "receita", "margem"]):
            if "quantity" not in col_lower and "nr_" not in col_lower and "qtd" not in col_lower:
                column_config[col] = st.column_config.NumberColumn(col, format="%.2f \u20ac")

    st.dataframe(df, use_container_width=True, hide_index=True, column_config=column_config)

    if 0 < len(df) <= 50:
        numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
        if len(numeric_cols) > 0:
            if len(df.columns) >= 2 and df.iloc[:, 0].dtype == "object":
                chart_df = df.set_index(df.columns[0])[numeric_cols]
                st.bar_chart(chart_df)
            else:
                st.line_chart(df[numeric_cols])


def display_tool_calls(tool_log: list[dict], show_sql: bool, show_tools: bool):
    """Render tool call log as expandable sections."""
    if not tool_log:
        return

    for i, tc in enumerate(tool_log):
        tool_name = tc["tool"]
        args = tc["args"]
        result = tc["result"]

        if tool_name == "execute_sql" and show_sql:
            with st.expander(f"Consulta SQL (passo {tc['iteration']})", expanded=False):
                st.code(args.get("query", ""), language="sql")
                if "error" in result:
                    st.error(result["error"])
                else:
                    row_count = result.get("row_count", 0)
                    st.caption(f"{row_count} linhas")
                    if result.get("rows"):
                        df = pd.DataFrame(result["rows"])
                        display_results(df)

        elif tool_name == "search_web" and show_tools:
            with st.expander(f"Pesquisa Web: {args.get('query', '')}", expanded=False):
                if "error" in result:
                    st.error(result["error"])
                else:
                    if result.get("answer"):
                        st.markdown(f"**Resumo:** {result['answer']}")
                    for r in result.get("results", []):
                        st.markdown(f"- [{r['title']}]({r['url']})")
                        if r.get("snippet"):
                            st.caption(r["snippet"][:200])

        elif tool_name == "ask_perplexity" and show_tools:
            with st.expander(f"Perplexity: {args.get('question', '')[:60]}...", expanded=False):
                if "error" in result:
                    st.error(result["error"])
                else:
                    st.markdown(result.get("answer", ""))
                    citations = result.get("citations", [])
                    if citations:
                        st.caption("Fontes: " + ", ".join(str(c) for c in citations[:5]))

        elif tool_name == "get_data_context" and show_tools:
            with st.expander("Contexto dos Dados", expanded=False):
                st.json(result)


# ---------------------------------------------------------------------------
# Main App
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(
        page_title=Config.APP_TITLE,
        page_icon=Config.APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # -- Session state init --
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "tool_logs" not in st.session_state:
        st.session_state.tool_logs = {}  # keyed by message index
    if "agent_history" not in st.session_state:
        st.session_state.agent_history = []
    if "sql_cache" not in st.session_state:
        st.session_state.sql_cache = {}

    # -- Sidebar --
    with st.sidebar:
        st.title(f"{Config.APP_ICON} {Config.APP_TITLE}")
        st.caption("V2 — Assistente Inteligente")

        st.markdown("---")

        # Mode toggle
        mode = st.radio(
            "Modo",
            options=["Claude V2 (Agente)", "Ollama V1 (SQL)"],
            index=0,
            help="V2 usa Claude com ferramentas para respostas consultivas. V1 usa Ollama para text-to-SQL simples.",
        )

        ollama_model = Config.OLLAMA_MODEL  # default

        if mode == "Claude V2 (Agente)":
            st.info(f"Modelo: {Config.AGENT_MODEL.split('/')[-1]}")
        else:
            st.info(f"Ollama: {Config.OLLAMA_HOST}")
            available_models = get_ollama_models()
            default_idx = available_models.index(Config.OLLAMA_MODEL) if Config.OLLAMA_MODEL in available_models else 0
            ollama_model = st.selectbox("Modelo Ollama", options=available_models, index=default_idx)

        st.markdown("---")
        st.markdown("**Dados:** Ago 2020 \u2014 Dez 2025")

        # Cached store/product counts (refreshed every hour)
        store_count, product_count = _get_sidebar_counts()
        if store_count is not None:
            st.markdown(f"**Lojas Ativas:** {store_count} | **Produtos:** {product_count:,}")
        else:
            st.markdown("**Lojas:** -- | **Produtos:** --")

        st.markdown("---")
        st.markdown("**Definições**")
        show_sql = st.checkbox("Mostrar consultas SQL", value=True)
        show_tools = st.checkbox("Mostrar ferramentas", value=True)
        debug = st.checkbox("Modo debug", value=Config.DEBUG)

        if st.button("Limpar Conversa"):
            st.session_state.messages = []
            st.session_state.tool_logs = {}
            st.session_state.agent_history = []
            st.session_state.sql_cache = {}
            # Clear module-level caches in agents.py
            from agents import clear_caches
            clear_caches()
            st.rerun()

        st.markdown("---")
        # DB status
        try:
            conn = get_db_connection()
            st.success(f"BD: Ligado ({Config.DB_HOST}:{Config.DB_PORT})")
        except Exception:
            st.error("BD: Desligado")

    # -- Main Area --
    st.markdown(f"**Dados:** Ago 2020 \u2014 Dez 2025 &nbsp;|&nbsp; Pergunte o que quiser sobre as suas lojas, mercado ou estratégia.")

    # Example questions
    with st.expander("Exemplos de perguntas", expanded=not st.session_state.messages):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Analista**")
            st.markdown("- Vendas por loja em Dezembro 2025\n- Produtos com melhor margem no Q4 2025\n- Pior dia de vendas do mês passado")
        with col2:
            st.markdown("**Investigador**")
            st.markdown("- Como está a Action a expandir em Portugal?\n- Tendências do retalho português 2025\n- Estratégias de preço da concorrência")
        with col3:
            st.markdown("**Estrategista**")
            st.markdown("- Bundles de produtos de verão para Braga\n- Em que loja devo investir?\n- Crescimento LFL face ao ano passado")

    # -- Chat History --
    for i, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            # Show tool logs for assistant messages
            if msg["role"] == "assistant" and i in st.session_state.tool_logs:
                display_tool_calls(st.session_state.tool_logs[i], show_sql, show_tools)

    # -- Chat Input --
    if question := st.chat_input("Pergunte sobre as suas lojas, mercado ou estratégia..."):
        # Show user message
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        # Process
        with st.chat_message("assistant"):
            if mode == "Claude V2 (Agente)":
                _handle_agent_mode(question, show_sql, show_tools, debug)
            else:
                _handle_ollama_mode(question, ollama_model, show_sql)

    # -- Footer --
    st.markdown("---")
    st.caption(f"StoreSace V2 \u00b7 {datetime.now().year}")


def _handle_agent_mode(question: str, show_sql: bool, show_tools: bool, debug: bool):
    """Process a question using Claude V2 agent with tools."""
    from agents import run_agent

    conn = get_db_connection()

    with st.spinner("A pensar..."):
        try:
            final_text, updated_history, tool_log = run_agent(
                user_message=question,
                history=st.session_state.agent_history,
                conn=conn,
                sql_cache=st.session_state.sql_cache,
            )
        except Exception as e:
            final_text = f"Error: {e}"
            updated_history = st.session_state.agent_history
            tool_log = []
            if debug:
                st.exception(e)

    # Update agent history
    st.session_state.agent_history = updated_history

    # Display tool calls
    if tool_log:
        display_tool_calls(tool_log, show_sql, show_tools)

    # Display final answer
    st.markdown(final_text)

    # Store message and tool log
    msg_idx = len(st.session_state.messages)
    st.session_state.messages.append({"role": "assistant", "content": final_text})
    if tool_log:
        st.session_state.tool_logs[msg_idx] = tool_log


def _handle_ollama_mode(question: str, model: str, show_sql: bool):
    """Process a question using Ollama V1 text-to-SQL."""
    with st.spinner(f"A gerar SQL com {model}..."):
        try:
            sql = ollama_text_to_sql(question, model=model)

            if show_sql:
                with st.expander("SQL Gerado", expanded=False):
                    st.code(sql, language="sql")

            df = execute_query(sql)
            st.success(f"{len(df)} resultados")
            display_results(df)

            answer = f"Consulta devolveu {len(df)} linhas."
            st.session_state.messages.append({"role": "assistant", "content": answer})

        except Exception as e:
            error_msg = f"Error: {e}"
            st.error(error_msg)
            st.session_state.messages.append({"role": "assistant", "content": error_msg})


if __name__ == "__main__":
    main()
