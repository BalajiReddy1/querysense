"""
QuerySense — Orchestrator 🎯
FastAPI backend that fans out to all 3 agents in parallel,
then calls the Judge. Streams results via Server-Sent Events (SSE).
"""

import os
import json
import time
import asyncio
import logging
from typing import AsyncGenerator

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

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

# Agent configuration
AGENTS = {
    "performance": {
        "url": f"http://localhost:{os.getenv('PERFORMANCE_AGENT_PORT', '8001')}/mcp",
        "tool": "analyze_sql_performance",
        "label": "Performance Agent 🚀",
        "color": "orange",
        "args_key": "dialect"
    },
    "cost": {
        "url": f"http://localhost:{os.getenv('COST_AGENT_PORT', '8002')}/mcp",
        "tool": "analyze_sql_cost",
        "label": "Cost Agent 💰",
        "color": "blue",
        "args_key": "dialect"
    },
    "security": {
        "url": f"http://localhost:{os.getenv('SECURITY_AGENT_PORT', '8003')}/mcp",
        "tool": "analyze_sql_security",
        "label": "Security Agent 🔒",
        "color": "red",
        "args_key": "dialect"
    },
}

JUDGE_URL = f"http://localhost:{os.getenv('JUDGE_AGENT_PORT', '8004')}/mcp"


class QueryRequest(BaseModel):
    query: str
    dialect: str = "postgresql"


def sse_event(data: dict) -> str:
    """Format a server-sent event."""
    return f"data: {json.dumps(data)}\n\n"


async def call_mcp_tool(
    client: httpx.AsyncClient,
    url: str,
    tool_name: str,
    arguments: dict,
    timeout: float = 90.0
) -> dict:
    """Call an MCP tool via streamable-http transport."""
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    
    response = await client.post(
        url,
        json=payload,
        timeout=timeout,
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    )
    response.raise_for_status()
    
    data = response.json()
    
    if "error" in data:
        raise RuntimeError(f"MCP error: {data['error']}")
    
    # Extract content from MCP response structure
    content = data.get("result", {}).get("content", [])
    if content and len(content) > 0:
        text = content[0].get("text", "{}")
        return json.loads(text)
    
    raise ValueError("Empty response from MCP server")


async def run_agent(
    client: httpx.AsyncClient,
    agent_key: str,
    query: str,
    dialect: str
) -> tuple[str, dict, float]:
    """Run a single agent and return (key, result, elapsed_time)."""
    agent = AGENTS[agent_key]
    start = time.time()
    
    result = await call_mcp_tool(
        client,
        agent["url"],
        agent["tool"],
        {"query": query, "dialect": dialect}
    )
    
    elapsed = round(time.time() - start, 2)
    return agent_key, result, elapsed


