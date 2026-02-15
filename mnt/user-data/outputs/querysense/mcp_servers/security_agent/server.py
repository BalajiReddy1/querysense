"""
QuerySense — Security Agent 🔒
Analyzes SQL queries for security vulnerabilities and rewrites with best practices.
Uses OpenAI GPT-4o-mini.
"""

import os
import json
import logging
from dotenv import load_dotenv
from fastmcp import FastMCP
import openai

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("security-agent")

mcp = FastMCP(
    name="QuerySense Security Agent",
    instructions="I analyze SQL queries for security vulnerabilities, injection risks, and data exposure issues."
)

SYSTEM_PROMPT = """You are a database security expert and SQL injection specialist. You've found critical vulnerabilities in Fortune 500 companies' data layers.

Analyze the given SQL query for security vulnerabilities:
1. SQL injection risks (string concatenation, dynamic SQL, unparameterized inputs)
2. Data over-exposure (SELECT * on sensitive tables, missing column filtering)
3. Privilege escalation risks (accessing tables beyond scope)
4. Data exfiltration patterns (UNION-based, subquery extraction)
5. Missing row-level security hints
6. Compliance issues (GDPR, HIPAA — PII/PHI exposure in SELECT)
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
  "model": "gpt-4o-mini"
}"""


@mcp.tool(
    description="Analyze a SQL query for security vulnerabilities, injection risks, and data exposure issues"
)
async def analyze_sql_security(
    query: str,
    dialect: str = "postgresql"
) -> dict:
    """
    Analyze SQL query for security vulnerabilities.
    
    Args:
        query: The SQL query to analyze
        dialect: SQL dialect (postgresql, mysql, mssql, sqlite)
    
    Returns:
        Dict with risk level, vulnerabilities found, hardened SQL, and compliance notes
    """
    logger.info(f"Security Agent analyzing query ({len(query)} chars, dialect: {dialect})")
    
    client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
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
        
        # gpt-4o-mini pricing: $0.00015/1K input, $0.0006/1K output
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cost = (input_tokens * 0.00000015) + (output_tokens * 0.0000006)
        
        result["tokens_used"] = response.usage.total_tokens
        result["cost_usd"] = round(cost, 6)
        
        logger.info(f"Security Agent done. Risk level: {result.get('risk_level', 'unknown')}")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return {
            "error": "Failed to parse response",
            "agent": "Security Agent 🔒",
            "model": "gpt-4o-mini",
            "risk_level": "Unknown",
            "vulnerabilities": ["Analysis failed - please retry"],
            "severity": "unknown",
            "rewritten_sql": query,
            "security_improvements": [],
            "compliance_notes": [],
            "parameterization_example": ""
        }
    except Exception as e:
        logger.error(f"Security Agent error: {e}")
        raise


if __name__ == "__main__":
    port = int(os.getenv("SECURITY_AGENT_PORT", "8003"))
    logger.info(f"🔒 Security Agent starting on port {port}")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=port, path="/mcp")
