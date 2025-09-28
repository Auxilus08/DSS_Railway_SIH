"""
WebSocket connection manager for real-time railway position tracking
"""

import json
import asyncio
from typing import Dict, List, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from .schemas import PositionBroadcast, WebSocketMessage
from .redis_client import RedisClient
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""
    
    def __init__(self):
        # Active connections by connection ID
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Subscriptions by train ID
        self.train_subscriptions: Dict[int, Set[str]] = {}
        
        # Subscriptions by section ID
        self.section_subscriptions: Dict[int, Set[str]] = {}
        
        # Phase 4: AI-specific subscriptions
        self.ai_subscribers: Set[str] = set()
        self.ai_training_subscribers: Set[str] = set()
        
        # General subscribers (all updates)
        self.general_subscribers: Set[str] = set()
        
        # Connection metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
        # Redis client for pub/sub
        self.redis_client: Optional[RedisClient] = None
        
        # Background tasks
        self.background_tasks: Set[asyncio.Task] = set()
    
    def set_redis_client(self, redis_client: RedisClient):
        """Set Redis client for pub/sub functionality"""
        self.redis_client = redis_client
    
    async def connect(self, websocket: WebSocket, connection_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Accept new WebSocket connection"""
        await websocket.accept()
        
        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = metadata or {}
        
        logger.info(f"WebSocket connection established: {connection_id}")
        
        # Send welcome message
        welcome_message = WebSocketMessage(
            type="connection_established",
            data={
                "connection_id": connection_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Connected to Railway Traffic Management System"
            }
        )
        
        await self.send_personal_message(welcome_message.dict(), connection_id)
    
    def disconnect(self, connection_id: str):
        """Remove WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        if connection_id in self.connection_metadata:
            del self.connection_metadata[connection_id]
        
        # Remove from all subscriptions
        self.general_subscribers.discard(connection_id)
        
        # Phase 4: Remove from AI subscriptions
        self.ai_subscribers.discard(connection_id)
        self.ai_training_subscribers.discard(connection_id)
        
        for train_id in list(self.train_subscriptions.keys()):
            self.train_subscriptions[train_id].discard(connection_id)
            if not self.train_subscriptions[train_id]:
                del self.train_subscriptions[train_id]
        
        for section_id in list(self.section_subscriptions.keys()):
            self.section_subscriptions[section_id].discard(connection_id)
            if not self.section_subscriptions[section_id]:
                del self.section_subscriptions[section_id]
        
        logger.info(f"WebSocket connection closed: {connection_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], connection_id: str):
        """Send message to specific connection"""
        if connection_id in self.active_connections:
            try:
                websocket = self.active_connections[connection_id]
                await websocket.send_text(json.dumps(message, default=str))
            except Exception as e:
                logger.error(f"Error sending message to {connection_id}: {e}")
                # Remove broken connection
                self.disconnect(connection_id)
    
    async def broadcast_to_all(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return
        
        message_text = json.dumps(message, default=str)
        
        # Send to all connections concurrently
        tasks = []
        for connection_id, websocket in list(self.active_connections.items()):
            task = asyncio.create_task(self._safe_send(websocket, message_text, connection_id))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def broadcast_to_subscribers(self, message: Dict[str, Any], subscribers: Set[str]):
        """Broadcast message to specific subscribers"""
        if not subscribers:
            return
        
        message_text = json.dumps(message, default=str)
        
        tasks = []
        for connection_id in list(subscribers):
            if connection_id in self.active_connections:
                websocket = self.active_connections[connection_id]
                task = asyncio.create_task(self._safe_send(websocket, message_text, connection_id))
                tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _safe_send(self, websocket: WebSocket, message: str, connection_id: str):
        """Safely send message to WebSocket"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Error sending to {connection_id}: {e}")
            self.disconnect(connection_id)
    
    # Subscription management
    def subscribe_to_train(self, connection_id: str, train_id: int):
        """Subscribe connection to train updates"""
        if train_id not in self.train_subscriptions:
            self.train_subscriptions[train_id] = set()
        
        self.train_subscriptions[train_id].add(connection_id)
        logger.info(f"Connection {connection_id} subscribed to train {train_id}")
    
    def unsubscribe_from_train(self, connection_id: str, train_id: int):
        """Unsubscribe connection from train updates"""
        if train_id in self.train_subscriptions:
            self.train_subscriptions[train_id].discard(connection_id)
            if not self.train_subscriptions[train_id]:
                del self.train_subscriptions[train_id]
        
        logger.info(f"Connection {connection_id} unsubscribed from train {train_id}")
    
    def subscribe_to_section(self, connection_id: str, section_id: int):
        """Subscribe connection to section updates"""
        if section_id not in self.section_subscriptions:
            self.section_subscriptions[section_id] = set()
        
        self.section_subscriptions[section_id].add(connection_id)
        logger.info(f"Connection {connection_id} subscribed to section {section_id}")
    
    def unsubscribe_from_section(self, connection_id: str, section_id: int):
        """Unsubscribe connection from section updates"""
        if section_id in self.section_subscriptions:
            self.section_subscriptions[section_id].discard(connection_id)
            if not self.section_subscriptions[section_id]:
                del self.section_subscriptions[section_id]
        
        logger.info(f"Connection {connection_id} unsubscribed from section {section_id}")
    
    def subscribe_to_all(self, connection_id: str):
        """Subscribe connection to all updates"""
        self.general_subscribers.add(connection_id)
        logger.info(f"Connection {connection_id} subscribed to all updates")
    
    def unsubscribe_from_all(self, connection_id: str):
        """Unsubscribe connection from all updates"""
        self.general_subscribers.discard(connection_id)
        logger.info(f"Connection {connection_id} unsubscribed from all updates")
    
    def subscribe_to_ai_updates(self, connection_id: str):
        """
        Phase 4: Subscribe connection to AI optimization updates
        """
        self.ai_subscribers.add(connection_id)
        logger.info(f"Connection {connection_id} subscribed to AI updates")
    
    def unsubscribe_from_ai_updates(self, connection_id: str):
        """
        Phase 4: Unsubscribe connection from AI optimization updates
        """
        self.ai_subscribers.discard(connection_id)
        logger.info(f"Connection {connection_id} unsubscribed from AI updates")
    
    def subscribe_to_ai_training(self, connection_id: str):
        """
        Phase 4: Subscribe connection to AI training updates
        """
        self.ai_training_subscribers.add(connection_id)
        logger.info(f"Connection {connection_id} subscribed to AI training updates")
    
    def unsubscribe_from_ai_training(self, connection_id: str):
        """
        Phase 4: Unsubscribe connection from AI training updates
        """
        self.ai_training_subscribers.discard(connection_id)
        logger.info(f"Connection {connection_id} unsubscribed from AI training updates")
    
    # Broadcasting methods
    async def broadcast_position_update(self, position_broadcast: PositionBroadcast):
        """Broadcast train position update"""
        message = position_broadcast.dict()
        
        # Send to general subscribers
        await self.broadcast_to_subscribers(message, self.general_subscribers)
        
        # Send to train-specific subscribers
        train_id = position_broadcast.train_id
        if train_id in self.train_subscriptions:
            await self.broadcast_to_subscribers(message, self.train_subscriptions[train_id])
        
        # Send to section-specific subscribers
        section_id = position_broadcast.position.section_id
        if section_id in self.section_subscriptions:
            await self.broadcast_to_subscribers(message, self.section_subscriptions[section_id])
    
    async def broadcast_conflict_alert(self, conflict_data: Dict[str, Any]):
        """Broadcast conflict alert"""
        message = WebSocketMessage(
            type="conflict_alert",
            data=conflict_data
        )
        
        await self.broadcast_to_all(message.dict())
    
    async def broadcast_ai_update(self, ai_data: Dict[str, Any]):
        """
        Phase 4: Broadcast AI optimization results
        Real-time AI notifications for conflict resolution
        """
        message = WebSocketMessage(
            type="ai_optimization",
            data=ai_data
        )
        
        # Send to AI subscribers
        await self.broadcast_to_subscribers(message.dict(), self.ai_subscribers)
        
        # Also send to general subscribers
        await self.broadcast_to_subscribers(message.dict(), self.general_subscribers)
        
        # Send to specific train/section subscribers if applicable
        train_id = ai_data.get("train_id")
        if train_id and train_id in self.train_subscriptions:
            await self.broadcast_to_subscribers(message.dict(), self.train_subscriptions[train_id])
        
        section_id = ai_data.get("section_id")
        if section_id and section_id in self.section_subscriptions:
            await self.broadcast_to_subscribers(message.dict(), self.section_subscriptions[section_id])
    
    async def broadcast_ai_training_update(self, training_data: Dict[str, Any]):
        """
        Phase 4: Broadcast AI training progress updates
        """
        message = WebSocketMessage(
            type="ai_training",
            data=training_data
        )
        
        # Send to AI training subscribers
        await self.broadcast_to_subscribers(message.dict(), self.ai_training_subscribers)
        
        # Also send to general subscribers
        await self.broadcast_to_subscribers(message.dict(), self.general_subscribers)
    
    async def broadcast_system_status(self, status_data: Dict[str, Any]):
        """Broadcast system status update"""
        message = WebSocketMessage(
            type="system_status",
            data=status_data
        )
        
        await self.broadcast_to_subscribers(message.dict(), self.general_subscribers)
    
    # Connection statistics
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "total_connections": len(self.active_connections),
            "general_subscribers": len(self.general_subscribers),
            "train_subscriptions": len(self.train_subscriptions),
            "section_subscriptions": len(self.section_subscriptions),
            "active_train_subscriptions": sum(len(subs) for subs in self.train_subscriptions.values()),
            "active_section_subscriptions": sum(len(subs) for subs in self.section_subscriptions.values()),
            # Phase 4: AI subscription stats
            "ai_subscribers": len(self.ai_subscribers),
            "ai_training_subscribers": len(self.ai_training_subscribers)
        }
    
    # Message handling
    async def handle_client_message(self, connection_id: str, message: Dict[str, Any]):
        """Handle incoming message from client"""
        message_type = message.get("type")
        data = message.get("data", {})
        
        try:
            if message_type == "subscribe_train":
                train_id = data.get("train_id")
                if train_id:
                    self.subscribe_to_train(connection_id, train_id)
                    await self.send_personal_message({
                        "type": "subscription_confirmed",
                        "data": {"train_id": train_id}
                    }, connection_id)
            
            elif message_type == "unsubscribe_train":
                train_id = data.get("train_id")
                if train_id:
                    self.unsubscribe_from_train(connection_id, train_id)
                    await self.send_personal_message({
                        "type": "unsubscription_confirmed",
                        "data": {"train_id": train_id}
                    }, connection_id)
            
            elif message_type == "subscribe_section":
                section_id = data.get("section_id")
                if section_id:
                    self.subscribe_to_section(connection_id, section_id)
                    await self.send_personal_message({
                        "type": "subscription_confirmed",
                        "data": {"section_id": section_id}
                    }, connection_id)
            
            elif message_type == "subscribe_all":
                self.subscribe_to_all(connection_id)
                await self.send_personal_message({
                    "type": "subscription_confirmed",
                    "data": {"scope": "all"}
                }, connection_id)
            
            # Phase 4: AI subscription handlers
            elif message_type == "subscribe_ai":
                self.subscribe_to_ai_updates(connection_id)
                await self.send_personal_message({
                    "type": "subscription_confirmed",
                    "data": {"scope": "ai_updates"}
                }, connection_id)
            
            elif message_type == "unsubscribe_ai":
                self.unsubscribe_from_ai_updates(connection_id)
                await self.send_personal_message({
                    "type": "unsubscription_confirmed",
                    "data": {"scope": "ai_updates"}
                }, connection_id)
            
            elif message_type == "subscribe_ai_training":
                self.subscribe_to_ai_training(connection_id)
                await self.send_personal_message({
                    "type": "subscription_confirmed",
                    "data": {"scope": "ai_training"}
                }, connection_id)
            
            elif message_type == "unsubscribe_ai_training":
                self.unsubscribe_from_ai_training(connection_id)
                await self.send_personal_message({
                    "type": "unsubscription_confirmed",
                    "data": {"scope": "ai_training"}
                }, connection_id)
            
            elif message_type == "ping":
                await self.send_personal_message({
                    "type": "pong",
                    "data": {"timestamp": datetime.utcnow().isoformat()}
                }, connection_id)
            
            else:
                await self.send_personal_message({
                    "type": "error",
                    "data": {"message": f"Unknown message type: {message_type}"}
                }, connection_id)
        
        except Exception as e:
            logger.error(f"Error handling client message from {connection_id}: {e}")
            await self.send_personal_message({
                "type": "error",
                "data": {"message": "Error processing message"}
            }, connection_id)
    
    # Redis pub/sub integration
    async def start_redis_listener(self):
        """Start Redis pub/sub listener for cross-instance communication"""
        if not self.redis_client:
            logger.warning("Redis client not available for pub/sub")
            return
        
        try:
            pubsub = await self.redis_client.subscribe([
                "railway:positions",
                "railway:conflicts",
                "railway:system"
            ])
            
            if pubsub:
                task = asyncio.create_task(self._redis_message_handler(pubsub))
                self.background_tasks.add(task)
                task.add_done_callback(self.background_tasks.discard)
        
        except Exception as e:
            logger.error(f"Error starting Redis listener: {e}")
    
    async def _redis_message_handler(self, pubsub):
        """Handle messages from Redis pub/sub"""
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    channel = message["channel"]
                    data = json.loads(message["data"])
                    
                    if channel == "railway:positions":
                        position_broadcast = PositionBroadcast(**data)
                        await self.broadcast_position_update(position_broadcast)
                    
                    elif channel == "railway:conflicts":
                        await self.broadcast_conflict_alert(data)
                    
                    elif channel == "railway:system":
                        await self.broadcast_system_status(data)
        
        except Exception as e:
            logger.error(f"Error in Redis message handler: {e}")
    
    async def cleanup(self):
        """Cleanup resources"""
        # Cancel background tasks
        for task in self.background_tasks:
            task.cancel()
        
        if self.background_tasks:
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        
        # Close all connections
        for connection_id in list(self.active_connections.keys()):
            try:
                websocket = self.active_connections[connection_id]
                await websocket.close()
            except:
                pass
        
        self.active_connections.clear()
        self.connection_metadata.clear()
        self.train_subscriptions.clear()
        self.section_subscriptions.clear()
        self.general_subscribers.clear()


# Global connection manager instance
connection_manager = ConnectionManager()