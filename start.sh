#!/bin/bash
# QuerySense — Start all agents + orchestrator
# Usage: ./start.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
ORANGE='\033[0;33m'
NC='\033[0m' # No Color

echo ""
echo "🏁 ═══════════════════════════════════════════════════"
echo "   QuerySense — Multi-Agent SQL Optimizer"
echo "   2 Fast 2 MCP Hackathon · Archestra.ai"
echo "═══════════════════════════════════════════════════════"
echo ""

# Load .env if it exists
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | xargs)
    echo -e "${GREEN}✅ Loaded .env${NC}"
else
    echo -e "${RED}❌ .env not found. Copy .env.example to .env and add your API keys.${NC}"
    exit 1
fi

# Check API keys
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "your_openai_api_key_here" ]; then
    echo -e "${RED}❌ OPENAI_API_KEY not set in .env${NC}"
    exit 1
fi

if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "your_anthropic_api_key_here" ]; then
    echo -e "${RED}❌ ANTHROPIC_API_KEY not set in .env${NC}"
    exit 1
fi

echo -e "${GREEN}✅ API keys verified${NC}"
echo ""

# Install dependencies
echo -e "${YELLOW}📦 Installing dependencies...${NC}"
pip install -r requirements.txt -q
echo -e "${GREEN}✅ Dependencies installed${NC}"
echo ""

# Create logs directory
mkdir -p logs

# Kill any existing processes on our ports
for port in 8001 8002 8003 8004 5000; do
    lsof -ti:$port | xargs kill -9 2>/dev/null || true
done

echo -e "${ORANGE}🚀 Starting Performance Agent (port 8001)...${NC}"
PYTHONPATH=. python mcp_servers/performance_agent/server.py > logs/performance.log 2>&1 &
PERF_PID=$!

echo -e "${BLUE}💰 Starting Cost Agent (port 8002)...${NC}"
PYTHONPATH=. python mcp_servers/cost_agent/server.py > logs/cost.log 2>&1 &
COST_PID=$!

echo -e "${RED}🔒 Starting Security Agent (port 8003)...${NC}"
PYTHONPATH=. python mcp_servers/security_agent/server.py > logs/security.log 2>&1 &
SEC_PID=$!

echo -e "${YELLOW}⚖️  Starting Judge Agent (port 8004)...${NC}"
PYTHONPATH=. python mcp_servers/judge_agent/server.py > logs/judge.log 2>&1 &
JUDGE_PID=$!

# Wait for agents to start
echo ""
echo -e "${YELLOW}⏳ Waiting for agents to boot...${NC}"
sleep 3

echo -e "${GREEN}🎯 Starting Orchestrator (port 5000)...${NC}"
cd orchestrator && PYTHONPATH=.. uvicorn main:app --host 0.0.0.0 --port 5000 --reload > ../logs/orchestrator.log 2>&1 &
ORCH_PID=$!
cd ..

sleep 2

echo ""
echo "═══════════════════════════════════════════════════════"
echo -e "${GREEN}✅ All services running!${NC}"
echo ""
echo "  🌐 QuerySense UI:   http://localhost:5000"
echo "  📊 API Health:      http://localhost:5000/health"
echo "  🎯 Orchestrator:    http://localhost:5000/docs"
echo ""
echo "  Agent Logs:         ./logs/"
echo ""
echo "  PIDs:"
echo "    Performance: $PERF_PID"
echo "    Cost:        $COST_PID"
echo "    Security:    $SEC_PID"
echo "    Judge:       $JUDGE_PID"
echo "    Orchestrator: $ORCH_PID"
echo ""
echo "  Press Ctrl+C to stop all services"
echo "═══════════════════════════════════════════════════════"

# Save PIDs for stop script
echo "$PERF_PID $COST_PID $SEC_PID $JUDGE_PID $ORCH_PID" > .pids

# Wait for any process to exit
wait
