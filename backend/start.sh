#!/bin/bash

# Railway Traffic Management System - Startup Script
# This script starts all services needed for the Controller Action APIs

set -e  # Exit on error

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Railway Traffic Management System - Startup${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════${NC}"
echo ""

# Step 1: Check Docker services
echo -e "${YELLOW}[1/5] Checking Docker services...${NC}"
cd /home/auxilus/sih

if ! docker compose ps | grep -q "Up"; then
    echo -e "${YELLOW}→ Starting Docker services...${NC}"
    docker compose up -d postgres redis
    echo -e "${GREEN}✓ Docker services started${NC}"
else
    echo -e "${GREEN}✓ Docker services already running${NC}"
fi

# Wait for services to be healthy
echo -e "${YELLOW}→ Waiting for services to be healthy...${NC}"
sleep 3

# Step 2: Activate virtual environment
echo ""
echo -e "${YELLOW}[2/5] Setting up Python environment...${NC}"
cd /home/auxilus/sih/backend

if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}→ Creating virtual environment...${NC}"
    python3 -m venv .venv
fi

source .venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Step 3: Install dependencies
echo ""
echo -e "${YELLOW}[3/5] Installing Python dependencies...${NC}"
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Step 4: Check database setup
echo ""
echo -e "${YELLOW}[4/5] Checking database setup...${NC}"

# Check if tables exist
if python -c "from app.db import get_engine; from sqlalchemy import inspect; engine = get_engine(); inspector = inspect(engine); tables = inspector.get_table_names(); exit(0 if len(tables) > 0 else 1)" 2>/dev/null; then
    echo -e "${GREEN}✓ Database tables exist${NC}"
else
    echo -e "${YELLOW}→ Creating database tables...${NC}"
    python create_tables.py
    echo -e "${GREEN}✓ Database tables created${NC}"
fi

# Check if controllers exist
if python -c "from app.db import get_engine; from app.models import Controller; from sqlalchemy.orm import Session; engine = get_engine(); session = Session(engine); controllers = session.query(Controller).all(); session.close(); exit(0 if len(controllers) > 0 else 1)" 2>/dev/null; then
    CONTROLLER_COUNT=$(python -c "from app.db import get_engine; from app.models import Controller; from sqlalchemy.orm import Session; engine = get_engine(); session = Session(engine); controllers = session.query(Controller).all(); print(len(controllers)); session.close()" 2>/dev/null)
    echo -e "${GREEN}✓ Found $CONTROLLER_COUNT controllers in database${NC}"
else
    echo -e "${YELLOW}→ No controllers found. Run 'python setup_auth.py' to create demo controllers${NC}"
fi

# Step 5: Start the server
echo ""
echo -e "${YELLOW}[5/5] Starting FastAPI server...${NC}"
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   Server starting on http://localhost:8000${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}📚 Documentation:${NC}"
echo -e "   Swagger UI: ${BLUE}http://localhost:8000/docs${NC}"
echo -e "   ReDoc:      ${BLUE}http://localhost:8000/redoc${NC}"
echo -e "   Health:     ${BLUE}http://localhost:8000/api/health${NC}"
echo ""
echo -e "${BLUE}🧪 Testing:${NC}"
echo -e "   Run automated tests: ${YELLOW}./test_controller_api.sh${NC}"
echo ""
echo -e "${BLUE}🔑 Demo Credentials:${NC}"
echo -e "   employee_id: CTR001, password: password_CTR001"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
