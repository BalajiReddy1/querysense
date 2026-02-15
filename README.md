# ⚡ QuerySense — Multi-Agent SQL Optimizer

> **3 Agents Race. 1 Query Wins.**
> Paste a SQL query. Three specialized MCP agents compete simultaneously. A Judge picks the winner and synthesizes the ultimate query.

Built for the [2 Fast 2 MCP Hackathon](https://www.wemakedevs.org/hackathons/2fast2mcp) by WeMakeDevs × Archestra.ai

---

## 🎯 What It Does

QuerySense is a **multi-agent SQL optimization platform** powered by Archestra. You paste a bad SQL query, and three specialized agents race to fix it:

| Agent | Model | Focus |
|---|---|---|
| 🚀 Performance Agent | GPT-4o | Speed, indexes, execution plans |
| 💰 Cost Agent | Claude 3.5 Sonnet | Cloud spend, bytes scanned, compute |
| 🔒 Security Agent | GPT-4o-mini | SQL injection, data exposure, compliance |

A **Judge Agent** (GPT-4o) reviews all three reports, scores each agent, picks a winner, and synthesizes a **Final Unified SQL** combining the best ideas from all three.

Everything runs as MCP servers orchestrated through **Archestra**.

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
│  GPT-4o   Claude 3.5  GPT-4o-mini                  │
│    │         │          │                           │
│    └─────────┴──────────┘                           │
│              │                                      │
│              ▼                                      │
│         [⚖️ Judge] ← GPT-4o                        │
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
- OpenAI API key
- Anthropic API key
- Docker (for Archestra)

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/querysense
cd querysense

# Copy and fill in your API keys
cp .env.example .env
nano .env
```

### 2. Start Archestra

```bash
docker pull archestra/platform:latest
docker run -p 9000:9000 -p 3000:3000 \
  -e ARCHESTRA_QUICKSTART=true \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v archestra-postgres-data:/var/lib/postgresql/data \
  -v archestra-app-data:/app/data \
  archestra/platform
```

### 3. Start QuerySense

```bash
chmod +x start.sh
./start.sh
```

### 4. Open the UI

```
http://localhost:5000
```

### Alternative: Docker Compose

```bash
cp .env.example .env  # fill in API keys
docker-compose up --build
```

---

## 🎮 Demo

Open the UI and click any demo query button:

- **N+1 Classic** — Subquery causing repeated table scans
- **SELECT * Monster** — Multiple joins with wildcard selects
- **Missing Index Trap** — Aggregation on unindexed columns
- **SQL Injection** — Classic injection vulnerability
- **Cost Killer** — Cartesian join scanning everything

Watch all 3 agents analyze it simultaneously and the Judge declare a winner!

---

## 🔌 MCP Tools

Each agent exposes one MCP tool:

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
│   ├── performance_agent/server.py   # FastMCP + GPT-4o
│   ├── cost_agent/server.py          # FastMCP + Claude 3.5
│   ├── security_agent/server.py      # FastMCP + GPT-4o-mini
│   └── judge_agent/server.py         # FastMCP + GPT-4o
├── orchestrator/
│   └── main.py                       # FastAPI + SSE streaming
├── ui/
│   └── index.html                    # Single-file race UI
├── docker-compose.yml
├── requirements.txt
├── start.sh                          # One-command startup
├── ARCHESTRA_SETUP.md                # Archestra registration guide
└── .env.example
```

---

## ⚙️ Supported SQL Dialects

PostgreSQL, MySQL, BigQuery, Snowflake, Redshift, SQLite, Databricks

---

## 💡 Why Archestra?

QuerySense uses Archestra as its MCP control plane:

- **Multi-LLM orchestration** — 3 different models (OpenAI, Anthropic) managed centrally
- **Cost tracking** — Every agent call tracked, total race cost displayed
- **Security isolation** — Each agent runs isolated, preventing prompt injection
- **Private MCP Registry** — All 4 servers registered and governed centrally
- **Observability** — Full OTEL traces of the entire race
- **Built-in Chat** — QuerySense also works natively in Archestra's chat UI

---

## 🏆 Hackathon

Built for **2 Fast 2 MCP** by [WeMakeDevs](https://wemakedevs.org) × [Archestra.ai](https://archestra.ai)

Dates: February 8–15, 2025

Prize pool: $10,000+

---

## 📄 License

MIT
