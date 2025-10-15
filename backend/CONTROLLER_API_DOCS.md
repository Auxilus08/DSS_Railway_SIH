# Controller Action API Documentation

## Overview

The Controller Action APIs provide production-ready endpoints for railway traffic controllers to manage conflicts, control trains, and maintain audit trails. These APIs implement enterprise-level security, rate limiting, and real-time notifications.

## Table of Contents

1. [Authentication](#authentication)
2. [Endpoints](#endpoints)
3. [Request/Response Examples](#examples)
4. [Error Handling](#error-handling)
5. [Rate Limiting](#rate-limiting)
6. [WebSocket Notifications](#websocket-notifications)
7. [Testing](#testing)

---

## Authentication

All controller action endpoints require authentication using JWT Bearer tokens.

### Getting a Token

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "employee_id": "CTR001",
    "password": "password_CTR001"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600,
  "controller": {
    "id": 1,
    "name": "John Doe",
    "employee_id": "CTR001",
    "auth_level": "supervisor",
    "section_responsibility": [1, 2, 3],
    "active": true
  }
}
```

### Using the Token

Include the token in the `Authorization` header:

```bash
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## Endpoints

### 1. Resolve Conflict

**POST** `/api/conflicts/{conflict_id}/resolve`

Implement controller decision on AI-detected conflicts.

#### Permissions
- **Required:** Supervisor or higher
- **Rate Limit:** 10 requests/minute per controller

#### Request Body

```json
{
  "action": "accept",  // "accept" | "modify" | "reject"
  "solution_id": "ai_solution_12345",
  "modifications": {
    "train_actions": [
      {
        "train_id": 101,
        "action": "delay",
        "parameters": {
          "delay_minutes": 10
        }
      }
    ]
  },
  "rationale": "Extended delay for better safety margin based on current weather conditions"
}
```

#### Response

```json
{
  "success": true,
  "conflict_id": 42,
  "action": "modify",
  "decision_id": 789,
  "resolution_time": "2025-10-14T10:30:00Z",
  "message": "Conflict resolution modify initiated. Executing in background.",
  "applied_solution": {
    "train_actions": [
      {
        "train_id": 101,
        "action": "delay",
        "parameters": {
          "delay_minutes": 10
        }
      }
    ]
  }
}
```

#### Action Types

| Action | Description | Required Fields |
|--------|-------------|----------------|
| `accept` | Accept AI recommendation as-is | `rationale` |
| `modify` | Accept with modifications | `rationale`, `modifications` |
| `reject` | Reject AI recommendation | `rationale` |

---

### 2. Train Control

**POST** `/api/trains/{train_id}/control`

Direct train control for emergencies and manual interventions.

#### Permissions
- **Required:** Supervisor or higher
- **Emergency Commands:** Manager or Admin only
- **Rate Limit:** 10 requests/minute per controller

#### Request Body

```json
{
  "command": "delay",  // "delay" | "reroute" | "priority" | "stop" | "speed_limit" | "resume"
  "parameters": {
    "delay_minutes": 15
  },
  "reason": "Track maintenance ahead requires schedule adjustment",
  "emergency": false
}
```

#### Response

```json
{
  "success": true,
  "train_id": 101,
  "train_number": "EXP2025",
  "command": "delay",
  "execution_time": "2025-10-14T10:35:00Z",
  "decision_id": 790,
  "notification_sent": true,
  "message": "Train control command delay initiated."
}
```

#### Command Parameters

##### DELAY
```json
{
  "command": "delay",
  "parameters": {
    "delay_minutes": 15  // 0-180 minutes
  },
  "reason": "Track maintenance ahead",
  "emergency": false
}
```

##### REROUTE
```json
{
  "command": "reroute",
  "parameters": {
    "new_route": [12, 15, 18, 22]  // List of section IDs
  },
  "reason": "Original route unavailable",
  "emergency": false
}
```

##### PRIORITY
```json
{
  "command": "priority",
  "parameters": {
    "new_priority": 8  // 1-10 (10 = highest)
  },
  "reason": "Critical passenger transport",
  "emergency": false
}
```

##### STOP (Emergency)
```json
{
  "command": "stop",
  "parameters": {},
  "reason": "Track obstruction detected",
  "emergency": true  // Requires Manager/Admin
}
```

##### SPEED_LIMIT
```json
{
  "command": "speed_limit",
  "parameters": {
    "max_speed_kmh": 60  // 0-300 km/h
  },
  "reason": "Poor visibility conditions",
  "emergency": false
}
```

##### RESUME
```json
{
  "command": "resume",
  "parameters": {},
  "reason": "Emergency resolved, resuming operations",
  "emergency": false
}
```

---

### 3. Get Active Conflicts

**GET** `/api/conflicts/active`

Retrieve current conflicts requiring controller attention, sorted by severity and urgency.

#### Permissions
- **Required:** Operator or higher
- **Rate Limit:** Standard (30 requests/minute)

#### Response

```json
{
  "total_conflicts": 5,
  "critical_conflicts": 1,
  "high_priority_conflicts": 3,
  "conflicts": [
    {
      "id": 42,
      "conflict_type": "collision_risk",
      "severity": "critical",
      "trains_involved": [101, 102],
      "sections_involved": [12, 13],
      "detection_time": "2025-10-14T10:25:00Z",
      "estimated_impact_minutes": 5,
      "description": "Two express trains on collision course at junction J12",
      "time_to_impact": 5.0,
      "ai_recommendations": {
        "solution_id": "ai_solution_12345",
        "confidence": 0.95,
        "train_actions": [
          {
            "train_id": 101,
            "action": "delay",
            "parameters": {
              "delay_minutes": 3
            }
          }
        ]
      },
      "ai_confidence": 0.95,
      "priority_score": 120.0
    }
  ],
  "timestamp": "2025-10-14T10:30:00Z"
}
```

#### Sorting Logic

Conflicts are sorted by **priority_score** (descending):

```
priority_score = severity_score + (100 / (time_to_impact + 1))
```

Where:
- `severity_score`: CRITICAL=100, HIGH=75, MEDIUM=50, LOW=25
- `time_to_impact`: Minutes until conflict occurs

---

### 4. Log Controller Decision

**POST** `/api/decisions/log`

Manually log controller actions for compliance and audit purposes.

#### Permissions
- **Required:** Operator or higher
- **Rate Limit:** 30 requests/minute per controller

#### Request Body

```json
{
  "conflict_id": 42,
  "train_id": 101,
  "section_id": 12,
  "action_taken": "delay",  // "delay" | "reroute" | "priority_change" | "emergency_stop" | "speed_limit" | "manual_override"
  "rationale": "Delayed train to prevent section overload during peak hours",
  "parameters": {
    "delay_minutes": 10,
    "original_schedule": "10:30",
    "new_schedule": "10:40"
  },
  "outcome": "Successfully prevented conflict. Train departed at 10:41."
}
```

#### Response

```json
{
  "success": true,
  "decision_id": 791,
  "controller_id": 1,
  "timestamp": "2025-10-14T10:40:00Z",
  "logged": true,
  "message": "Decision successfully logged in audit trail"
}
```

---

### 5. Query Audit Trail

**GET** `/api/audit/decisions`

Query audit trail with comprehensive filters for compliance reporting.

#### Permissions
- **Required:** Operator or higher
- **Rate Limit:** Standard (30 requests/minute)

#### Query Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `controller_id` | int | Filter by controller | `?controller_id=1` |
| `conflict_id` | int | Filter by conflict | `?conflict_id=42` |
| `train_id` | int | Filter by train | `?train_id=101` |
| `section_id` | int | Filter by section | `?section_id=12` |
| `action_taken` | string | Filter by action type | `?action_taken=delay` |
| `start_date` | datetime | Start date | `?start_date=2025-10-01T00:00:00Z` |
| `end_date` | datetime | End date | `?end_date=2025-10-14T23:59:59Z` |
| `executed_only` | boolean | Only executed decisions | `?executed_only=true` |
| `approved_only` | boolean | Only approved decisions | `?approved_only=true` |
| `limit` | int | Max results (1-1000) | `?limit=50` |
| `offset` | int | Pagination offset | `?offset=0` |
| `export_format` | string | Export format | `?export_format=csv` |

#### Response

```json
{
  "total_records": 150,
  "returned_records": 50,
  "offset": 0,
  "decisions": [
    {
      "id": 791,
      "controller_id": 1,
      "controller_name": "John Doe",
      "controller_employee_id": "CTR001",
      "conflict_id": 42,
      "train_id": 101,
      "section_id": 12,
      "action_taken": "delay",
      "timestamp": "2025-10-14T10:40:00Z",
      "rationale": "Delayed train to prevent section overload",
      "parameters": {
        "delay_minutes": 10
      },
      "executed": true,
      "execution_time": "2025-10-14T10:41:00Z",
      "execution_result": "Train delayed by 10 minutes",
      "approval_required": false,
      "approved_by_controller_id": null,
      "approved_by_name": null,
      "approval_time": null,
      "ai_generated": false,
      "ai_confidence": null
    }
  ],
  "performance_metrics": {
    "execution_rate": 95.5,
    "average_resolution_time_minutes": 2.3,
    "total_decisions": 50,
    "executed_decisions": 48
  },
  "timestamp": "2025-10-14T11:00:00Z"
}
```

---

### 6. Performance Metrics

**GET** `/api/audit/performance`

Get performance metrics for controller decisions.

#### Permissions
- **Required:** Supervisor or higher
- **Rate Limit:** Standard (30 requests/minute)

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `start_date` | datetime | Start date (default: 30 days ago) |
| `end_date` | datetime | End date (default: now) |

#### Response

```json
{
  "total_decisions": 450,
  "executed_decisions": 428,
  "execution_rate": 95.11,
  "average_resolution_time_minutes": 2.45,
  "decisions_by_controller": {
    "John Doe": 150,
    "Jane Smith": 120,
    "Bob Johnson": 180
  },
  "decisions_by_action": {
    "delay": 180,
    "reroute": 95,
    "priority_change": 75,
    "manual_override": 50,
    "emergency_stop": 15,
    "speed_limit": 35
  },
  "ai_vs_manual_decisions": {
    "ai_generated": 320,
    "manual": 130
  },
  "conflicts_resolved": 380,
  "conflicts_pending": 25,
  "average_ai_confidence": 0.8675,
  "period_start": "2025-09-14T00:00:00Z",
  "period_end": "2025-10-14T11:00:00Z"
}
```

---

## Error Handling

All endpoints return standard error responses:

### 400 Bad Request

```json
{
  "detail": "Conflict already resolved"
}
```

### 401 Unauthorized

```json
{
  "detail": "Could not validate credentials"
}
```

### 403 Forbidden

```json
{
  "detail": "Insufficient permissions"
}
```

### 404 Not Found

```json
{
  "detail": "Conflict 999 not found"
}
```

### 429 Too Many Requests

```json
{
  "detail": "Rate limit exceeded. Maximum 10 requests per minute."
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error during conflict resolution"
}
```

---

## Rate Limiting

### Rate Limit Headers

All responses include rate limit information:

```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 60
```

### Rate Limits by Endpoint

| Endpoint | Limit | Window |
|----------|-------|--------|
| POST /conflicts/{id}/resolve | 10 | 1 minute |
| POST /trains/{id}/control | 10 | 1 minute |
| GET /conflicts/active | 30 | 1 minute |
| POST /decisions/log | 30 | 1 minute |
| GET /audit/decisions | 30 | 1 minute |

### Rate Limit Implementation

Rate limiting uses Redis for distributed tracking:

```python
# Rate limit key format
rate_limit:{controller_id}:{endpoint}

# TTL: 60 seconds
# Increment on each request
# Reject when count > limit
```

---

## WebSocket Notifications

Controller actions trigger real-time WebSocket notifications to all connected clients.

### Connection

```javascript
const ws = new WebSocket('ws://localhost:8000/api/ws');

ws.onopen = () => {
  console.log('Connected to railway control WebSocket');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  handleNotification(message);
};
```

### Notification Types

#### Conflict Resolved

```json
{
  "type": "conflict_resolved",
  "conflict_id": 42,
  "action": "accept",
  "resolution_time": "2025-10-14T10:30:00Z",
  "controller_id": 1
}
```

#### Train Control

```json
{
  "type": "train_control",
  "train_id": 101,
  "train_number": "EXP2025",
  "command": "delay",
  "parameters": {
    "delay_minutes": 15
  },
  "controller_id": 1,
  "timestamp": "2025-10-14T10:35:00Z",
  "message": "Train delayed by 15 minutes"
}
```

#### Decision Logged

```json
{
  "type": "decision_logged",
  "decision_id": 791,
  "controller_id": 1,
  "action": "delay",
  "timestamp": "2025-10-14T10:40:00Z"
}
```

---

## Testing

### Running Unit Tests

```bash
cd backend
pytest tests/test_controller_actions.py -v
```

### Test Coverage

```bash
pytest tests/test_controller_actions.py --cov=app.routes.controller --cov-report=html
```

### Manual Testing with cURL

#### 1. Login

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"employee_id": "CTR001", "password": "password_CTR001"}'
```

#### 2. Get Active Conflicts

```bash
curl -X GET "http://localhost:8000/api/conflicts/active" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

#### 3. Resolve Conflict

```bash
curl -X POST "http://localhost:8000/api/conflicts/42/resolve" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "accept",
    "solution_id": "ai_solution_12345",
    "rationale": "AI recommendation is optimal"
  }'
```

#### 4. Control Train

```bash
curl -X POST "http://localhost:8000/api/trains/101/control" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "delay",
    "parameters": {"delay_minutes": 15},
    "reason": "Track maintenance ahead",
    "emergency": false
  }'
```

#### 5. Log Decision

```bash
curl -X POST "http://localhost:8000/api/decisions/log" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "train_id": 101,
    "action_taken": "delay",
    "rationale": "Manual delay to prevent congestion",
    "parameters": {"delay_minutes": 10}
  }'
```

#### 6. Query Audit Trail

```bash
curl -X GET "http://localhost:8000/api/audit/decisions?controller_id=1&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

---

## Authorization Levels

### Operator
- View active conflicts
- Log decisions
- Query audit trail (own decisions)

### Supervisor
- All Operator permissions
- Resolve conflicts
- Control trains (non-emergency)
- Query full audit trail

### Manager
- All Supervisor permissions
- Emergency train control
- Performance metrics
- System-wide audit access

### Admin
- All Manager permissions
- System configuration
- Controller management
- Full system access

---

## Best Practices

### 1. Decision Rationale

Always provide clear, detailed rationales:

✅ **Good:**
```
"Extended delay to 10 minutes from AI's 5-minute recommendation based on 
current weather conditions (heavy fog) and reduced visibility at junction J12"
```

❌ **Bad:**
```
"Changed delay time"
```

### 2. Emergency Commands

Use emergency flag only for true emergencies:

- Track obstructions
- Equipment failures
- Safety hazards
- Critical passenger situations

### 3. Rate Limit Management

- Batch related operations
- Use WebSocket notifications instead of polling
- Cache active conflicts locally
- Implement exponential backoff for retries

### 4. Audit Trail

- Log all manual interventions
- Include outcome when known
- Reference related conflicts
- Document decision-making process

---

## Support

For issues or questions:
- **Technical Support:** tech-support@railway.com
- **Documentation:** https://docs.railway.com/controller-api
- **Emergency Hotline:** +1-800-RAILWAY

---

## Changelog

### Version 1.0.0 (2025-10-14)
- Initial release
- 5 controller action endpoints
- Rate limiting implementation
- WebSocket notifications
- Comprehensive audit trail
- Performance metrics

---

## License

© 2025 Railway Traffic Management System. All rights reserved.
