"""
QuerySense — Security Agent 🔒
Analyzes SQL queries for security vulnerabilities.
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
logger = logging.getLogger("security-agent")

mcp = FastMCP(
    name="QuerySense Security Agent",
    instructions="I analyze SQL queries for security vulnerabilities, injection risks, and data exposure issues."
)

client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

SYSTEM_PROMPT = """You are a database security expert and SQL injection specialist. You've found critical vulnerabilities in Fortune 500 companies' data layers.

Analyze the given SQL query for security vulnerabilities:
1. SQL injection risks (string concatenation, dynamic SQL, unparameterized inputs)
2. Data over-exposure (SELECT * on sensitive tables, missing column filtering)
3. Privilege escalation risks
4. Data exfiltration patterns (UNION-based, subquery extraction)
5. Missing row-level security hints
6. Compliance issues (GDPR, HIPAA — PII/PHI exposure)
7. Rewrite using parameterized patterns and principle of least privilege

IMPORTANT: Return ONLY valid JSON, no markdown, no explanation outside the JSON.

Return this exact JSON structure:
{
  "risk_level": "Critical|High|Medium|Low|Safe",
  "vulnerabilities": ["list of specific vulnerabilities found"],
  "severity": "critical|high|medium|low",
  "rewritten_sql": "the security-hardened SQL query",
  "security_improvements": ["list of specific security changes made"],
  "compliance_notes": ["GDPR/HIPAA/SOC2 relevant observations"],
  "parameterization_example": "example of how to use this query safely with parameters",
  "agent": "Security Agent 🔒",
  "model": "llama-3.3-70b"
}"""


@mcp.tool(
    description="Analyze a SQL query for security vulnerabilities, injection risks, and data exposure issues"
)
async def analyze_sql_security(query: str, dialect: str = "postgresql") -> dict:
    """Analyze SQL query for security vulnerabilities."""
    logger.info(f"Security Agent analyzing query ({len(query)} chars)")

    try:
        response = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            temperature=0.1,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"SQL Dialect: {dialect}\n\nQuery to analyze:\n```sql\n{query}\n```"}
            ]
        )

        result = json.loads(response.choices[0].message.content)
        result["tokens_used"] = response.usage.total_tokens
        result["cost_usd"] = 0.0  # Groq is free!
        logger.info(f"Security Agent done. Risk level: {result.get('risk_level')}")
        return result

    except Exception as e:
        logger.error(f"Security Agent error: {e}")
        return {
            "error": str(e),
            "agent": "Security Agent 🔒",
            "model": "llama-3.3-70b",
            "risk_level": "Unknown",
            "vulnerabilities": [f"Error: {str(e)}"],
            "severity": "unknown",
            "rewritten_sql": query,
            "security_improvements": [],
            "compliance_notes": [],
            "parameterization_example": "",
            "cost_usd": 0.0
        }


if __name__ == "__main__":
    port = int(os.getenv("SECURITY_AGENT_PORT", "8003"))
    logger.info(f"🔒 Security Agent starting on port {port}")
    mcp.run(transport="sse", host="0.0.0.0", port=port)