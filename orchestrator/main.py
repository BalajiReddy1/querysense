"""
QuerySense — Orchestrator 🎯
FastAPI backend that fans out to all 3 agents in parallel,
then calls the Judge. Streams results via Server-Sent Events (SSE).
Uses FastMCP Client to call each agent.
"""

import os
import json
import time
import asyncio
import logging
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from fastmcp import Client

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("orchestrator")

app = FastAPI(
    title="QuerySense Orchestrator",
    description="Multi-agent SQL optimization platform",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Agent configuration - SSE transport
AGENTS = {
    "performance": {
        "url": f"http://localhost:{os.getenv('PERFORMANCE_AGENT_PORT', '8001')}/sse",
        "tool": "analyze_sql_performance",
        "label": "Performance Agent 🚀",
        "color": "orange",
    },
    "cost": {
        "url": f"http://localhost:{os.getenv('COST_AGENT_PORT', '8002')}/sse",
        "tool": "analyze_sql_cost",
        "label": "Cost Agent 💰",
        "color": "blue",
    },
    "security": {
        "url": f"http://localhost:{os.getenv('SECURITY_AGENT_PORT', '8003')}/sse",
        "tool": "analyze_sql_security",
        "label": "Security Agent 🔒",
        "color": "red",
    },
}

JUDGE_URL = f"http://localhost:{os.getenv('JUDGE_AGENT_PORT', '8004')}/sse"


class QueryRequest(BaseModel):
    query: str
    dialect: str = "postgresql"


def sse_event(data: dict) -> str:
    """Format a server-sent event."""
    return f"data: {json.dumps(data)}\n\n"


async def call_agent(url: str, tool_name: str, arguments: dict) -> dict:
    """Call an MCP agent tool using FastMCP Client over SSE."""
    async with Client(url) as client:
        result = await client.call_tool(tool_name, arguments)

        # FastMCP CallToolResult — extract text from .content list
        if hasattr(result, "content"):
            items = result.content
        elif isinstance(result, list):
            items = result
        else:
            # Last resort: stringify the whole result
            items = [result]

        # Get text from first content item
        if items:
            first = items[0]
            if hasattr(first, "text"):
                text = first.text
            else:
                text = str(first)
        else:
            raise ValueError("Empty response from agent")

        # Parse JSON
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
            raise ValueError(f"Could not parse JSON from response: {text[:300]}")


async def run_agent(agent_key: str, query: str, dialect: str) -> tuple:
    """Run a single agent and return (key, result, elapsed_time)."""
    agent = AGENTS[agent_key]
    start = time.time()
    result = await call_agent(
        agent["url"],
        agent["tool"],
        {"query": query, "dialect": dialect}
    )
    elapsed = round(time.time() - start, 2)
    return agent_key, result, elapsed


async def stream_race(query: str, dialect: str) -> AsyncGenerator[str, None]:
    """Core race logic — runs all agents in parallel and streams SSE events."""

    race_start = time.time()

    yield sse_event({
        "event": "race_start",
        "message": "🏁 Race started! 3 agents analyzing your SQL simultaneously...",
        "query_preview": query[:100] + ("..." if len(query) > 100 else ""),
        "dialect": dialect,
    })

    results = {}
    errors = {}

    # Create all 3 agent tasks to run simultaneously
    tasks = {
        agent_key: asyncio.create_task(run_agent(agent_key, query, dialect))
        for agent_key in AGENTS.keys()
    }

    pending = set(tasks.values())
    task_to_key = {v: k for k, v in tasks.items()}

    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

        for task in done:
            agent_key = task_to_key[task]
            agent_info = AGENTS[agent_key]

            try:
                _, result, elapsed = task.result()
                results[agent_key] = result

                yield sse_event({
                    "event": "agent_done",
                    "agent_key": agent_key,
                    "agent_label": agent_info["label"],
                    "agent_color": agent_info["color"],
                    "elapsed": elapsed,
                    "result": result,
                    "position": len(results)
                })

                logger.info(f"✅ {agent_info['label']} finished in {elapsed}s")

            except Exception as e:
                error_msg = str(e)
                errors[agent_key] = error_msg
                logger.error(f"❌ {agent_info['label']} failed: {error_msg}")

                results[agent_key] = {
                    "error": error_msg,
                    "agent": agent_info["label"],
                    "rewritten_sql": query,
                    "issues_found": [f"Agent error: {error_msg}"]
                }

                yield sse_event({
                    "event": "agent_error",
                    "agent_key": agent_key,
                    "agent_label": agent_info["label"],
                    "error": error_msg
                })

    # All agents done — call judge
    all_elapsed = round(time.time() - race_start, 2)

    yield sse_event({
        "event": "judging",
        "message": "⚖️ All agents finished! Judge is reviewing reports...",
        "agents_elapsed": all_elapsed
    })

    try:
        judge_start = time.time()
        verdict = await call_agent(
            JUDGE_URL,
            "judge_sql_results",
            {
                "original_query": query,
                "performance_report": results.get("performance", {}),
                "cost_report": results.get("cost", {}),
                "security_report": results.get("security", {})
            }
        )
        judge_elapsed = round(time.time() - judge_start, 2)
        total_elapsed = round(time.time() - race_start, 2)

        total_cost = sum([
            results.get(k, {}).get("cost_usd", 0)
            for k in ["performance", "cost", "security"]
        ]) + verdict.get("cost_usd", 0)

        yield sse_event({
            "event": "verdict",
            "verdict": verdict,
            "judge_elapsed": judge_elapsed,
            "total_elapsed": total_elapsed,
            "total_cost_usd": round(total_cost, 6),
            "had_errors": bool(errors)
        })

        logger.info(f"🏆 Race complete in {total_elapsed}s. Winner: {verdict.get('winner', 'unknown')}")

    except Exception as e:
        logger.error(f"Judge failed: {e}")
        yield sse_event({
            "event": "judge_error",
            "error": str(e),
            "message": "Judge encountered an error."
        })

    yield sse_event({"event": "done"})


@app.post("/analyze")
async def analyze(req: QueryRequest):
    """Stream SQL analysis from all 3 agents + judge verdict."""
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    if len(req.query) > 10000:
        raise HTTPException(status_code=400, detail="Query too long (max 10,000 chars)")

    return StreamingResponse(
        stream_race(req.query.strip(), req.dialect),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive"
        }
    )


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/demo-queries")
async def demo_queries():
    return {
        "queries": [
            {
                "name": "The N+1 Classic",
                "dialect": "postgresql",
                "sql": "SELECT *\nFROM orders o\nWHERE o.user_id IN (\n    SELECT id FROM users\n    WHERE created_at > '2024-01-01'\n    AND country = 'US'\n)\nORDER BY o.created_at DESC;"
            },
            {
                "name": "The SELECT * Monster",
                "dialect": "bigquery",
                "sql": "SELECT *\nFROM events e\nJOIN users u ON e.user_id = u.id\nJOIN products p ON e.product_id = p.id\nJOIN sessions s ON e.session_id = s.id\nWHERE e.event_type = 'purchase'\nAND YEAR(e.created_at) = 2024\nORDER BY e.created_at DESC;"
            },
            {
                "name": "The Missing Index Trap",
                "dialect": "postgresql",
                "sql": "SELECT customer_id, region, SUM(amount) AS total\nFROM transactions\nWHERE status = 'completed'\nAND created_at BETWEEN '2024-01-01' AND '2024-12-31'\nGROUP BY customer_id, region\nHAVING SUM(amount) > 1000\nORDER BY total DESC;"
            },
            {
                "name": "The SQL Injection",
                "dialect": "mysql",
                "sql": "SELECT id, username, email, password_hash, ssn\nFROM users\nWHERE username = '$username'\nUNION SELECT * FROM admin_users WHERE '1'='1';"
            },
            {
                "name": "The Cost Killer",
                "dialect": "snowflake",
                "sql": "SELECT DISTINCT u.*, o.*, p.*, r.*\nFROM users u, orders o, products p, reviews r\nWHERE u.id = o.user_id\nORDER BY u.created_at DESC;"
            }
        ]
    }


# Serve the UI — absolute path so it works from any working directory
import pathlib
_THIS_DIR = pathlib.Path(__file__).parent
_UI_DIR = _THIS_DIR.parent / "ui"
if _UI_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_UI_DIR), html=True), name="ui")
else:
    import warnings
    warnings.warn(f"UI directory not found at {_UI_DIR}")


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("ORCHESTRATOR_PORT", "5000"))
    logger.info(f"🎯 QuerySense Orchestrator starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")