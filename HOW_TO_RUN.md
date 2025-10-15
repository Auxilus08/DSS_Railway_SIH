# 🚂 How to Run the Railway Traffic Management System

This guide will help you run the complete Railway Traffic Management System with advanced conflict detection and controller action APIs.

## 📋 Prerequisites

Before starting, ensure you have:

- **Docker & Docker Compose** (Recommended - easiest setup)
- **Python 3.11+** (for manual setup)
- **Node.js 18+** & **npm** (for frontend)
- **PostgreSQL 15+** with TimescaleDB (for manual setup)
- **Redis 7+** (for caching and rate limiting)

## 🚀 Quick Start (Docker - Recommended)

### 1. Clone and Setup Environment

```bash
# Clone the repository
git clone https://github.com/Auxilus08/DSS_Railway_SIH.git
cd DSS_Railway_SIH

# Copy environment files
cp .env.example .env
cp backend/.env.example backend/.env

# Edit .env files with your settings (optional - defaults work)
nano .env
nano backend/.env
```

### 2. Start the System

```bash
# Start all services with Docker Compose
docker-compose up --build

# Or run in background
docker-compose up --build -d
```

### 3. Initialize Database (First Time Only)

```bash
# Wait for services to start, then initialize the database
docker-compose exec backend python setup_railway_db.py

# Create demo controller accounts
docker-compose exec backend python setup_auth.py

# (Optional) Load demo data for testing
docker-compose exec backend python create_demo_data.py
```

### 4. Access the System

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health
- **Conflict Detection Status**: http://localhost:8000/api/conflicts/status

### 5. Demo Credentials

After running `setup_auth.py`, use these credentials:

| Employee ID | Password | Role | Description |
|------------|----------|------|-------------|
| CTR001 | railway123 | Supervisor | Alice Johnson |
| CTR002 | railway123 | Supervisor | Bob Smith |
| ADMIN001 | admin123 | Admin | System Admin |
| MANAGER001 | manager123 | Manager | Operations Manager |
| OPERATOR001 | operator123 | Operator | Basic Operator |

## 🛠 Manual Setup (Development)

### 1. Database Setup

```bash
# Start PostgreSQL with TimescaleDB and Redis using Docker Compose
docker-compose up -d postgres redis

# Or start manually:
# PostgreSQL with TimescaleDB
docker run -d --name postgres \
  -e POSTGRES_DB=railway_db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  timescale/timescaledb:2.13.1-pg15

# Redis
docker run -d --name redis \
  -p 6379:6379 \
  redis:7-alpine
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your database credentials

# Initialize database
python setup_railway_db.py

# Create demo users (optional)
python setup_auth.py

# Load demo data (optional)
python create_demo_data.py

# Start the server
uvicorn app.main:app --reload --port 8000

# Or use the startup script
./start.sh
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## 🔧 Environment Configuration

### Key Environment Variables

Edit `.env` file in the root directory:

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=railway_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT Security
JWT_SECRET=your_super_secret_key_at_least_32_characters_long
JWT_ALGORITHM=HS256
JWT_EXPIRES_IN=3600

# API Configuration
API_BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173
```

## ⚡ Conflict Detection & Controller Actions

The system provides powerful conflict detection and controller action capabilities:

### Controller Action APIs

The system includes 5 comprehensive controller action endpoints:

1. **GET /api/conflicts/active** - Get active conflicts with AI recommendations
2. **POST /api/conflicts/{id}/resolve** - Resolve conflicts (accept/modify/reject)
3. **POST /api/trains/{id}/control** - Control trains (delay/reroute/priority/stop/speed/resume)
4. **POST /api/decisions/log** - Log manual controller decisions
5. **GET /api/audit/decisions** - Query audit trail with filtering
6. **GET /api/audit/performance** - Get performance metrics

See [CONTROLLER_API_DOCS.md](backend/CONTROLLER_API_DOCS.md) for complete API documentation.

### Check System Status
```bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/conflicts/status
```

