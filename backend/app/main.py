import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from fastapi import FastAPI, Request, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from .db import get_engine
from .redis_client import startup_redis, shutdown_redis, get_redis
from .websocket_manager import connection_manager
from .schemas import HealthResponse, PerformanceMetrics, APIResponse

# Import route modules
from .routes import auth, positions, sections, websocket
from .conflict_scheduler import start_conflict_detection, stop_conflict_detection, get_conflict_detection_status, run_manual_conflict_detection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting Railway Traffic Management API...")
    
    # Initialize Redis
    await startup_redis()
    
    # Set Redis client for WebSocket manager
    redis_client = await get_redis()
    connection_manager.set_redis_client(redis_client)
    
    # Start conflict detection scheduler
    await start_conflict_detection(redis_client)
    logger.info("Conflict detection scheduler started")
    
    logger.info("Railway Traffic Management API started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Railway Traffic Management API...")
    
    # Stop conflict detection scheduler
    await stop_conflict_detection()
    logger.info("Conflict detection scheduler stopped")
    
    # Cleanup WebSocket connections
    await connection_manager.cleanup()
    
    # Shutdown Redis
    await shutdown_redis()
    
    logger.info("Railway Traffic Management API shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Railway Traffic Management API",
    description="Real-time railway position tracking and traffic management system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
origins = [
    os.getenv("FRONTEND_URL", "http://localhost:5173"),
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",  # React dev server
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.utcnow()
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = (datetime.utcnow() - start_time).total_seconds() * 1000
    
    # Log request
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.2f}ms"
    )
    
    # Add performance headers
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Timestamp"] = start_time.isoformat()
    
    return response

# Include routers
app.include_router(auth.router)
app.include_router(positions.router)
app.include_router(sections.router)
app.include_router(websocket.router)

