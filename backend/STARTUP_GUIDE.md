# 🚀 Controller APIs - Complete Startup Guide

This guide walks you through starting the Railway Traffic Management System with the new Controller Action APIs.

---

## 📋 Prerequisites

Before starting, ensure you have:

- ✅ Docker and Docker Compose installed
- ✅ Python 3.8+ installed
- ✅ PostgreSQL (via Docker)
- ✅ Redis (via Docker)

---

## 🔧 Step-by-Step Startup

### **Step 1: Start Docker Services**

```bash
cd /home/auxilus/sih

# Start PostgreSQL and Redis
docker compose up -d postgres redis

# Verify services are running
docker compose ps

# You should see:
# - postgres (port 5432)
# - redis (port 6379)
```

### **Step 2: Set Up Python Environment**

```bash
cd /home/auxilus/sih/backend

# Activate virtual environment (if you have one)
source .venv/bin/activate  # or your venv path

# Install/update dependencies
pip install -r requirements.txt
```

### **Step 3: Initialize Database**

```bash
cd /home/auxilus/sih/backend

# Create database tables
python create_tables.py

# (Optional) Seed with demo data
python seed_data.py

# (Optional) Create demo controller passwords
python setup_auth.py
```

### **Step 4: Start the Backend Server**

```bash
cd /home/auxilus/sih/backend

# Start FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# You should see:
# INFO:     Uvicorn running on http://0.0.0.0:8000
# INFO:     Application startup complete.
```

**Keep this terminal open** - the server needs to keep running.

### **Step 5: Test the APIs**

Open a **new terminal** and run:

```bash
cd /home/auxilus/sih/backend

# Run automated test suite
./test_controller_api.sh

# Or test manually with curl
curl http://localhost:8000/api/health
```

### **Step 6: View Interactive Documentation**

Open your browser and navigate to:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## 🐳 Quick Docker Commands

### Start Services
```bash
cd /home/auxilus/sih
docker compose up -d postgres redis
```

### Check Status
```bash
docker compose ps
docker compose logs postgres
docker compose logs redis
```

### Stop Services
```bash
docker compose down
```

### Restart Services
```bash
docker compose restart postgres redis
```

### View Logs
```bash
docker compose logs -f postgres
docker compose logs -f redis
```

---

## 🧪 Testing the Controller APIs

### Method 1: Automated Test Script

```bash
cd /home/auxilus/sih/backend
./test_controller_api.sh
```

This will run 13 comprehensive tests covering:
- Authentication
- Active conflicts
- Conflict resolution
- Train control
- Decision logging
- Audit trail
- Rate limiting
- Authorization
- Input validation

### Method 2: Interactive API Docs

1. Open http://localhost:8000/docs
2. Click "Authorize" button
3. Login to get token:
   - POST `/api/auth/login`
   - Use: `employee_id: CTR001`, `password: password_CTR001`
4. Copy the `access_token`
5. Click "Authorize" and enter: `Bearer YOUR_TOKEN`
6. Test any endpoint!

### Method 3: Manual cURL Commands

```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"employee_id":"CTR001","password":"password_CTR001"}' \
  | jq -r '.access_token')

# 2. Get active conflicts
curl http://localhost:8000/api/conflicts/active \
  -H "Authorization: Bearer $TOKEN" | jq

# 3. Query audit trail
curl "http://localhost:8000/api/audit/decisions?limit=10" \
  -H "Authorization: Bearer $TOKEN" | jq
```

---

## 🔑 Demo Controller Credentials

If you ran `setup_auth.py`, you should have these demo accounts:

| Employee ID | Password | Auth Level | Sections |
|-------------|----------|------------|----------|
| CTR001 | password_CTR001 | Supervisor | 1, 2, 3 |
| CTR002 | password_CTR002 | Supervisor | 2, 3, 4 |
| CTR003 | password_CTR003 | Manager | 1, 2, 3, 4 |
| ADM001 | password_ADM001 | Admin | All |

Use any of these to test the APIs with different permission levels.

---

## 🐛 Troubleshooting