### Get Active Conflicts
```bash
# Login first
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"employee_id": "CTR001", "password": "railway123"}' \
  | jq -r '.access_token')

# Get active conflicts with AI recommendations
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/conflicts/active | jq
```

### Resolve a Conflict
```bash
# Accept AI recommendation
curl -X POST http://localhost:8000/api/conflicts/1/resolve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "accept",
    "ai_solution_id": "ai_rec_123"
  }' | jq

# Modify AI recommendation
curl -X POST http://localhost:8000/api/conflicts/2/resolve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "modify",
    "modified_solution": {
      "train_actions": [
        {"train_id": 1, "action": "delay", "parameters": {"delay_minutes": 10}}
      ]
    },
    "modification_reason": "Track maintenance requires additional delay"
  }' | jq
```

### Control a Train
```bash
# Delay a train
curl -X POST http://localhost:8000/api/trains/1/control \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "delay",
    "delay_minutes": 15,
    "rationale": "Track maintenance ahead",
    "emergency": false
  }' | jq

# Change train priority
curl -X POST http://localhost:8000/api/trains/2/control \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "priority",
    "new_priority": 9,
    "rationale": "VIP passengers on board"
  }' | jq

# Reroute a train
curl -X POST http://localhost:8000/api/trains/3/control \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "reroute",
    "new_route": [2, 3, 4, 5],
    "rationale": "Original route under maintenance"
  }' | jq
```

### Query Audit Trail
```bash
# Get recent decisions
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/audit/decisions?limit=10&executed_only=true" | jq

# Get performance metrics
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/audit/performance?days=7" | jq
```

### Run Manual Detection
```bash
curl -X POST http://localhost:8000/api/conflicts/detect
```

### View Conflict History
```bash
curl http://localhost:8000/api/conflicts/history
```

### Monitor Performance
```bash
curl http://localhost:8000/api/conflicts/metrics
```

## 🧪 Testing the System

### 1. Run Automated Controller API Tests

```bash
cd backend

# Run the comprehensive automated test suite (13 tests)
./test_controller_api.sh

# This tests:
# - Authentication
# - Active conflicts retrieval
# - Conflict resolution (accept/modify)
# - Train control (delay/priority/reroute)
# - Decision logging
# - Audit trail queries
# - Performance metrics
# - Rate limiting
# - Authorization
# - Input validation
```

### 2. Run Backend Unit Tests

```bash
cd backend

# Run all tests
pytest tests/ -v

# Run specific controller action tests
pytest tests/test_controller_actions.py -v

# Run conflict detection tests
pytest tests/test_conflict_detection.py -v

# Run with coverage
pytest --cov=app tests/
```

### 3. Test Individual Endpoints

```bash
# Performance test with mock trains
cd backend/test_scripts
python performance_test.py

# WebSocket connection test
python websocket_test.py

# cURL API tests
./curl_tests.sh
```

### 4. Load Test Data

```bash
# Create demo trains and conflicts
cd backend
python create_demo_data.py

# This creates:
# - 5 trains (TR001-TR005) of various types
# - 3 active conflicts with AI recommendations
```

## 📊 System Monitoring

### Health Check
```bash
curl http://localhost:8000/api/health

# Response includes:
# - Overall status
# - Database status
# - Redis status
# - Active connections
# - Timestamp
```

### System Information
```bash
curl http://localhost:8000/api/system-info

# Returns:
# - System version
# - Python version
# - Database version
# - Available endpoints
```

### Performance Metrics (Requires Auth)
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/audit/performance?days=7

# Returns:
# - Total decisions
# - Execution rate
# - Average resolution time
# - Decisions by controller
# - Decisions by action type
# - AI vs manual decisions
# - Conflicts resolved/pending
# - Average AI confidence
```

### Real-time Monitoring

The system provides WebSocket connections for real-time monitoring:
- Train positions: `ws://localhost:8000/ws/positions`
- Conflict alerts: `ws://localhost:8000/ws/conflicts`
- System status: `ws://localhost:8000/ws/system`

## 🌐 WebSocket Real-time Features

