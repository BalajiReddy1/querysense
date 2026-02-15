# ⚡ QuerySense — Multi-Agent SQL Optimizer

> **3 Agents Race. 1 Query Wins.**
> Paste a SQL query. Three specialized MCP agents compete simultaneously. A Judge picks the winner and synthesizes the ultimate query.

Built for the [2 Fast 2 MCP Hackathon](https://www.wemakedevs.org/hackathons/2fast2mcp) by WeMakeDevs × Archestra.ai

---

## 🎯 What It Does

QuerySense is a **multi-agent SQL optimization platform** powered by Archestra. You paste a bad SQL query, and three specialized agents race to fix it:

| Agent | Model | Focus |
|---|---|---|
| 🚀 Performance Agent | Llama 3.3 70B (Groq) | Speed, indexes, execution plans |
| 💰 Cost Agent | Llama 3.3 70B (Groq) | Cloud spend, bytes scanned, compute |
| 🔒 Security Agent | Llama 3.3 70B (Groq) | SQL injection, data exposure, compliance |

A **Judge Agent** (Llama 3.3 70B) reviews all three reports, scores each agent, picks a winner, and synthesizes a **Final Unified SQL** combining the best ideas from all three.

Everything runs as MCP servers orchestrated through **Archestra**.

**Total cost per race: $0.00** — runs entirely on Groq's free tier.

---

## 🏗️ Architecture

```
User pastes SQL query
         │
         ▼
┌─────────────────────────────────────────────────────┐
│                  Archestra Platform                  │
│                                                     │
│   QuerySense Orchestrator Agent                     │
│              │                                      │
│    ┌─────────┼──────────┐                           │
│    ▼         ▼          ▼   (parallel execution)    │
│  [🚀 Perf]  [💰 Cost] [🔒 Sec]                     │
│  Llama 3.3  Llama 3.3  Llama 3.3                   │
│    │         │          │                           │
│    └─────────┴──────────┘                           │
│              │                                      │
│              ▼                                      │
│         [⚖️ Judge] ← Llama 3.3                     │
│    Picks winner + Final SQL                         │
└─────────────────────────────────────────────────────┘
         │
         ▼
  Live race UI + Archestra Chat
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Groq API key (free) — get one at https://console.groq.com
- Docker (for Archestra, optional)

### 1. Clone & Setup

```bash
git clone https://github.com/BalajiReddy1/querysense
cd querysense

cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

`.env` should look like:
```
GROQ_API_KEY=your_groq_api_key_here

PERFORMANCE_AGENT_PORT=8001
COST_AGENT_PORT=8002
SECURITY_AGENT_PORT=8003
JUDGE_AGENT_PORT=8004
ORCHESTRATOR_PORT=5000
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start all agents

Open 5 terminals and run one command in each:

```bash
# Terminal 1
cd mcp_servers/performance_agent && python server.py

# Terminal 2
cd mcp_servers/cost_agent && python server.py

# Terminal 3
cd mcp_servers/security_agent && python server.py

# Terminal 4
cd mcp_servers/judge_agent && python server.py

# Terminal 5 — run from project ROOT
uvicorn orchestrator.main:app --host 0.0.0.0 --port 5000 --reload
```

### 4. Open the UI

```
http://localhost:5000
```

### Optional: Start Archestra

```bash
docker pull archestra/platform:latest
docker run -p 9000:9000 -p 3000:3000 \
  -e ARCHESTRA_QUICKSTART=true \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v archestra-postgres-data:/var/lib/postgresql/data \
  -v archestra-app-data:/app/data \
  archestra/platform
```

Then follow `ARCHESTRA_SETUP.md` to register all 4 MCP servers.

---

## 🎮 Demo Queries

Click any demo button in the UI:

- **N+1 Classic** — Subquery causing repeated table scans
- **SELECT * Monster** — Multiple joins with wildcard selects
- **Missing Index Trap** — Aggregation on unindexed columns
- **SQL Injection** — Classic injection vulnerability
- **Cost Killer** — Cartesian join scanning everything

---

## 🔌 MCP Tools

Each agent exposes one MCP tool via SSE transport:

| Server | Tool | Port |
|---|---|---|
| Performance Agent | `analyze_sql_performance(query, dialect)` | 8001 |
| Cost Agent | `analyze_sql_cost(query, dialect)` | 8002 |
| Security Agent | `analyze_sql_security(query, dialect)` | 8003 |
| Judge Agent | `judge_sql_results(original, perf, cost, sec)` | 8004 |

All registered in Archestra's Private MCP Registry.

---

## 📁 Project Structure

```
querysense/
├── mcp_servers/
│   ├── performance_agent/server.py   # FastMCP + Llama 3.3 via Groq
│   ├── cost_agent/server.py          # FastMCP + Llama 3.3 via Groq
│   ├── security_agent/server.py      # FastMCP + Llama 3.3 via Groq
│   └── judge_agent/server.py         # FastMCP + Llama 3.3 via Groq
├── orchestrator/
│   └── main.py                       # FastAPI + SSE streaming
├── ui/
│   └── index.html                    # Single-file race UI
├── docker-compose.yml
├── requirements.txt
├── ARCHESTRA_SETUP.md
└── .env.example
```

---

## ⚙️ Supported SQL Dialects

PostgreSQL, MySQL, BigQuery, Snowflake, Redshift, SQLite, Databricks

---

## 💡 Why Archestra?

QuerySense uses Archestra as its MCP control plane:

- **Multi-agent orchestration** — 4 MCP servers managed and governed centrally
- **Cost tracking** — Every agent call tracked, total race cost displayed
- **Security isolation** — Each agent runs isolated, preventing prompt injection
- **Private MCP Registry** — All 4 servers registered and shared org-wide
- **Observability** — Full OTEL traces of the entire race
- **Built-in Chat** — QuerySense also works natively inside Archestra's chat UI

---

## 🏆 Hackathon

Built for **2 Fast 2 MCP** by [WeMakeDevs](https://wemakedevs.org) × [Archestra.ai](https://archestra.ai)

Dates: February 8–15, 2025 

---

## 📄 License

MIT