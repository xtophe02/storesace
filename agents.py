#!/usr/bin/env python3
"""
StoreSace V2 - Multi-Agent Advisory System
Native Claude tool use via OpenRouter. No LangGraph.
"""

import hashlib
import json
import os
import re
import logging
import time
from datetime import datetime, date
from typing import Any

import psycopg2
import psycopg2.extras
import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
AGENT_MODEL = os.getenv("AGENT_MODEL", "anthropic/claude-opus-4-6")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY", "")
DB_SCHEMA = os.getenv("DB_SCHEMA", "prod_515383678")

MAX_ROWS = 200
MAX_ITERATIONS = 10
MAX_HISTORY_MESSAGES = 10
CACHE_TTL_SECONDS = 24 * 3600  # 24 hours for web/perplexity caches

# Module-level caches (persist across requests within the same process)
_web_cache: dict[str, tuple[float, dict]] = {}        # query -> (timestamp, result)
_perplexity_cache: dict[str, tuple[float, dict]] = {}  # question -> (timestamp, result)
_data_context_cache: dict | None = None


# ---------------------------------------------------------------------------
# System Prompt Builder
# ---------------------------------------------------------------------------

def build_system_prompt() -> str:
    """Load instructions.md and inject runtime context."""
    try:
        with open("instructions.md", "r", encoding="utf-8") as f:
            instructions = f.read()
    except FileNotFoundError:
        instructions = "(instructions.md not found)"

    today = date.today()

    return f"""You are StoreSace Advisory — an intelligent retail analytics assistant for Poupeuro, a discount variety retail chain with 9 stores in northern Portugal.

You have access to tools that let you:
1. **execute_sql** — Query the PostgreSQL database (read-only SELECT only)
2. **search_web** — Search the web for current market information (Tavily)
3. **ask_perplexity** — Ask Perplexity AI for synthesized research answers
4. **get_data_context** — Get database metadata (date range, store count, product count)

## CRITICAL RULES — ALWAYS USE TOOLS:
- **NEVER answer questions about sales, revenue, products, stores, or any business data from memory. You MUST call execute_sql to get real data.**
- **NEVER invent or estimate numbers. If you need data, query for it.**
- **NEVER answer questions about competitors, market trends, or external information from memory. You MUST call search_web or ask_perplexity to get current information.**
- For strategic questions → call BOTH execute_sql (internal data) AND search_web/ask_perplexity (external context), then synthesize advice
- If unsure whether you need a tool → use the tool. It is always better to verify with real data than to guess.
- Always check data boundaries first if the question involves dates near the edges

## How to present answers:
- Present monetary values in EUR with 2 decimal places
- Answer in the same language as the question (Portuguese or English)
- Be concise but thorough. Give actionable insights, not just raw numbers.
- When showing data, provide brief analysis of what the numbers mean.

## Current Context:
- **Today's Date:** {today.isoformat()}
- **Data Range:** August 2020 to December 2025
- **Schema:** {DB_SCHEMA}
- **IMPORTANT:** Data ends on 2025-12-31. If the user asks about dates after Dec 2025, inform them that the data only covers up to December 2025 and offer to show the most recent available data instead.

## Database Instructions:
{instructions}
"""


# ---------------------------------------------------------------------------
# Tool Definitions (OpenAI function-calling format)
# ---------------------------------------------------------------------------

def get_tool_definitions() -> list[dict]:
    """Return tool definitions in OpenAI function-calling format."""
    return [
        {
            "type": "function",
            "function": {
                "name": "execute_sql",
                "description": "Execute a read-only SQL SELECT query against the PostgreSQL database. The query must be a SELECT statement. The search_path is set automatically — do NOT include SET search_path in your query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The SQL SELECT query to execute. Do NOT include SET search_path."
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Search the web for current information about retail markets, competitors, trends, or any external context. Use for questions about competitors (Action, PrimaPrix, Mercadona, Lidl), market trends, or Portuguese retail news.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query in English or Portuguese"
                        }
                    },
                    "required": ["query"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "ask_perplexity",
                "description": "Ask Perplexity AI a research question for a synthesized, well-sourced answer. Best for complex questions that need analysis, not just search results. Use for strategic questions, market analysis, or when you need a well-reasoned answer about retail, competitors, or Portuguese market.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "The research question to ask Perplexity"
                        }
                    },
                    "required": ["question"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_data_context",
                "description": "Get database metadata: available date range, number of active stores and their names, total product count. Use this to verify data boundaries before running queries.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }
    ]


# ---------------------------------------------------------------------------
# Tool Handlers
# ---------------------------------------------------------------------------

DANGEROUS_KEYWORDS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE|EXECUTE|COPY|"
    r"pg_read_file|pg_write_file|pg_execute_server_program)\b",
    re.IGNORECASE
)


