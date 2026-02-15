"""
QuerySense — Cost Agent 💰
Analyzes SQL queries for cloud data warehouse cost inefficiencies.
Uses Anthropic Claude 3.5 Sonnet.
"""

import os
import re
import json
import logging
from dotenv import load_dotenv
from fastmcp import FastMCP
import anthropic

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cost-agent")

mcp = FastMCP(
    name="QuerySense Cost Agent",
    instructions="I analyze SQL queries for cloud cost inefficiencies and rewrite them to minimize data scanned and compute used."
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
  "model": "claude-3-5-sonnet"
}"""


@mcp.tool(
    description="Analyze a SQL query for cloud cost inefficiencies and rewrite it to minimize compute and data scanned"
)
async def analyze_sql_cost(
    query: str,
    dialect: str = "bigquery"
) -> dict:
    """
    Analyze SQL query for cost optimization opportunities.
    
    Args:
        query: The SQL query to analyze
        dialect: SQL dialect / warehouse (bigquery, snowflake, redshift, databricks)
    
    Returns:
        Dict with cost rating, expensive operations, rewritten SQL, and savings estimate
    """
    logger.info(f"Cost Agent analyzing query ({len(query)} chars, dialect: {dialect})")
    
    client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    try:
        response = await client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            temperature=0.1,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": f"SQL Dialect/Warehouse: {dialect}\n\nQuery to analyze:\n```sql\n{query}\n```\n\nRespond with JSON only."
                }
            ]
        )
        
        text = response.content[0].text.strip()
        
        # Strip markdown code blocks if present
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        
        # Find JSON object
        start = text.find('{')
        end = text.rfind('}') + 1
        if start >= 0 and end > start:
            result = json.loads(text[start:end])
        else:
            raise ValueError("No JSON object found in response")
        
        # Add token/cost metadata
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        total_tokens = input_tokens + output_tokens
        # Claude 3.5 Sonnet pricing: ~$0.003/1K input, $0.015/1K output
        cost = (input_tokens * 0.000003) + (output_tokens * 0.000015)
        
        result["tokens_used"] = total_tokens
        result["cost_usd"] = round(cost, 6)
        
        logger.info(f"Cost Agent done. Cost rating: {result.get('cost_rating', 'unknown')}")
        return result
        
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"JSON parse error: {e}")
        return {
            "error": "Failed to parse response",
            "agent": "Cost Agent 💰",
            "model": "claude-3-5-sonnet",
            "cost_rating": "Unknown",
            "expensive_operations": ["Analysis failed - please retry"],
            "severity": "unknown",
            "rewritten_sql": query,
            "savings_explanation": [],
            "estimated_cost_reduction_pct": "N/A",
            "partitioning_suggestions": []
        }
    except Exception as e:
        logger.error(f"Cost Agent error: {e}")
        raise


if __name__ == "__main__":
    port = int(os.getenv("COST_AGENT_PORT", "8002"))
    logger.info(f"💰 Cost Agent starting on port {port}")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port, path="/mcp")
