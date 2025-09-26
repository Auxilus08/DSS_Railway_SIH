# Railway Traffic Management API Documentation

A comprehensive real-time API for railway position tracking and traffic management with WebSocket streaming, JWT authentication, and high-performance data processing.

## 🚀 Quick Start

### Prerequisites
```bash
# Install dependencies
pip install -r requirements.txt

# Setup database (with seed data)
python setup_railway_db.py

# Start Redis (required for caching and pub/sub)
redis-server

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Access Points
- **API Documentation**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/health
- **WebSocket**: ws://localhost:8000/ws/positions

## 📋 API Overview

### Core Features
- ✅ **Real-time position tracking** with <100ms response time
- ✅ **WebSocket streaming** for live updates
- ✅ **JWT authentication** for controllers
- ✅ **Rate limiting** (1000 requests/minute per train)
- ✅ **Redis caching** for optimal performance
- ✅ **TimescaleDB** for time-series position data
- ✅ **Bulk operations** for efficient data processing
- ✅ **Comprehensive validation** and error handling

### Rate Limits
- **Position Updates**: 1000 requests/minute per train
- **Bulk Updates**: 100 requests/minute per IP
- **General API**: 1000 requests/minute per IP

## 🔐 Authentication

### Login
```http
POST /api/auth/login
Content-Type: application/json

{
  "employee_id": "CTR001",
  "password": "password_CTR001"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "controller": {
    "id": 1,
    "name": "Alice Johnson",
    "employee_id": "CTR001",
    "auth_level": "supervisor",
    "section_responsibility": [1, 2, 3, 4, 5],
    "active": true,
    "created_at": "2024-01-01T00:00:00Z"
  }
}
```

### Demo Credentials
```http
GET /api/auth/demo-credentials
```

**Available Demo Accounts:**
- `CTR001` / `password_CTR001` (Supervisor)
- `CTR002` / `password_CTR002` (Operator)
- `CTR003` / `password_CTR003` (Manager)
- `CTR004` / `password_CTR004` (Operator)
- `CTR005` / `password_CTR005` (Admin)

### Using Authentication
Include the JWT token in the Authorization header:
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## 🚄 Position Tracking Endpoints

### 1. Single Position Update
```http
POST /api/trains/position
Content-Type: application/json

{
  "train_id": 1,
  "section_id": 3,
  "coordinates": {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "altitude": 10.0
  },
  "speed_kmh": 85.5,
  "heading": 45.0,
  "timestamp": "2024-01-01T12:00:00Z",
  "distance_from_start": 150.0,
  "signal_strength": 95,
  "gps_accuracy": 2.5
}
```

**Response:**
```json
{
  "success": true,
  "message": "Position updated successfully",
  "data": {
    "train_id": 1,
    "timestamp": "2024-01-01T12:00:00Z",
    "section_code": "EX-A"
  },
  "timestamp": "2024-01-01T12:00:00.123Z"
}
```

### 2. Bulk Position Update
```http
POST /api/trains/position/bulk
Authorization: Bearer <token>
Content-Type: application/json

