"""
QuerySense — Cost Agent 💰
Analyzes SQL queries for cloud data warehouse cost inefficiencies.
Uses Groq (FREE) - llama-3.3-70b-versatile
"""

import os
import json
import logging
from dotenv import load_dotenv
from fastmcp import FastMCP
from openai import AsyncOpenAI

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cost-agent")

mcp = FastMCP(
    name="QuerySense Cost Agent",
    instructions="I analyze SQL queries for cloud cost inefficiencies and rewrite them to minimize data scanned and compute used."
)

client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

SYSTEM_PROMPT = """You are a cloud data warehouse cost optimization specialist. You've saved companies millions in BigQuery, Snowflake, Redshift, and Databricks bills.

Analyze the given SQL query for cost inefficiencies:
1. Identify expensive operations (SELECT *, missing partition filters, no LIMIT, unbounded JOINs, scanning huge tables unnecessarily, using DISTINCT when unnecessary, etc.)
2. Estimate the cost impact: Low (<$1/run), Medium ($1-10/run), High ($10-100/run), Very High (>$100/run)
3. Rewrite to minimize bytes scanned and compute used
4. Calculate estimated cost reduction percentage
5. List partitioning/clustering strategies that would help

IMPORTANT: Return ONLY valid JSON, no markdown, no explanation outside the JSON.

Return this exact JSON structure:
{
  "cost_rating": "Low|Medium|High|Very High",
  "expensive_operations": ["list of specific cost-driving operations"],
  "severity": "critical|high|medium|low",
  "rewritten_sql": "the cost-optimized SQL query",
  "savings_explanation": ["list of specific changes with cost impact"],
  "estimated_cost_reduction_pct": "e.g. 70-85%",
  "partitioning_suggestions": ["partitioning/clustering recommendations"],
  "agent": "Cost Agent 💰",
  "model": "llama-3.3-70b"
}"""


@mcp.tool(
    description="Analyze a SQL query for cloud cost inefficiencies and rewrite it to minimize compute and data scanned"
)
async def analyze_sql_cost(query: str, dialect: str = "bigquery") -> dict:
    """Analyze SQL query for cost optimization opportunities."""
    logger.info(f"Cost Agent analyzing query ({len(query)} chars)")

    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            temperature=0.1,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"SQL Dialect/Warehouse: {dialect}\n\nQuery to analyze:\n```sql\n{query}\n```"}
            ]
        )

        result = json.loads(response.choices[0].message.content)
        result["tokens_used"] = response.usage.total_tokens
        result["cost_usd"] = 0.0  # Groq is free!
        logger.info(f"Cost Agent done. Cost rating: {result.get('cost_rating')}")
        return result

    except Exception as e:
        logger.error(f"Cost Agent error: {e}")
        return {
            "error": str(e),
            "agent": "Cost Agent 💰",
            "model": "llama-3.3-70b",
            "cost_rating": "Unknown",
            "expensive_operations": [f"Error: {str(e)}"],
            "severity": "unknown",
            "rewritten_sql": query,
            "savings_explanation": [],
            "estimated_cost_reduction_pct": "N/A",
            "partitioning_suggestions": [],
            "cost_usd": 0.0
        }


if __name__ == "__main__":
    port = int(os.getenv("COST_AGENT_PORT", "8002"))
    logger.info(f"💰 Cost Agent starting on port {port}")
    mcp.run(transport="sse", host="0.0.0.0", port=port)