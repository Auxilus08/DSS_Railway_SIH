"""
WebSocket routes for real-time railway position streaming
"""

import json
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.orm import Session
from ..db import get_session
from ..models import Controller
from ..auth import verify_token
from ..websocket_manager import connection_manager
from ..redis_client import get_redis, RedisClient
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


async def authenticate_websocket(
    websocket: WebSocket,
    token: Optional[str] = None
) -> Optional[Controller]:
    """Authenticate WebSocket connection using JWT token"""
    
    if not token:
        return None
    
    try:
        token_data = verify_token(token)
        if not token_data:
            return None
        
        # Get controller from database
        db = next(get_session())
        controller = db.query(Controller).filter(
            Controller.employee_id == token_data.employee_id,
            Controller.active == True
        ).first()
        
        return controller
    
    except Exception as e:
        logger.error(f"WebSocket authentication error: {e}")
        return None


@router.websocket("/ws/positions")
async def websocket_positions(
    websocket: WebSocket,
    token: Optional[str] = Query(None, description="JWT authentication token"),
    client_id: Optional[str] = Query(None, description="Client identifier"),
    redis_client: RedisClient = Depends(get_redis)
):
    """
    WebSocket endpoint for real-time train position streaming
    
    Authentication is optional but recommended for production use.
    
    Message Types:
    - position_update: Real-time train position updates
    - conflict_alert: Conflict detection alerts
    - system_status: System status updates
    
    Client can send subscription messages:
    - {"type": "subscribe_train", "data": {"train_id": 123}}
    - {"type": "subscribe_section", "data": {"section_id": 456}}
    - {"type": "subscribe_all", "data": {}}
    - {"type": "ping", "data": {}}
    """
    
    # Generate connection ID
    connection_id = client_id or str(uuid.uuid4())
    
    # Authenticate if token provided
    controller = None
    if token:
        controller = await authenticate_websocket(websocket, token)
        if not controller:
            await websocket.close(code=4001, reason="Invalid authentication token")
            return
    
    # Prepare connection metadata
    metadata = {
        "connected_at": datetime.utcnow().isoformat(),
        "authenticated": controller is not None,
        "controller_id": controller.id if controller else None,
        "controller_name": controller.name if controller else None,
        "auth_level": controller.auth_level.value if controller else None,
        "client_id": client_id
    }
    
    try:
        # Accept connection
        await connection_manager.connect(websocket, connection_id, metadata)
        
        # Set Redis client for pub/sub
        connection_manager.set_redis_client(redis_client)
        
        # Start Redis listener if not already running
        await connection_manager.start_redis_listener()
        
        # Log connection
        logger.info(f"WebSocket connected: {connection_id} (authenticated: {controller is not None})")
        
        # Send initial system status
        await connection_manager.send_personal_message({
            "type": "system_status",
            "data": {
                "status": "connected",
                "server_time": datetime.utcnow().isoformat(),
                "connection_id": connection_id,
                "authenticated": controller is not None,
                "available_subscriptions": [
                    "subscribe_train",
                    "subscribe_section", 
                    "subscribe_all",
                    "unsubscribe_train",
                    "unsubscribe_section",
                    "ping"
                ]
            }
        }, connection_id)
        
        # Main message loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle client message
                await connection_manager.handle_client_message(connection_id, message)
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {connection_id}")
                break
            
            except json.JSONDecodeError:
                # Send error for invalid JSON
                await connection_manager.send_personal_message({
                    "type": "error",
                    "data": {"message": "Invalid JSON format"}
                }, connection_id)
            
            except Exception as e:
                logger.error(f"Error handling WebSocket message from {connection_id}: {e}")
                await connection_manager.send_personal_message({
                    "type": "error",
                    "data": {"message": "Error processing message"}
                }, connection_id)
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected during setup: {connection_id}")
    
    except Exception as e:
        logger.error(f"WebSocket error for {connection_id}: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
    
    finally:
        # Clean up connection
        connection_manager.disconnect(connection_id)
        logger.info(f"WebSocket cleanup completed for: {connection_id}")


@router.websocket("/ws/admin")
async def websocket_admin(
    websocket: WebSocket,
    token: str = Query(..., description="JWT authentication token (required)"),
    redis_client: RedisClient = Depends(get_redis)
):
    """
    Admin WebSocket endpoint for system monitoring
    
    Requires authentication with manager or admin level access.
    Provides additional system metrics and control capabilities.
    """
    
    # Generate connection ID
    connection_id = f"admin_{str(uuid.uuid4())}"
    
    # Authenticate (required for admin endpoint)
    controller = await authenticate_websocket(websocket, token)
    if not controller:
        await websocket.close(code=4001, reason="Authentication required")
        return
    
    # Check admin permissions
    if controller.auth_level.value not in ["manager", "admin"]:
        await websocket.close(code=4003, reason="Insufficient permissions")
        return
    
    # Prepare connection metadata
    metadata = {
        "connected_at": datetime.utcnow().isoformat(),
        "authenticated": True,
        "controller_id": controller.id,
        "controller_name": controller.name,
        "auth_level": controller.auth_level.value,
        "admin_connection": True
    }
    
    try:
        # Accept connection
        await connection_manager.connect(websocket, connection_id, metadata)
        
        # Set Redis client
        connection_manager.set_redis_client(redis_client)
        
        # Log admin connection
        logger.info(f"Admin WebSocket connected: {connection_id} (controller: {controller.name})")
        
        # Send admin welcome message
        stats = connection_manager.get_connection_stats()
        await connection_manager.send_personal_message({
            "type": "admin_connected",
            "data": {
                "status": "connected",
                "server_time": datetime.utcnow().isoformat(),
                "connection_id": connection_id,
                "controller": {
                    "id": controller.id,
                    "name": controller.name,
                    "auth_level": controller.auth_level.value
                },
                "connection_stats": stats,
                "admin_capabilities": [
                    "view_all_connections",
                    "broadcast_system_messages",
                    "monitor_performance",
                    "force_disconnect_clients"
                ]
            }
        }, connection_id)
        
        # Subscribe to all updates by default for admin
        connection_manager.subscribe_to_all(connection_id)
        
        # Main message loop
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                message_type = message.get("type")
                
                # Handle admin-specific messages
                if message_type == "get_connection_stats":
                    stats = connection_manager.get_connection_stats()
                    await connection_manager.send_personal_message({
                        "type": "connection_stats",
                        "data": stats
                    }, connection_id)
                
                elif message_type == "broadcast_system_message":
                    # Broadcast message to all connected clients
                    broadcast_data = message.get("data", {})
                    await connection_manager.broadcast_system_status({
                        "message_type": "admin_broadcast",
                        "from_controller": controller.name,
                        "timestamp": datetime.utcnow().isoformat(),
                        **broadcast_data
                    })
                    
                    await connection_manager.send_personal_message({
                        "type": "broadcast_sent",
                        "data": {"message": "System message broadcasted"}
                    }, connection_id)
                
                elif message_type == "get_performance_metrics":
                    # Get performance metrics from Redis
                    metrics = {
                        "position_updates_total": await redis_client.get_counter("position_updates_total"),
                        "bulk_updates_total": await redis_client.get_counter("bulk_position_updates_total"),
                        "active_connections": len(connection_manager.active_connections),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
                    await connection_manager.send_personal_message({
                        "type": "performance_metrics",
                        "data": metrics
                    }, connection_id)
                
                else:
                    # Handle regular client messages
                    await connection_manager.handle_client_message(connection_id, message)
                
            except WebSocketDisconnect:
                logger.info(f"Admin WebSocket disconnected: {connection_id}")
                break
            
            except json.JSONDecodeError:
                await connection_manager.send_personal_message({
                    "type": "error",
                    "data": {"message": "Invalid JSON format"}
                }, connection_id)
            
            except Exception as e:
                logger.error(f"Error handling admin WebSocket message from {connection_id}: {e}")
                await connection_manager.send_personal_message({
                    "type": "error",
                    "data": {"message": "Error processing admin message"}
                }, connection_id)
    
    except WebSocketDisconnect:
        logger.info(f"Admin WebSocket disconnected during setup: {connection_id}")
    
    except Exception as e:
        logger.error(f"Admin WebSocket error for {connection_id}: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except:
            pass
    
    finally:
        # Clean up connection
        connection_manager.disconnect(connection_id)
        logger.info(f"Admin WebSocket cleanup completed for: {connection_id}")


@router.get("/ws/stats")
async def get_websocket_stats():
    """
    Get WebSocket connection statistics
    
    Public endpoint for monitoring WebSocket health
    """
    
    try:
        stats = connection_manager.get_connection_stats()
        
        return {
            "success": True,
            "data": {
                **stats,
                "timestamp": datetime.utcnow().isoformat(),
                "server_status": "healthy"
            }
        }
    
    except Exception as e:
        logger.error(f"Error getting WebSocket stats: {e}")
        return {
            "success": False,
            "error": "Error retrieving WebSocket statistics",
            "timestamp": datetime.utcnow().isoformat()
        }