### Problem: "Connection refused" or "Cannot connect to database"

**Solution:**
```bash
# Check if Docker services are running
docker compose ps

# If not running, start them
docker compose up -d postgres redis

# Check logs for errors
docker compose logs postgres
```

### Problem: "Login failed" or "Invalid credentials"

**Solution:**
```bash
# Run setup script to create demo passwords
cd /home/auxilus/sih/backend
python setup_auth.py

# Or check if controllers exist
python -c "
from app.db import get_engine
from sqlalchemy.orm import Session
from app.models import Controller

engine = get_engine()
with Session(engine) as session:
    controllers = session.query(Controller).all()
    print(f'Found {len(controllers)} controllers')
    for c in controllers:
        print(f'  - {c.employee_id}: {c.name} ({c.auth_level.value})')
"
```

### Problem: "Module not found" errors

**Solution:**
```bash
cd /home/auxilus/sih/backend

# Reinstall dependencies
pip install -r requirements.txt

# Or install specific missing modules
pip install fastapi uvicorn sqlalchemy pydantic python-jose bcrypt redis
```

### Problem: "Port already in use"

**Solution:**
```bash
# Check what's using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or use a different port
uvicorn app.main:app --reload --port 8001
```

### Problem: Redis connection errors

**Solution:**
```bash
# Check Redis is running
docker compose ps redis

# Restart Redis
docker compose restart redis

# Check Redis logs
docker compose logs redis
```

### Problem: Database migrations needed

**Solution:**
```bash
cd /home/auxilus/sih/backend

# Run migrations
alembic upgrade head

# Or recreate tables
python create_tables.py
```

---

## 🔍 Verification Checklist

Before running tests, verify:

- [ ] Docker services running: `docker compose ps`
- [ ] PostgreSQL accessible: `psql -h localhost -U railway_user -d railway_db`
- [ ] Redis accessible: `redis-cli ping`
- [ ] Backend server running: `curl http://localhost:8000/api/health`
- [ ] Controllers exist: Check database or run `setup_auth.py`
- [ ] Dependencies installed: `pip list | grep fastapi`

---

## 📊 Expected Test Results

When you run `./test_controller_api.sh`, you should see:

```
═══════════════════════════════════════════════════════
CONTROLLER ACTION API TEST SUITE
═══════════════════════════════════════════════════════

✓ Login successful
✓ Retrieved X active conflicts
✓ Conflict resolved successfully
✓ Train control executed successfully
✓ Decision logged successfully
✓ Retrieved X audit records
✓ Retrieved performance metrics
✓ Rate limiting working correctly
✓ Authorization protection working correctly
✓ Validation working correctly

═══════════════════════════════════════════════════════
TEST SUITE COMPLETE
═══════════════════════════════════════════════════════
```

---

## 🚀 Production Deployment

For production deployment:

1. **Set environment variables:**
```bash
export JWT_SECRET="your-production-secret-key"
export DATABASE_URL="postgresql://user:pass@prod-db:5432/railway"
export REDIS_URL="redis://prod-redis:6379"
```

2. **Use production WSGI server:**
```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

3. **Enable HTTPS** (use nginx or similar)

4. **Set up monitoring** (use the performance metrics endpoint)

---

## 📞 Need Help?

- **Documentation:** See `CONTROLLER_API_DOCS.md`
- **Quick Reference:** See `CONTROLLER_QUICK_REF.md`
- **Architecture:** See `CONTROLLER_ARCHITECTURE.md`
- **Test Issues:** Check server logs: `docker compose logs -f`

---

## 🎯 Quick Start Summary

**The absolute fastest way to get started:**

```bash
# Terminal 1: Start services
cd /home/auxilus/sih
docker compose up -d postgres redis

# Terminal 2: Start backend
cd /home/auxilus/sih/backend
uvicorn app.main:app --reload

# Terminal 3: Run tests
cd /home/auxilus/sih/backend
./test_controller_api.sh

# Browser: View docs
open http://localhost:8000/docs
```

**That's it!** You're now running the complete Railway Traffic Management System with Controller Action APIs! 🎉