def handle_execute_sql(query: str, conn, sql_cache: dict | None = None) -> dict[str, Any]:
    """Validate and execute a read-only SQL query. Returns dict with columns, rows, row_count."""
    query = query.strip().rstrip(";").strip()

    # Remove SET search_path if the model included it
    query = re.sub(r"(?i)^SET\s+search_path\s+TO\s+\S+\s*;\s*", "", query).strip()

    if not query:
        return {"error": "Empty query"}

    # Safety: only SELECT allowed
    if not query.upper().lstrip().startswith("SELECT"):
        return {"error": "Only SELECT queries are allowed."}

    if DANGEROUS_KEYWORDS.search(query):
        return {"error": "Query contains forbidden keywords."}

    # Check SQL cache
    cache_key = hashlib.md5(query.encode()).hexdigest()
    if sql_cache is not None and cache_key in sql_cache:
        logger.info("SQL cache hit")
        cached = sql_cache[cache_key].copy()
        cached["cached"] = True
        return cached

    full_query = f"SET search_path TO {DB_SCHEMA}; {query}"

    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(full_query)
        rows = cur.fetchmany(MAX_ROWS)
        columns = [desc[0] for desc in cur.description] if cur.description else []
        total = cur.rowcount

        # Convert to serialisable types
        clean_rows = []
        for row in rows:
            clean = {}
            for k, v in row.items():
                if isinstance(v, (datetime, date)):
                    clean[k] = v.isoformat()
                elif hasattr(v, "as_integer_ratio"):  # Decimal / float
                    clean[k] = float(v)
                else:
                    clean[k] = v
            clean_rows.append(clean)

        cur.close()
        conn.rollback()  # ensure no transaction lingers

        result = {
            "columns": columns,
            "rows": clean_rows,
            "row_count": len(clean_rows),
            "total_rows": total,
        }
        if total > MAX_ROWS:
            result["note"] = f"Showing first {MAX_ROWS} of {total} rows."

        # Store in cache
        if sql_cache is not None:
            sql_cache[cache_key] = result

        return result

    except Exception as e:
        conn.rollback()
        return {"error": str(e)}


def handle_search_web(query: str) -> dict[str, Any]:
    """Search the web using Tavily API. Cached for 24 hours."""
    if not TAVILY_API_KEY:
        return {"error": "TAVILY_API_KEY not configured"}

    # Check cache (24h TTL)
    now = time.time()
    if query in _web_cache:
        ts, cached_result = _web_cache[query]
        if now - ts < CACHE_TTL_SECONDS:
            logger.info("Web search cache hit")
            cached = cached_result.copy()
            cached["cached"] = True
            return cached

    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": query,
                "max_results": 5,
                "include_answer": True,
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        results = []
        for r in data.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "snippet": r.get("content", "")[:500],
            })

        result = {
            "answer": data.get("answer", ""),
            "results": results,
        }

        # Store in cache
        _web_cache[query] = (now, result)

        return result
    except Exception as e:
        return {"error": f"Web search failed: {str(e)}"}


def handle_ask_perplexity(question: str) -> dict[str, Any]:
    """Ask Perplexity AI for a synthesized answer. Cached for 24 hours."""
    if not PERPLEXITY_API_KEY:
        return {"error": "PERPLEXITY_API_KEY not configured"}

    # Check cache (24h TTL)
    now = time.time()
    if question in _perplexity_cache:
        ts, cached_result = _perplexity_cache[question]
        if now - ts < CACHE_TTL_SECONDS:
            logger.info("Perplexity cache hit")
            cached = cached_result.copy()
            cached["cached"] = True
            return cached

    try:
        resp = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "sonar",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a retail market research assistant focused on the Portuguese market. Provide concise, well-sourced answers."
                    },
                    {"role": "user", "content": question}
                ],
                "max_tokens": 1024,
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        answer = data["choices"][0]["message"]["content"]
        citations = data.get("citations", [])
        result = {"answer": answer, "citations": citations}

        # Store in cache
        _perplexity_cache[question] = (now, result)

        return result
    except Exception as e:
        return {"error": f"Perplexity request failed: {str(e)}"}