# Health check endpoints
@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Health check endpoint
    
    Returns system status and component health
    """
    try:
        # Check database
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"
    
    # Check Redis
    try:
        redis_client = await get_redis()
        if await redis_client.is_connected():
            redis_status = "healthy"
        else:
            redis_status = "unhealthy"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_status = "unhealthy"
    
    # Get WebSocket stats
    ws_stats = connection_manager.get_connection_stats()
    
    # Determine overall status
    overall_status = "healthy" if db_status == "healthy" and redis_status == "healthy" else "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version="1.0.0",
        database_status=db_status,
        redis_status=redis_status,
        active_connections=ws_stats["total_connections"]
    )


@app.get("/api/db-check", tags=["Health"])
async def database_check():
    """
    Detailed database connectivity check
    """
    try:
        engine = get_engine()
        with engine.connect() as conn:
            # Test basic connectivity
            result = conn.execute(text("SELECT version()")).scalar_one()
            
            # Test TimescaleDB extension
            timescale_version = conn.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'")
            ).scalar_one_or_none()
            
            # Test PostGIS extension
            postgis_version = conn.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'postgis'")
            ).scalar_one_or_none()
        
        return APIResponse(
            success=True,
            message="Database connectivity check passed",
            data={
                "postgresql_version": result,
                "timescaledb_version": timescale_version,
                "postgis_version": postgis_version,
                "extensions_available": {
                    "timescaledb": timescale_version is not None,
                    "postgis": postgis_version is not None
                }
            }
        )
    
    except Exception as e:
        logger.error(f"Database check failed: {e}")
        return APIResponse(
            success=False,
            message="Database connectivity check failed",
            data={"error": str(e)}
        )


@app.get("/api/performance", response_model=PerformanceMetrics, tags=["Monitoring"])
async def get_performance_metrics():
    """
    Get system performance metrics
    """
    try:
        redis_client = await get_redis()
        
        # Get metrics from Redis
        position_updates = await redis_client.get_counter("position_updates_total")
        bulk_updates = await redis_client.get_counter("bulk_position_updates_total")
        
        # Get WebSocket stats
        ws_stats = connection_manager.get_connection_stats()
        
        # Calculate cache hit rate (simplified)
        cache_hits = await redis_client.get_counter("cache_hits") or 0
        cache_misses = await redis_client.get_counter("cache_misses") or 0
        cache_hit_rate = (cache_hits / (cache_hits + cache_misses) * 100) if (cache_hits + cache_misses) > 0 else 0
        
        # Get database connection info
        engine = get_engine()
        db_connections = engine.pool.size()
        
        # Count active trains (from cache or database)
        active_trains = len(await redis_client.get_active_trains())
        
        return PerformanceMetrics(
            total_trains=active_trains,
            active_trains=active_trains,
            position_updates_per_minute=position_updates,  # This would need time-based calculation
            average_response_time_ms=50.0,  # This would need actual measurement
            active_websocket_connections=ws_stats["total_connections"],
            cache_hit_rate=cache_hit_rate,
            database_connections=db_connections
        )
    
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving performance metrics"
        )


@app.get("/api/system-info", tags=["Monitoring"])
async def get_system_info():
    """
    Get comprehensive system information
    """
    try:
        # Get WebSocket connection stats
        ws_stats = connection_manager.get_connection_stats()
        
        # Get Redis info
        redis_client = await get_redis()
        redis_connected = await redis_client.is_connected()
        
        # Get database info
        engine = get_engine()
        with engine.connect() as conn:
            db_version = conn.execute(text("SELECT version()")).scalar_one()
        
        return APIResponse(
            success=True,
            message="System information retrieved",
            data={
                "api_version": "1.0.0",
                "timestamp": datetime.utcnow().isoformat(),
                "database": {
                    "connected": True,
                    "version": db_version,
                    "pool_size": engine.pool.size()
                },
                "redis": {
                    "connected": redis_connected,
                    "url": os.getenv("REDIS_URL", "redis://localhost:6379/0")
                },
                "websocket": ws_stats,
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
        )
    
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving system information"
        )


# Conflict Detection API Endpoints
@app.get("/api/conflicts/status", tags=["Conflict Detection"])
async def get_conflict_detection_status_api():
    """
    Get current conflict detection system status and metrics
    """
    try:
        status = get_conflict_detection_status()
        return APIResponse(
            success=True,
            message="Conflict detection status retrieved",
            data=status
        )
    except Exception as e:
        logger.error(f"Error getting conflict detection status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving conflict detection status"
        )


@app.post("/api/conflicts/detect", tags=["Conflict Detection"])
@limiter.limit("5/minute")
async def run_manual_conflict_detection_api(request: Request):
    """
    Run conflict detection manually (for testing/debugging)
    Rate limited to 5 requests per minute
    """
    try:
        result = await run_manual_conflict_detection()
        return APIResponse(
            success=result.get('success', True),
            message="Manual conflict detection completed",
            data=result
        )
    except Exception as e:
        logger.error(f"Error running manual conflict detection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error running conflict detection"
        )


@app.get("/api/conflicts/history", tags=["Conflict Detection"])
async def get_conflict_history():
    """
    Get historical conflict data from database
    """
    try:
        from .db import get_db
        from .models import Conflict
        
        db = next(get_db())
        
        # Get recent conflicts (last 24 hours)
        conflicts = db.query(Conflict).filter(
            Conflict.detection_time >= datetime.utcnow() - timedelta(hours=24)
        ).order_by(Conflict.detection_time.desc()).limit(100).all()
        
        conflict_data = []
        for conflict in conflicts:
            conflict_data.append({
                'id': conflict.id,
                'type': conflict.conflict_type,
                'severity': conflict.severity.value,
                'trains_involved': conflict.trains_involved,
                'sections_involved': conflict.sections_involved,
                'detection_time': conflict.detection_time.isoformat(),
                'resolution_time': conflict.resolution_time.isoformat() if conflict.resolution_time else None,
                'description': conflict.description,
                'auto_resolved': conflict.auto_resolved,
                'estimated_impact_minutes': conflict.estimated_impact_minutes
            })
        
        return APIResponse(
            success=True,
            message=f"Retrieved {len(conflict_data)} conflicts from last 24 hours",
            data={
                'conflicts': conflict_data,
                'total_count': len(conflict_data),
                'time_range': '24 hours'
            }
        )
    
    except Exception as e:
        logger.error(f"Error getting conflict history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving conflict history"
        )


@app.get("/api/conflicts/metrics", tags=["Conflict Detection"])
async def get_conflict_metrics():
    """
    Get conflict detection performance metrics and statistics
    """
    try:
        from .db import get_db
        from .models import Conflict
        from sqlalchemy import func
        
        db = next(get_db())
        
        # Get conflict statistics
        total_conflicts = db.query(func.count(Conflict.id)).scalar()
        
        resolved_conflicts = db.query(func.count(Conflict.id)).filter(
            Conflict.resolution_time.isnot(None)
        ).scalar()
        
        # Conflicts by severity
        severity_stats = db.query(
            Conflict.severity,
            func.count(Conflict.id)
        ).group_by(Conflict.severity).all()
        
        # Conflicts by type
        type_stats = db.query(
            Conflict.conflict_type,
            func.count(Conflict.id)
        ).group_by(Conflict.conflict_type).all()
        
        # Recent conflicts (last hour)
        recent_conflicts = db.query(func.count(Conflict.id)).filter(
            Conflict.detection_time >= datetime.utcnow() - timedelta(hours=1)
        ).scalar()
        
        # Get system status
        system_status = get_conflict_detection_status()
        
        return APIResponse(
            success=True,
            message="Conflict detection metrics retrieved",
            data={
                'total_conflicts': total_conflicts,
                'resolved_conflicts': resolved_conflicts,
                'resolution_rate': (resolved_conflicts / total_conflicts * 100) if total_conflicts > 0 else 0,
                'recent_conflicts_1h': recent_conflicts,
                'severity_distribution': {
                    str(severity): count for severity, count in severity_stats
                },
                'type_distribution': {
                    conflict_type: count for conflict_type, count in type_stats
                },
                'system_performance': system_status.get('stats', {}),
                'detection_system_status': system_status.get('is_running', False)
            }
        )
    
    except Exception as e:
        logger.error(f"Error getting conflict metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving conflict metrics"
        )


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """
    Railway Traffic Management API root endpoint
    """
    return {
        "message": "Railway Traffic Management API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
        "websocket": "/ws/positions",
        "timestamp": datetime.utcnow().isoformat()
    }