### Connect to WebSocket
```javascript
// Connect to real-time updates
const ws = new WebSocket('ws://localhost:8000/ws/positions');

// Subscribe to all updates
ws.send(JSON.stringify({
  type: 'subscribe_all'
}));

// Listen for conflict alerts
ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  if (data.type === 'conflict_alert') {
    console.log('Conflict detected:', data.data);
  }
};
```

## 🔐 Authentication

### Create a Controller Account

```bash
# Using the API
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Controller",
    "employee_id": "CTRL001",
    "password": "secure_password123",
    "auth_level": "supervisor"
  }'
```

### Login and Get JWT Token

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": "CTR001",
    "password": "railway123"
  }'

# Response includes:
# - access_token (JWT)
# - token_type (bearer)
# - expires_in (3600 seconds)
# - controller info

# Save token for subsequent requests
TOKEN="your_jwt_token_here"
```

### Use Token in Requests

```bash
# All controller action endpoints require authentication
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/conflicts/active
```

## 🚂 Sample Train Operations

### Add a Train

```bash
curl -X POST http://localhost:8000/api/trains \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "train_number": "EXP001",
    "type": "express",
    "max_speed_kmh": 160,
    "capacity": 500,
    "priority": 8,
    "length_meters": 200,
    "weight_tons": 400
  }'
```

### Update Train Position

```bash
curl -X POST http://localhost:8000/api/positions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "train_id": 1,
    "section_id": 100,
    "coordinates": {
      "latitude": 28.6139,
      "longitude": 77.2090
    },
    "speed_kmh": 120.5,
    "heading": 45.0
  }'
```

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check if PostgreSQL is running
   docker ps | grep postgres
   
   # Check logs
   docker-compose logs postgres
   
   # Restart database
   docker-compose restart postgres
   ```

2. **Redis Connection Failed**
   ```bash
   # Check Redis status
   docker ps | grep redis
   
   # Test Redis connection
   redis-cli ping
   
   # Restart Redis
   docker-compose restart redis
   ```

3. **Port Already in Use**
   ```bash
   # Find and kill process using port 8000
   lsof -i :8000
   kill -9 <PID>
   
   # Or change port in docker-compose.yml
   ```

4. **Authentication Errors**
   ```bash
   # Recreate demo users
   cd backend
   python setup_auth.py
   
   # Check JWT secret in .env
   echo $JWT_SECRET
   ```

5. **Database Schema Issues**
   ```bash
   # Add missing columns (if needed)
   docker-compose exec postgres psql -U postgres -d railway_db
   
   # For AI fields in conflicts table:
   ALTER TABLE conflicts ADD COLUMN IF NOT EXISTS ai_analyzed BOOLEAN DEFAULT FALSE;
   ALTER TABLE conflicts ADD COLUMN IF NOT EXISTS ai_confidence REAL;
   ALTER TABLE conflicts ADD COLUMN IF NOT EXISTS ai_recommendations JSONB;
   
   # For AI fields in decisions table:
   ALTER TABLE decisions ADD COLUMN IF NOT EXISTS ai_generated BOOLEAN DEFAULT FALSE;
   ALTER TABLE decisions ADD COLUMN IF NOT EXISTS ai_confidence REAL;
   ```

6. **TimescaleDB Extension Error**
   ```bash
   # Connect to database and enable extension
   docker-compose exec postgres psql -U postgres -d railway_db
   CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
   ```

7. **Test Failures**
   ```bash
   # Ensure demo data exists
   cd backend
   python create_demo_data.py
   
   # Check server is running
   curl http://localhost:8000/api/health
   
   # Run tests with verbose output
   ./test_controller_api.sh
   ```

### Performance Issues

1. **Slow Conflict Detection**
   - Check database indexes: `python backend/validation_queries.py`
   - Monitor system resources: `docker stats`
   - Review conflict detection logs

2. **High Memory Usage**
   - Adjust Docker memory limits in `docker-compose.yml`
   - Optimize database queries
   - Clear Redis cache: `redis-cli FLUSHALL`

### Logs and Debugging