{
  "positions": [
    {
      "train_id": 1,
      "section_id": 3,
      "coordinates": {
        "latitude": 40.7128,
        "longitude": -74.0060
      },
      "speed_kmh": 85.5,
      "heading": 45.0,
      "timestamp": "2024-01-01T12:00:00Z"
    },
    {
      "train_id": 2,
      "section_id": 5,
      "coordinates": {
        "latitude": 40.7589,
        "longitude": -73.9851
      },
      "speed_kmh": 92.0,
      "heading": 90.0,
      "timestamp": "2024-01-01T12:00:00Z"
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Bulk update completed: 2 updated, 0 errors",
  "data": {
    "updated_count": 2,
    "error_count": 0,
    "updated_positions": [
      {
        "train_id": 1,
        "timestamp": "2024-01-01T12:00:00Z",
        "section_code": "EX-A"
      },
      {
        "train_id": 2,
        "timestamp": "2024-01-01T12:00:00Z",
        "section_code": "IND-1"
      }
    ]
  }
}
```

### 3. Get Current Train Position
```http
GET /api/trains/{train_id}/position
```

**Response:**
```json
{
  "train_id": 1,
  "section_id": 3,
  "section_code": "EX-A",
  "section_name": "Express Track Section A",
  "coordinates": {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "altitude": 10.0
  },
  "speed_kmh": 85.5,
  "heading": 45.0,
  "timestamp": "2024-01-01T12:00:00Z",
  "distance_from_start": 150.0,
  "signal_strength": 95,
  "gps_accuracy": 2.5
}
```

### 4. Get Position History
```http
GET /api/trains/{train_id}/position/history?hours=1&limit=100
```

**Response:**
```json
{
  "success": true,
  "message": "Retrieved 25 position records",
  "data": {
    "train_id": 1,
    "train_number": "EX001",
    "time_range": {
      "start": "2024-01-01T11:00:00Z",
      "end": "2024-01-01T12:00:00Z",
      "hours": 1
    },
    "total_records": 25,
    "positions": [
      {
        "timestamp": "2024-01-01T12:00:00Z",
        "section_id": 3,
        "section_code": "EX-A",
        "coordinates": {
          "latitude": 40.7128,
          "longitude": -74.0060,
          "altitude": 10.0
        },
        "speed_kmh": 85.5,
        "heading": 45.0,
        "distance_from_start": 150.0,
        "signal_strength": 95,
        "gps_accuracy": 2.5
      }
    ]
  }
}
```

## 🛤️ Section Status Endpoints

### 1. Get All Sections Status
```http
GET /api/sections/status
Authorization: Bearer <token>
```

**Query Parameters:**
- `section_ids`: List of specific section IDs
- `section_type`: Filter by type (track, junction, station, yard)
- `include_inactive`: Include inactive sections (default: false)

**Response:**
```json
{
  "sections": [
    {
      "section": {
        "id": 1,
        "name": "Central Station Platform 1",
        "section_code": "CS-P1",
        "section_type": "station",
        "length_meters": 500.0,
        "max_speed_kmh": 30,
        "capacity": 2,
        "electrified": true,
        "signaling_system": "ETCS Level 2",
        "active": true,
        "created_at": "2024-01-01T00:00:00Z"
      },
      "current_occupancy": 1,
      "utilization_percentage": 50.0,
      "trains_present": [
        {
          "id": 1,
          "train_number": "EX001",
          "type": "express",
          "speed_kmh": 0.0,
          "operational_status": "active"
        }
      ],
      "status": "busy"
    }
  ],
  "total_sections": 20,
  "occupied_sections": 8,
  "network_utilization": 40.0,
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### 2. Get Specific Section Status
```http
GET /api/sections/{section_id}/status
Authorization: Bearer <token>
```

### 3. Get Section Occupancy History
```http
GET /api/sections/{section_id}/occupancy-history?hours=24
Authorization: Bearer <token>
```

**Response:**
```json
{
  "success": true,
  "message": "Retrieved occupancy history for section CS-P1",
  "data": {
    "section": {
      "id": 1,
      "section_code": "CS-P1",
      "name": "Central Station Platform 1",
      "capacity": 2
    },
    "time_range": {
      "start": "2024-01-01T00:00:00Z",
      "end": "2024-01-01T12:00:00Z",
      "hours": 24
    },
    "statistics": {
      "total_visits": 15,
      "current_occupancy": 1,
      "completed_visits": 14,
      "average_duration_minutes": 8.5,
      "utilization_percentage": 50.0
    },
    "history": [
      {
        "train_id": 1,
        "train_number": "EX001",
        "train_type": "express",
        "entry_time": "2024-01-01T11:45:00Z",
        "exit_time": null,
        "expected_exit_time": "2024-01-01T12:05:00Z",
        "duration_minutes": null,
        "still_present": true
      }
    ]
  }
}
```

## 🌐 WebSocket Real-time Streaming

### Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/positions');

// With authentication
const ws = new WebSocket('ws://localhost:8000/ws/positions?token=<jwt_token>&client_id=my_client');
```

### Message Types

#### 1. Connection Established
```json
{
  "type": "connection_established",
  "data": {
    "connection_id": "abc123",
    "timestamp": "2024-01-01T12:00:00Z",
    "message": "Connected to Railway Traffic Management System"
  }
}
```

#### 2. Position Updates
```json
{
  "type": "position_update",
  "train_id": 1,
  "train_number": "EX001",
  "train_type": "express",
  "position": {
    "train_id": 1,
    "section_id": 3,
    "section_code": "EX-A",
    "section_name": "Express Track Section A",
    "coordinates": {
      "latitude": 40.7128,
      "longitude": -74.0060,
      "altitude": 10.0
    },
    "speed_kmh": 85.5,
    "heading": 45.0,
    "timestamp": "2024-01-01T12:00:00Z"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

#### 3. Conflict Alerts
```json
{
  "type": "conflict_alert",
  "data": {
    "conflict_id": 123,
    "conflict_type": "collision_risk",
    "severity": "high",
    "trains_involved": [1, 2],
    "sections_involved": [3, 4],
    "detection_time": "2024-01-01T12:00:00Z",
    "description": "Two trains approaching same junction"
  }
}
```

### Client Commands

#### Subscribe to Train Updates
```json
{
  "type": "subscribe_train",
  "data": {
    "train_id": 1
  }
}
```

#### Subscribe to Section Updates
```json
{
  "type": "subscribe_section",
  "data": {
    "section_id": 3
  }
}
```

#### Subscribe to All Updates
```json
{
  "type": "subscribe_all",
  "data": {}
}
```

#### Ping/Pong
```json
{
  "type": "ping",
  "data": {
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

### Admin WebSocket
```javascript
const adminWs = new WebSocket('ws://localhost:8000/ws/admin?token=<admin_token>');
```

**Admin Commands:**
- `get_connection_stats` - Get connection statistics
- `broadcast_system_message` - Broadcast to all clients
- `get_performance_metrics` - Get performance data

## 📊 Monitoring Endpoints

### Health Check
```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0",
  "database_status": "healthy",
  "redis_status": "healthy",
  "active_connections": 5
}
```

### Performance Metrics
```http
GET /api/performance
```

**Response:**
```json
{
  "total_trains": 10,
  "active_trains": 8,
  "position_updates_per_minute": 150,
  "average_response_time_ms": 45.2,
  "active_websocket_connections": 5,
  "cache_hit_rate": 85.5,
  "database_connections": 10
}
```

### System Information
```http
GET /api/system-info
```

**Response:**
```json
{
  "success": true,
  "message": "System information retrieved",
  "data": {
    "api_version": "1.0.0",
    "timestamp": "2024-01-01T12:00:00Z",
    "database": {
      "connected": true,
      "version": "PostgreSQL 14.0",
      "pool_size": 20
    },
    "redis": {
      "connected": true,
      "url": "redis://localhost:6379/0"
    },
    "websocket": {
      "total_connections": 5,
      "general_subscribers": 2,
      "train_subscriptions": 3,
      "section_subscriptions": 1
    },
    "environment": {
      "python_version": "3.11+",
      "fastapi_version": "0.104+",
      "features": [
        "real_time_position_tracking",
        "websocket_streaming",
        "jwt_authentication",
        "rate_limiting",
        "redis_caching",
        "timescaledb_support",
        "postgis_support"
      ]
    }
  }
}
```

## 🧪 Testing

### Run Unit Tests
```bash
cd backend
python -m pytest tests/ -v
```

### cURL Tests
```bash
./test_scripts/curl_tests.sh
```

### WebSocket Tests
```bash
python test_scripts/websocket_test.py
```

### Performance Tests
```bash
python test_scripts/performance_test.py
```

## 📝 Example Usage

### JavaScript Client Example
```javascript
class RailwayTracker {
  constructor(baseUrl, wsUrl) {
    this.baseUrl = baseUrl;
    this.wsUrl = wsUrl;
    this.token = null;
    this.ws = null;
  }

  async login(employeeId, password) {
    const response = await fetch(`${this.baseUrl}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ employee_id: employeeId, password })
    });
    
    const data = await response.json();
    this.token = data.access_token;
    return data;
  }

  async updatePosition(trainId, sectionId, coordinates, speed, heading) {
    const response = await fetch(`${this.baseUrl}/api/trains/position`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        train_id: trainId,
        section_id: sectionId,
        coordinates,
        speed_kmh: speed,
        heading,
        timestamp: new Date().toISOString()
      })
    });
    
    return response.json();
  }

  connectWebSocket() {
    const wsUrl = this.token 
      ? `${this.wsUrl}?token=${this.token}&client_id=js_client`
      : this.wsUrl;
    
    this.ws = new WebSocket(wsUrl);
    
    this.ws.onopen = () => {
      console.log('WebSocket connected');
      
      // Subscribe to all position updates
      this.ws.send(JSON.stringify({
        type: 'subscribe_all',
        data: {}
      }));
    };
    
    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      console.log('Received:', message);
      
      if (message.type === 'position_update') {
        this.handlePositionUpdate(message);
      } else if (message.type === 'conflict_alert') {
        this.handleConflictAlert(message);
      }
    };
    
    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  handlePositionUpdate(message) {
    console.log(`Train ${message.train_number} at ${message.position.speed_kmh} km/h`);
    // Update UI with new position
  }

  handleConflictAlert(message) {
    console.warn('Conflict detected:', message.data);
    // Show alert to user
  }
}

// Usage
const tracker = new RailwayTracker(
  'http://localhost:8000',
  'ws://localhost:8000/ws/positions'
);

// Login and connect
tracker.login('CTR001', 'password_CTR001').then(() => {
  tracker.connectWebSocket();
});
```

### Python Client Example
```python
import asyncio
import aiohttp
import websockets
import json
from datetime import datetime

class RailwayClient:
    def __init__(self, base_url, ws_url):
        self.base_url = base_url
        self.ws_url = ws_url
        self.token = None
        self.session = None

    async def login(self, employee_id, password):
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/api/auth/login", json={
                "employee_id": employee_id,
                "password": password
            }) as response:
                data = await response.json()
                self.token = data["access_token"]
                return data

    async def update_position(self, train_id, section_id, lat, lon, speed, heading):
        headers = {"Content-Type": "application/json"}
        data = {
            "train_id": train_id,
            "section_id": section_id,
            "coordinates": {"latitude": lat, "longitude": lon},
            "speed_kmh": speed,
            "heading": heading,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.base_url}/api/trains/position", 
                                  json=data, headers=headers) as response:
                return await response.json()

    async def listen_websocket(self):
        ws_url = f"{self.ws_url}?token={self.token}" if self.token else self.ws_url
        
        async with websockets.connect(ws_url) as websocket:
            # Subscribe to all updates
            await websocket.send(json.dumps({
                "type": "subscribe_all",
                "data": {}
            }))
            
            async for message in websocket:
                data = json.loads(message)
                print(f"Received: {data['type']}")
                
                if data["type"] == "position_update":
                    train = data["train_number"]
                    speed = data["position"]["speed_kmh"]
                    print(f"Train {train} moving at {speed} km/h")

# Usage
async def main():
    client = RailwayClient(
        "http://localhost:8000",
        "ws://localhost:8000/ws/positions"
    )
    
    await client.login("CTR001", "password_CTR001")
    await client.listen_websocket()

asyncio.run(main())
```

## 🚨 Error Handling

### HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation error)
- `401` - Unauthorized (invalid/missing token)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found (train/section doesn't exist)
- `422` - Unprocessable Entity (validation error)
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error

### Error Response Format
```json
{
  "success": false,
  "error": "Validation error",
  "details": {
    "field": "coordinates.latitude",
    "message": "Latitude must be between -90 and 90"
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Rate Limit Headers
```http
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 2024-01-01T12:01:00Z
X-Process-Time: 45.2
```

## 🔧 Configuration

### Environment Variables
```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=railway_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
DATABASE_URL=postgresql://user:pass@host:port/railway_db

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# JWT
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRES_IN=3600

# API
API_BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173
```

### Docker Deployment
```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f api

# Scale API instances
docker-compose up -d --scale api=3
```

## 📈 Performance Optimization

### Caching Strategy
- **Position Cache**: 5 minutes TTL
- **Section Status**: 1 minute TTL
- **Train Info**: 1 hour TTL
- **Rate Limiting**: 1 minute sliding window

### Database Optimization
- **TimescaleDB** hypertables for position data
- **Composite indexes** for frequent queries
- **Connection pooling** (20 connections)
- **Query optimization** with proper indexes

### WebSocket Optimization
- **Connection pooling** and reuse
- **Message batching** for bulk updates
- **Selective subscriptions** to reduce bandwidth
- **Automatic reconnection** handling

## 🛡️ Security

### Authentication
- **JWT tokens** with configurable expiration
- **Role-based access control** (operator, supervisor, manager, admin)
- **Section-based permissions** for controllers
- **Token validation** on all protected endpoints

### Rate Limiting
- **Per-train limits** for position updates
- **IP-based limits** for general API access
- **Sliding window** algorithm
- **Redis-backed** for distributed systems

### Data Validation
- **Pydantic models** for request validation
- **GPS coordinate** bounds checking
- **Speed and heading** validation
- **Timestamp** validation (prevent future dates)

---

## 📞 Support

For technical support or questions:
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/health
- **System Info**: http://localhost:8000/api/system-info
- **WebSocket Stats**: http://localhost:8000/ws/stats

**Built for High Performance, Reliability, and Real-time Operations** 🚂⚡