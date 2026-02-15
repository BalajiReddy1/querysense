# QuerySense — Archestra Registration Guide

After starting all services with `./start.sh`, register all 4 MCP servers
in the Archestra platform at http://localhost:3000

## Step 1: Start Archestra

```bash
docker pull archestra/platform:latest
docker run -p 9000:9000 -p 3000:3000 \
  -e ARCHESTRA_QUICKSTART=true \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v archestra-postgres-data:/var/lib/postgresql/data \
  -v archestra-app-data:/app/data \
  archestra/platform
```

## Step 2: Add API Keys

1. Open http://localhost:3000
2. Go to Settings → LLM API Keys
3. Add OpenAI API key
4. Add Anthropic API key

## Step 3: Register MCP Servers

Go to MCP Registry → Add New → Custom/Self-hosted

Register these 4 servers:

### Performance Agent
- Name: `querysense-performance-agent`
- Description: Analyzes SQL for speed bottlenecks, rewrites for max performance using GPT-4o
- URL: `http://host.docker.internal:8001/mcp`
- Transport: streamable-http

### Cost Agent
- Name: `querysense-cost-agent`
- Description: Analyzes SQL for cloud cost inefficiencies using Claude 3.5 Sonnet
- URL: `http://host.docker.internal:8002/mcp`
- Transport: streamable-http

### Security Agent
- Name: `querysense-security-agent`
- Description: Analyzes SQL for injection risks and vulnerabilities using GPT-4o-mini
- URL: `http://host.docker.internal:8003/mcp`
- Transport: streamable-http

### Judge Agent
- Name: `querysense-judge-agent`
- Description: Reviews all 3 agent reports, picks winner, synthesizes ultimate SQL
- URL: `http://host.docker.internal:8004/mcp`
- Transport: streamable-http

## Step 4: Create QuerySense Agent in Archestra

1. Go to Agents → Create New Agent
2. Configure:
   - **Name**: QuerySense Orchestrator
   - **System Prompt**: (see below)
   - **Enable tools**: All 4 QuerySense MCP tools
   - **Model**: GPT-4o or Claude 3.5 Sonnet

**System Prompt:**
```
You are QuerySense, a multi-agent SQL optimization orchestrator.

When given a SQL query to analyze:
1. Call analyze_sql_performance to get performance insights
2. Call analyze_sql_cost to get cost optimization insights  
3. Call analyze_sql_security to get security vulnerability insights
4. Call judge_sql_results with all three reports to get the final verdict and unified SQL

Always present:
- Which agent won and why
- The final unified SQL
- The top improvements made
- The total cost of the analysis

You help data engineers write faster, cheaper, and safer SQL.
```

## Step 5: Test in Archestra Chat

1. Go to Chat
2. Select "QuerySense Orchestrator" agent
3. Paste this query:
   ```sql
   SELECT * FROM orders WHERE user_id IN (SELECT id FROM users)
   ```
4. Watch all 4 MCP tools fire in sequence!

## Architecture in Archestra

```
Archestra Chat UI
       │
       ▼
QuerySense Orchestrator Agent
       │
       ├── analyze_sql_performance → querysense-performance-agent (port 8001)
       ├── analyze_sql_cost        → querysense-cost-agent (port 8002)
       ├── analyze_sql_security    → querysense-security-agent (port 8003)
       └── judge_sql_results       → querysense-judge-agent (port 8004)
```

Archestra handles:
- ✅ Multi-LLM orchestration (GPT-4o + Claude + GPT-4o-mini)
- ✅ Cost tracking per agent call
- ✅ Security sub-agent isolation
- ✅ Observability (OTEL)
- ✅ Rate limiting and access control