```bash
# View all logs
docker-compose logs -f

# Backend logs only
docker-compose logs -f backend

# Database logs
docker-compose logs -f postgres

# Enable debug mode
export DEBUG=true
```

## 📈 Performance Optimization

### For Production Deployment

1. **Database Optimization**
   ```sql
   -- Run in PostgreSQL
   ANALYZE;
   REINDEX DATABASE railway_db;
   ```

2. **Redis Configuration**
   ```bash
   # In redis.conf
   maxmemory 1gb
   maxmemory-policy allkeys-lru
   ```

3. **Docker Resource Limits**
   ```yaml
   # In docker-compose.yml
   services:
     backend:
       deploy:
         resources:
           limits:
             memory: 2G
             cpus: '1.0'
   ```

## 🚀 Production Deployment

### Using Docker Compose

```bash
# Production configuration
cp docker-compose.yml docker-compose.prod.yml

# Edit for production
nano docker-compose.prod.yml

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

### Environment Variables for Production

```bash
ENVIRONMENT=production
DEBUG=false
JWT_SECRET=your_production_secret_key
POSTGRES_PASSWORD=strong_production_password
```

## 📞 Support

If you encounter issues:

1. Check the logs: `docker-compose logs -f`
2. Verify environment variables in `.env` files
3. Ensure all required ports are available
4. Check database connectivity
5. Review the API documentation at `/docs`

## 🎯 Next Steps

Once the system is running:

1. **Explore the API**: Visit http://localhost:8000/docs for interactive API documentation
2. **Test Controller Actions**: 
   - Run `./test_controller_api.sh` to verify all endpoints
   - Try resolving conflicts manually through the API
   - Test train control commands
3. **Monitor Real-time**: Connect to WebSocket for live updates
4. **Add Train Data**: Use `create_demo_data.py` or add your own trains via API
5. **View Analytics**: Check system performance metrics
6. **Explore Frontend**: Visit http://localhost:5173 for the web interface
7. **Read Documentation**:
   - [CONTROLLER_API_DOCS.md](backend/CONTROLLER_API_DOCS.md) - Complete API reference
   - [CONTROLLER_ARCHITECTURE.md](backend/CONTROLLER_ARCHITECTURE.md) - System architecture
   - [STARTUP_GUIDE.md](backend/STARTUP_GUIDE.md) - Quick start guide
   - [TEST_RESULTS.md](backend/TEST_RESULTS.md) - Test coverage report

## 📚 Additional Documentation

- **API Reference**: [CONTROLLER_API_DOCS.md](backend/CONTROLLER_API_DOCS.md)
- **Implementation Details**: [CONTROLLER_IMPLEMENTATION_SUMMARY.md](backend/CONTROLLER_IMPLEMENTATION_SUMMARY.md)
- **Quick Reference**: [CONTROLLER_QUICK_REF.md](backend/CONTROLLER_QUICK_REF.md)
- **Architecture**: [CONTROLLER_ARCHITECTURE.md](backend/CONTROLLER_ARCHITECTURE.md)
- **Conflict Detection**: [CONFLICT_DETECTION_README.md](backend/CONFLICT_DETECTION_README.md)
- **Database Setup**: [DATABASE_TESTING_SETUP.md](backend/DATABASE_TESTING_SETUP.md)

## 🎓 Key Features

✅ **Real-time Conflict Detection** - Automated detection of scheduling conflicts  
✅ **AI-powered Recommendations** - Smart conflict resolution suggestions  
✅ **Controller Action APIs** - Complete control over trains and conflicts  
✅ **Audit Trail** - Full logging of all decisions and actions  
✅ **Rate Limiting** - Protection for critical operations  
✅ **WebSocket Support** - Real-time notifications  
✅ **Background Tasks** - Async execution of train control commands  
✅ **Role-based Access** - Fine-grained permission control  
✅ **Comprehensive Testing** - 13+ automated tests, 15+ unit tests  
✅ **Performance Metrics** - Detailed analytics and monitoring  

The system is now ready for railway traffic management with real-time conflict detection and controller actions! 🚂✨