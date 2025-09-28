# 🚂 How to Run the Railway Traffic Management System

This guide will help you run the complete Railway Traffic Management System with the advanced conflict detection engine.

## 📋 Prerequisites

Before starting, ensure you have:

- **Docker & Docker Compose** (Recommended - easiest setup)
- **Python 3.11+** (for manual setup)
- **Node.js 18+** & **npm** (for frontend)
- **PostgreSQL 15+** with TimescaleDB (for manual setup)
- **Redis 7+** (for manual setup)

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
```

### 4. Access the System

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Conflict Detection Status**: http://localhost:8000/api/conflicts/status

## 🛠 Manual Setup (Development)

### 1. Database Setup

```bash
# Start PostgreSQL with TimescaleDB
docker run -d --name postgres \
  -e POSTGRES_DB=railway_db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -p 5432:5432 \
  timescale/timescaledb:2.13.1-pg15

# Start Redis
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

# Start the server
uvicorn app.main:app --reload --port 8000
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

## ⚡ Conflict Detection System

The conflict detection system starts automatically when the backend starts. You can:

### Check System Status
```bash
curl http://localhost:8000/api/conflicts/status
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

### 1. Run Backend Tests

```bash
cd backend
pytest tests/ -v

# Run specific conflict detection tests
pytest tests/test_conflict_detection.py -v

# Run with coverage
pytest --cov=app tests/
```

### 2. Test Conflict Detection

```bash
# Performance test with mock trains
cd backend/test_scripts
python performance_test.py

# WebSocket connection test
python websocket_test.py

# cURL API tests
./curl_tests.sh
```

### 3. Load Test Data

```bash
# Run the demo script to simulate train movements
cd backend
python demo_railway_system.py
```

## 📊 System Monitoring

### Health Check
```bash
curl http://localhost:8000/api/health
```

### Database Check
```bash
curl http://localhost:8000/api/db-check
```

### Performance Metrics
```bash
curl http://localhost:8000/api/performance
```

### System Information
```bash
curl http://localhost:8000/api/system-info
```

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
    "password": "secure_password123"
  }'
```

### Login

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": "CTRL001",
    "password": "secure_password123"
  }'
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
   ```

2. **Redis Connection Failed**
   ```bash
   # Check Redis status
   docker ps | grep redis
   
   # Test Redis connection
   redis-cli ping
   ```

3. **Port Already in Use**
   ```bash
   # Find and kill process using port 8000
   lsof -i :8000
   kill -9 <PID>
   
   # Or change port in docker-compose.yml
   ```

4. **TimescaleDB Extension Error**
   ```bash
   # Connect to database and enable extension
   docker-compose exec postgres psql -U postgres -d railway_db
   CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
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

1. **Explore the API**: Visit http://localhost:8000/docs
2. **Test Conflict Detection**: Use the `/api/conflicts/detect` endpoint
3. **Monitor Real-time**: Connect to WebSocket for live updates
4. **Add Train Data**: Use the seed data or add your own trains
5. **View Analytics**: Check system performance metrics

The system is now ready for railway traffic management with real-time conflict detection! 🚂✨