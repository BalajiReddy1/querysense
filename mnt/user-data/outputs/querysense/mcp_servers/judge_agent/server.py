"""
QuerySense — Judge Agent ⚖️
Reviews all 3 agent reports, picks a winner, and synthesizes the ultimate SQL.
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
logger = logging.getLogger("judge-agent")

mcp = FastMCP(
    name="QuerySense Judge Agent",
    instructions="I review reports from 3 SQL specialist agents, pick the best approach, and synthesize the ultimate optimized query."
)

SYSTEM_PROMPT = """You are the Chief SQL Architect and head judge of the QuerySense optimization competition.

You receive:
1. The original SQL query (the problem)
2. A Performance Agent report (focused on speed)
3. A Cost Agent report (focused on cloud spend)
4. A Security Agent report (focused on safety)

Your job as judge:
1. Evaluate each agent's rewritten SQL holistically — not just on their specialty, but on overall quality
2. Score each agent 1-10 across: correctness, improvement quality, practicality, completeness
3. Declare ONE winner (who had the best overall approach)
4. Write a clear, opinionated verdict explaining the decision
5. Create a FINAL UNIFIED SQL that takes the BEST ideas from ALL three agents — this is the crown jewel
6. Summarize the top 5 improvements in the final SQL vs the original

IMPORTANT: Return ONLY valid JSON, no markdown, no explanation outside the JSON.

Return this exact JSON structure:
{
  "winner": "Performance Agent 🚀|Cost Agent 💰|Security Agent 🔒",
  "winner_reason": "1-2 sentence explanation of why this agent won",
  "scores": {
    "Performance Agent 🚀": {"score": 8, "comment": "short comment"},
    "Cost Agent 💰": {"score": 7, "comment": "short comment"},
    "Security Agent 🔒": {"score": 6, "comment": "short comment"}
  },
  "verdict": "Full 3-4 sentence judge's verdict explaining the decision and what made each agent stand out",
  "final_sql": "The ultimate unified SQL combining best ideas from all agents",
  "final_sql_explanation": "2-3 sentence explanation of what the final SQL incorporates",
  "top_improvements": [
    "improvement 1 (from which agent)",
    "improvement 2 (from which agent)",
    "improvement 3 (from which agent)",
    "improvement 4 (from which agent)",
    "improvement 5 (from which agent)"
  ],
  "overall_query_health": "Poor|Fair|Good|Excellent",
  "agent": "Judge Agent ⚖️",
  "model": "gpt-4o"
}"""


@mcp.tool(
    description="Judge the 3 agent SQL reports, pick a winner, and synthesize the ultimate optimized query"
)
async def judge_sql_results(
    original_query: str,
    performance_report: dict,
    cost_report: dict,
    security_report: dict
) -> dict:
    """
    Judge all three agent reports and produce final verdict + unified SQL.
    
    Args:
        original_query: The original SQL query that was analyzed
        performance_report: Report from the Performance Agent
        cost_report: Report from the Cost Agent
        security_report: Report from the Security Agent
    
    Returns:
        Dict with winner, scores, verdict, final unified SQL, and top improvements
    """
    logger.info("Judge Agent reviewing all reports...")
    
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    context = f"""ORIGINAL QUERY (The Problem):
```sql
{original_query}
```

---
PERFORMANCE AGENT REPORT:
{json.dumps(performance_report, indent=2)}

---
COST AGENT REPORT:
{json.dumps(cost_report, indent=2)}

---
SECURITY AGENT REPORT:
{json.dumps(security_report, indent=2)}
"""
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            response_format={"type": "json_object"},
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context}
            ]
        )
        
        result = json.loads(response.choices[0].message.content)
        result["tokens_used"] = response.usage.total_tokens
        result["cost_usd"] = round(response.usage.total_tokens * 0.0000025, 6)
        
        logger.info(f"Judge verdict: {result.get('winner', 'unknown')} wins!")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return {
            "error": "Failed to parse judge response",
            "agent": "Judge Agent ⚖️",
            "model": "gpt-4o",
            "winner": "Performance Agent 🚀",
            "winner_reason": "Default fallback",
            "scores": {
                "Performance Agent 🚀": {"score": 7, "comment": "N/A"},
                "Cost Agent 💰": {"score": 7, "comment": "N/A"},
                "Security Agent 🔒": {"score": 7, "comment": "N/A"}
            },
            "verdict": "Judgment failed due to parsing error.",
            "final_sql": original_query,
            "final_sql_explanation": "N/A",
            "top_improvements": [],
            "overall_query_health": "Unknown"
        }
    except Exception as e:
        logger.error(f"Judge Agent error: {e}")
        raise


if __name__ == "__main__":
    port = int(os.getenv("JUDGE_AGENT_PORT", "8004"))
    logger.info(f"⚖️  Judge Agent starting on port {port}")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port, path="/mcp")