async def stream_race(query: str, dialect: str) -> AsyncGenerator[str, None]:
    """Core race logic — runs all agents in parallel and streams SSE events."""
    
    race_start = time.time()
    
    # Announce race start
    yield sse_event({
        "event": "race_start",
        "message": "🏁 Race started! 3 agents analyzing your SQL simultaneously...",
        "query_preview": query[:100] + ("..." if len(query) > 100 else ""),
        "dialect": dialect,
        "timestamp": race_start
    })
    
    results = {}
    errors = {}
    
    async with httpx.AsyncClient() as client:
        
        # Create all 3 agent tasks to run simultaneously
        tasks = {
            agent_key: asyncio.create_task(run_agent(client, agent_key, query, dialect))
            for agent_key in AGENTS.keys()
        }
        
        # As tasks complete, stream their results
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
                        "position": len(results)  # 1st, 2nd, 3rd to finish
                    })
                    
                    logger.info(f"✅ {agent_info['label']} finished in {elapsed}s")
                    
                except Exception as e:
                    error_msg = str(e)
                    errors[agent_key] = error_msg
                    logger.error(f"❌ {agent_info['label']} failed: {error_msg}")
                    
                    # Use fallback result so judge still works
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
        
        # All agents done — call the judge
        all_elapsed = round(time.time() - race_start, 2)
        
        yield sse_event({
            "event": "judging",
            "message": "⚖️ All agents finished! Judge is reviewing reports...",
            "agents_elapsed": all_elapsed
        })
        
        try:
            judge_start = time.time()
            verdict = await call_mcp_tool(
                client,
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
            
            # Calculate total cost
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
                "message": "Judge encountered an error. Check agent results above."
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
    """Health check — verify all agents are reachable."""
    statuses = {}
    
    async with httpx.AsyncClient() as client:
        for key, agent in AGENTS.items():
            try:
                # Simple ping to check if server is up
                resp = await client.get(
                    agent["url"].replace("/mcp", "/health"),
                    timeout=3.0
                )
                statuses[key] = "ok"
            except Exception as e:
                statuses[key] = f"unreachable: {str(e)[:50]}"
        
        # Check judge
        try:
            resp = await client.get(JUDGE_URL.replace("/mcp", "/health"), timeout=3.0)
            statuses["judge"] = "ok"
        except Exception as e:
            statuses["judge"] = f"unreachable: {str(e)[:50]}"
    
    all_ok = all(v == "ok" for v in statuses.values())
    
    return {
        "status": "ok" if all_ok else "degraded",
        "agents": statuses,
        "version": "1.0.0"
    }


@app.get("/demo-queries")
async def demo_queries():
    """Return pre-loaded demo SQL queries."""
    return {
        "queries": [
            {
                "name": "The N+1 Classic",
                "dialect": "postgresql",
                "description": "Subquery in WHERE causing repeated scans",
                "sql": """SELECT *
FROM orders o
WHERE o.user_id IN (
    SELECT id FROM users
    WHERE created_at > '2024-01-01'
    AND country = 'US'
)
ORDER BY o.created_at DESC;"""
            },
            {
                "name": "The SELECT * Monster",
                "dialect": "bigquery",
                "description": "Multiple SELECT * with unnecessary JOIN",
                "sql": """SELECT *
FROM events e
JOIN users u ON e.user_id = u.id
JOIN products p ON e.product_id = p.id
JOIN sessions s ON e.session_id = s.id
WHERE e.event_type = 'purchase'
AND YEAR(e.created_at) = 2024
ORDER BY e.created_at DESC;"""
            },
            {
                "name": "The Missing Index Trap",
                "dialect": "postgresql",
                "description": "Aggregation on unindexed columns without partition",
                "sql": """SELECT
    customer_id,
    region,
    product_category,
    SUM(amount) AS total_revenue,
    COUNT(*) AS transaction_count,
    AVG(amount) AS avg_order_value
FROM transactions
WHERE status = 'completed'
AND created_at BETWEEN '2024-01-01' AND '2024-12-31'
GROUP BY customer_id, region, product_category
HAVING SUM(amount) > 1000
ORDER BY total_revenue DESC;"""
            },
            {
                "name": "The Security Nightmare",
                "dialect": "mysql",
                "description": "SQL injection vulnerable dynamic query",
                "sql": """SELECT id, username, email, password_hash, ssn, credit_card_number, 
       address, phone, date_of_birth, salary
FROM users 
WHERE username = '$username' 
AND status != 'banned'
UNION SELECT * FROM admin_users WHERE '1'='1';"""
            },
            {
                "name": "The Warehouse Cost Killer",
                "dialect": "snowflake",
                "description": "Cartesian join with no filters scanning everything",
                "sql": """SELECT DISTINCT
    u.id, u.name, u.email, u.created_at, u.updated_at,
    o.id AS order_id, o.total, o.status, o.created_at AS order_date,
    p.name AS product_name, p.price, p.category, p.description,
    r.rating, r.review_text, r.created_at AS review_date
FROM users u, orders o, products p, reviews r
WHERE u.id = o.user_id
ORDER BY u.created_at DESC;"""
            }
        ]
    }


# Serve UI from /ui directory
try:
    app.mount("/", StaticFiles(directory="ui", html=True), name="ui")
except Exception:
    pass  # UI directory may not exist in some deployments


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("ORCHESTRATOR_PORT", "5000"))
    logger.info(f"🎯 QuerySense Orchestrator starting on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
