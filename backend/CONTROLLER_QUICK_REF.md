# Controller Action APIs - Quick Reference

## 🚀 Quick Start

### 1. Login
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"employee_id":"CTR001","password":"password_CTR001"}'
```

### 2. Use Token
```bash
export TOKEN="your_jwt_token_here"
```

---

## 📋 API Endpoints

### Get Active Conflicts
```bash
GET /api/conflicts/active
Authorization: Bearer {token}
```

### Resolve Conflict
```bash
POST /api/conflicts/{conflict_id}/resolve
{
  "action": "accept|modify|reject",
  "solution_id": "string",
  "modifications": {},
  "rationale": "string (min 10 chars)"
}
```

### Control Train
```bash
POST /api/trains/{train_id}/control
{
  "command": "delay|reroute|priority|stop|speed_limit|resume",
  "parameters": {...},
  "reason": "string (min 10 chars)",
  "emergency": false
}
```

### Log Decision
```bash
POST /api/decisions/log
{
  "action_taken": "string",
  "rationale": "string (min 10 chars)",
  "conflict_id": int (optional),
  "train_id": int (optional),
  "parameters": {}
}
```

### Query Audit Trail
```bash
GET /api/audit/decisions?controller_id=1&limit=10
Authorization: Bearer {token}
```

### Performance Metrics
```bash
GET /api/audit/performance?start_date=2025-01-01T00:00:00Z
Authorization: Bearer {token}
```

---

## 🔐 Authorization Levels

| Level | Permissions |
|-------|-------------|
| **Operator** | View conflicts, Log decisions, Query own audit |
| **Supervisor** | + Resolve conflicts, Control trains |
| **Manager** | + Emergency controls, Full metrics |
| **Admin** | + Full system access |

---

## ⚡ Rate Limits

| Endpoint | Limit |
|----------|-------|
| Conflict resolution | 10/min |
| Train control | 10/min |
| Active conflicts | 30/min |
| Decision logging | 30/min |
| Audit queries | 30/min |

---

## 🎯 Command Parameters

### DELAY
```json
{"delay_minutes": 15}  // 0-180
```

### REROUTE
```json
{"new_route": [12, 15, 18, 22]}  // section IDs
```

### PRIORITY
```json
{"new_priority": 8}  // 1-10
```

### STOP
```json
{}  // No parameters, requires Manager/Admin
```

### SPEED_LIMIT
```json
{"max_speed_kmh": 60}  // 0-300
```

### RESUME
```json
{}  // No parameters
```

---

## 🔔 WebSocket Events

### Subscribe
```javascript
ws.send(JSON.stringify({
  type: "subscribe_all"
}));
```

### Events
- `conflict_resolved` - Conflict resolution completed
- `train_control` - Train control executed
- `decision_logged` - Decision logged in audit

---

## ❌ Error Codes

| Code | Meaning |
|------|---------|
| 400 | Bad request / Already resolved |
| 401 | Unauthorized / Invalid token |
| 403 | Forbidden / Insufficient permissions |
| 404 | Not found |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

---

## 🧪 Testing

### Run Tests
```bash
pytest backend/tests/test_controller_actions.py -v
```

### Test Coverage
```bash
pytest backend/tests/test_controller_actions.py --cov=app.routes.controller
```

---

## 📁 Files Created

```
backend/
├── app/
│   ├── routes/
│   │   └── controller.py          # API endpoints
│   └── schemas.py                  # Updated with new schemas
├── tests/
│   └── test_controller_actions.py  # Unit tests
├── CONTROLLER_API_DOCS.md          # Full documentation
└── CONTROLLER_IMPLEMENTATION_SUMMARY.md  # Implementation summary
```

---

## 🎨 Example Workflows

### Accept AI Recommendation
```bash
curl -X POST http://localhost:8000/api/conflicts/42/resolve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "accept",
    "solution_id": "ai_solution_123",
    "rationale": "AI recommendation is optimal for current conditions"
  }'
```

### Emergency Stop
```bash
curl -X POST http://localhost:8000/api/trains/101/control \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "command": "stop",
    "parameters": {},
    "reason": "Track obstruction detected",
    "emergency": true
  }'
```

### Query Recent Decisions
```bash
curl -X GET "http://localhost:8000/api/audit/decisions?limit=20&executed_only=true" \
  -H "Authorization: Bearer $TOKEN"
```

---

## 🔧 Configuration

### Environment Variables
```bash
JWT_SECRET=your-secret-key
JWT_ALGORITHM=HS256
JWT_EXPIRES_IN=3600
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://user:pass@localhost/railway
```

---

## 📊 Key Features

✅ 5 Production-ready API endpoints
✅ Role-based access control (4 levels)
✅ Rate limiting (Redis-based)
✅ Real-time WebSocket notifications
✅ Comprehensive audit trail
✅ Background task processing
✅ Input validation (Pydantic)
✅ Transaction management
✅ Error handling
✅ 15+ unit tests
✅ Complete documentation

---

## 📞 Support

- **Documentation:** See CONTROLLER_API_DOCS.md
- **Implementation:** See CONTROLLER_IMPLEMENTATION_SUMMARY.md
- **Tests:** Run `pytest backend/tests/test_controller_actions.py -v`

---

**Status:** ✅ Production Ready

All endpoints tested and validated. Ready for deployment.
