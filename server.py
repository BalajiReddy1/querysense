"""
QuerySense — Performance Agent 🚀
Analyzes SQL queries for speed bottlenecks and rewrites for maximum performance.
Uses OpenAI GPT-4o.
"""

import os
import json
import logging
from dotenv import load_dotenv
from fastmcp import FastMCP
import openai

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("performance-agent")

mcp = FastMCP(
    name="QuerySense Performance Agent",
    instructions="I analyze SQL queries for performance bottlenecks and rewrite them for maximum speed."
)

SYSTEM_PROMPT = """You are an elite SQL performance engineer with 20+ years of experience optimizing queries at scale.

Analyze the given SQL query and:
1. Identify ALL performance bottlenecks (missing indexes, N+1 patterns, full table scans, unnecessary subqueries, missing LIMIT clauses, expensive ORDER BY on unindexed columns, implicit type conversions, etc.)
2. Rewrite the query for maximum execution speed
3. Explain each specific change and WHY it helps
4. Estimate relative speedup (e.g., "2-5x faster", "10x+ faster")
5. Suggest indexes that would further help this query

IMPORTANT: Return ONLY valid JSON, no markdown, no explanation outside the JSON.

Return this exact JSON structure:
{
  "issues_found": ["list of specific problems identified"],
  "severity": "critical|high|medium|low",
  "original_rating": "Poor|Fair|Good|Excellent",
  "rewritten_sql": "the optimized SQL query",
  "changes_made": ["list of specific changes with reasons"],
  "estimated_speedup": "e.g. 5-10x faster",
  "index_suggestions": ["CREATE INDEX suggestions"],
  "agent": "Performance Agent 🚀",
  "model": "gpt-4o"
}"""


@mcp.tool(
    description="Analyze a SQL query for performance bottlenecks and rewrite it for maximum speed"
)
async def analyze_sql_performance(
    query: str,
    dialect: str = "postgresql"
) -> dict:
    """
    Analyze SQL query for performance issues.
    
    Args:
        query: The SQL query to analyze
        dialect: SQL dialect (postgresql, mysql, bigquery, snowflake, sqlite)
    
    Returns:
        Dict with issues, rewritten SQL, changes made, and speedup estimate
    """
    logger.info(f"Performance Agent analyzing query ({len(query)} chars, dialect: {dialect})")
    
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            temperature=0.1,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"SQL Dialect: {dialect}\n\nQuery to analyze:\n```sql\n{query}\n```"
                }
            ]
        )
        
        result = json.loads(response.choices[0].message.content)
        result["tokens_used"] = response.usage.total_tokens
        result["cost_usd"] = round(response.usage.total_tokens * 0.0000025, 6)  # GPT-4o pricing
        
        logger.info(f"Performance Agent done. Severity: {result.get('severity', 'unknown')}")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return {
            "error": "Failed to parse response",
            "agent": "Performance Agent 🚀",
            "model": "gpt-4o",
            "issues_found": ["Analysis failed - please retry"],
            "severity": "unknown",
            "original_rating": "Unknown",
            "rewritten_sql": query,
            "changes_made": [],
            "estimated_speedup": "N/A",
            "index_suggestions": []
        }
    except Exception as e:
        logger.error(f"Performance Agent error: {e}")
        raise


if __name__ == "__main__":
    port = int(os.getenv("PERFORMANCE_AGENT_PORT", "8001"))
    logger.info(f"🚀 Performance Agent starting on port {port}")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port, path="/mcp")