def handle_get_data_context(conn) -> dict[str, Any]:
    """Return database metadata: date range, stores, product count. Cached until process restart."""
    global _data_context_cache

    if _data_context_cache is not None:
        logger.info("Data context cache hit")
        cached = _data_context_cache.copy()
        cached["cached"] = True
        return cached

    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(f"SET search_path TO {DB_SCHEMA};")

        # Date range
        cur.execute("SELECT MIN(date) AS min_date, MAX(date) AS max_date FROM da_stores_date;")
        dates = cur.fetchone()

        # Active stores
        cur.execute("SELECT id, name FROM stores WHERE status = 1 ORDER BY name;")
        stores = cur.fetchall()

        # Product count
        cur.execute("SELECT COUNT(*) AS cnt FROM items WHERE status = 1;")
        items = cur.fetchone()

        cur.close()
        conn.rollback()

        result = {
            "date_range": {
                "from": dates["min_date"].isoformat() if dates["min_date"] else None,
                "to": dates["max_date"].isoformat() if dates["max_date"] else None,
            },
            "active_stores": [{"id": s["id"], "name": s["name"]} for s in stores],
            "active_store_count": len(stores),
            "active_product_count": items["cnt"],
        }

        _data_context_cache = result
        return result
    except Exception as e:
        conn.rollback()
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def dispatch_tool(name: str, args: dict, conn, sql_cache: dict | None = None) -> dict[str, Any]:
    """Route a tool call to the correct handler."""
    if name == "execute_sql":
        return handle_execute_sql(args.get("query", ""), conn, sql_cache=sql_cache)
    elif name == "search_web":
        return handle_search_web(args.get("query", ""))
    elif name == "ask_perplexity":
        return handle_ask_perplexity(args.get("question", ""))
    elif name == "get_data_context":
        return handle_get_data_context(conn)
    else:
        return {"error": f"Unknown tool: {name}"}


def clear_caches():
    """Clear all module-level caches. Called on conversation reset."""
    global _data_context_cache
    _web_cache.clear()
    _perplexity_cache.clear()
    _data_context_cache = None


# ---------------------------------------------------------------------------
# Main Agent Loop
# ---------------------------------------------------------------------------

def run_agent(
    user_message: str,
    history: list[dict],
    conn,
    sql_cache: dict | None = None,
) -> tuple[str, list[dict], list[dict]]:
    """
    Main agent loop.

    Args:
        user_message: The user's question
        history: Conversation history (list of message dicts)
        conn: psycopg2 connection
        sql_cache: Optional dict for caching SQL results within session

    Returns:
        (final_text, updated_history, tool_call_log)
    """
    if not OPENROUTER_API_KEY:
        return "Error: OPENROUTER_API_KEY not configured.", history, []

    system_prompt = build_system_prompt()
    tools = get_tool_definitions()

    # Trim history to last N messages to cap input token growth
    trimmed_history = history[-MAX_HISTORY_MESSAGES:] if len(history) > MAX_HISTORY_MESSAGES else history

    # Build messages: system + trimmed history + new user message
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(trimmed_history)
    messages.append({"role": "user", "content": user_message})

    tool_call_log = []  # For UI display

    for iteration in range(MAX_ITERATIONS):
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": AGENT_MODEL,
                    "messages": messages,
                    "tools": tools,
                    "max_tokens": 4096,
                },
                timeout=120,
            )

            if resp.status_code != 200:
                error_msg = f"OpenRouter API error {resp.status_code}: {resp.text[:500]}"
                logger.error(error_msg)
                return error_msg, history, tool_call_log

            data = resp.json()
            choice = data["choices"][0]
            message = choice["message"]
            finish_reason = choice.get("finish_reason", "")

        except requests.exceptions.Timeout:
            return "Request timed out. Please try again.", history, tool_call_log
        except Exception as e:
            return f"API request failed: {str(e)}", history, tool_call_log

        # Append the assistant message to our messages list
        messages.append(message)

        # Check if the model wants to call tools
        tool_calls = message.get("tool_calls")

        if not tool_calls:
            # No tool calls — we have the final answer
            final_text = message.get("content", "")
            # Update history
            updated_history = history + [
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": final_text},
            ]
            return final_text, updated_history, tool_call_log

        # Execute each tool call
        for tc in tool_calls:
            fn_name = tc["function"]["name"]
            try:
                fn_args = json.loads(tc["function"]["arguments"])
            except json.JSONDecodeError:
                fn_args = {}

            logger.info(f"Tool call: {fn_name}({fn_args})")
            result = dispatch_tool(fn_name, fn_args, conn, sql_cache=sql_cache)

            # Log for UI
            tool_call_log.append({
                "tool": fn_name,
                "args": fn_args,
                "result": result,
                "iteration": iteration + 1,
            })

            # Append tool result as a message for the next iteration
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": json.dumps(result, ensure_ascii=False, default=str),
            })

    # Hit iteration limit
    last_content = messages[-1].get("content", "") if messages else ""
    fallback = last_content or "I reached the maximum number of reasoning steps. Here's what I found so far — please try a more specific question."
    updated_history = history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": fallback},
    ]
    return fallback, updated_history, tool_call_log
