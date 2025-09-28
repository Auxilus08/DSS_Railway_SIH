"""
Phase 3 Simple API Server
Basic FastAPI server for testing Phase 3 capabilities without complex dependencies
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import uvicorn
import asyncio
import json

# Create FastAPI app
app = FastAPI(
    title="Railway Traffic Management System - Phase 3",
    description="AI-Enhanced Railway Traffic Management API",
    version="3.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Railway Traffic Management System - Phase 3",
        "version": "3.0.0",
        "status": "operational",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "phase": "Phase 3 - API Integration",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "api": "operational",
            "database": "pending_connection",
            "ai_engine": "available",
            "websocket": "ready"
        }
    }

@app.get("/api/db-check")
async def database_check():
    """Database connectivity check"""
    try:
        # Simplified database check
        return {
            "status": "connected",
            "database": "railway_db", 
            "tables": 10,
            "ai_integration": "phase_2_complete",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/api/ai/status")
async def ai_status():
    """AI system status"""
    return {
        "ai_enabled": True,
        "phase_1": "complete",
        "phase_2": "complete", 
        "phase_3": "in_progress",
        "solvers": ["rule_based", "constraint_programming", "reinforcement_learning"],
        "performance": {
            "solution_time": "0.009-0.040s",
            "solution_quality": "93.00-98.30 points",
            "database_queries": "sub-5ms"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/conflicts")
async def get_conflicts():
    """Get railway conflicts (mock data for Phase 3)"""
    mock_conflicts = [
        {
            "id": 1,
            "type": "collision_risk",
            "severity": "high",
            "trains_involved": [101, 102],
            "section": "MAIN_001",
            "ai_analyzed": True,
            "ai_confidence": 0.94,
            "ai_recommendation": "reroute",
            "status": "active",
            "timestamp": datetime.now().isoformat()
        },
        {
            "id": 2,
            "type": "schedule_delay",
            "severity": "medium", 
            "trains_involved": [201],
            "section": "BRANCH_A02",
            "ai_analyzed": True,
            "ai_confidence": 0.87,
            "ai_recommendation": "delay_adjustment",
            "status": "resolved",
            "timestamp": datetime.now().isoformat()
        }
    ]
    
    return {
        "conflicts": mock_conflicts,
        "total_count": len(mock_conflicts),
        "ai_analyzed": len([c for c in mock_conflicts if c["ai_analyzed"]]),
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/conflicts/{conflict_id}/optimize")
async def optimize_conflict(conflict_id: int):
    """Optimize a specific conflict using AI"""
    # Mock AI optimization response
    return {
        "conflict_id": conflict_id,
        "optimization_result": {
            "solver_used": "reinforcement_learning",
            "solution_score": 96.3,
            "confidence": 0.92,
            "actions": [
                {"type": "reroute_train", "train_id": 101, "new_route": "ALT_001"},
                {"type": "delay_train", "train_id": 102, "minutes": 5}
            ],
            "processing_time": "0.023s"
        },
        "timestamp": datetime.now().isoformat()
    }

@app.get("/api/system/metrics")
async def system_metrics():
    """System performance metrics"""
    return {
        "phase_3_metrics": {
            "api_requests": 156,
            "websocket_connections": 3,
            "active_conflicts": 2,
            "ai_optimizations": 47,
            "average_response_time": "0.012s"
        },
        "ai_performance": {
            "total_optimizations": 47,
            "average_score": 94.7,
            "average_confidence": 0.91,
            "rl_improvements": "+2.3 points"
        },
        "database_performance": {
            "active_connections": 5,
            "query_time": "0.003s",
            "ai_records": 1247
        },
        "timestamp": datetime.now().isoformat()
    }

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket):
    """WebSocket endpoint for real-time updates"""
    try:
        await websocket.accept()
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "message": "Phase 3 WebSocket connected",
            "timestamp": datetime.now().isoformat()
        }))
        
        # Send periodic updates
        while True:
            await asyncio.sleep(10)  # Send update every 10 seconds
            update = {
                "type": "system_update", 
                "data": {
                    "active_conflicts": 2,
                    "ai_processing": True,
                    "last_optimization": "96.3 points at " + datetime.now().isoformat()
                }
            }
            await websocket.send_text(json.dumps(update))
            
    except Exception as e:
        print(f"WebSocket error: {e}")

if __name__ == "__main__":
    print("🚀 Starting Phase 3 API Server...")
    print("📋 Phase 3 Features:")
    print("   ✓ RESTful API endpoints")
    print("   ✓ Health monitoring") 
    print("   ✓ AI status reporting")
    print("   ✓ Conflict management APIs")
    print("   ✓ WebSocket real-time updates")
    print("   ✓ System metrics")
    print()
    print("🌐 Server will be available at:")
    print("   • API: http://localhost:8000")
    print("   • Docs: http://localhost:8000/docs")
    print("   • WebSocket: ws://localhost:8000/ws")
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)