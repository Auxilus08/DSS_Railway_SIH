"""
Background task scheduler for railway conflict detection.
Runs conflict detection every 30 seconds and manages the detection pipeline.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from .conflict_detector import ConflictDetector
from .db import get_db
from .redis_client import RedisClient
from .websocket_manager import connection_manager

logger = logging.getLogger(__name__)


class ConflictDetectionScheduler:
    """
    Background task scheduler that runs conflict detection at regular intervals.
    Manages the entire conflict detection pipeline including:
    - Running detection every 30 seconds
    - Storing conflicts in database
    - Sending real-time alerts
    - Managing performance metrics
    """
    
    def __init__(self, redis_client: Optional[RedisClient] = None):
        self.redis_client = redis_client
        self.detection_interval = 30  # seconds
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.detector: Optional[ConflictDetector] = None
        
        # Performance tracking
        self.stats = {
            'runs_completed': 0,
            'runs_failed': 0,
            'total_conflicts_detected': 0,
            'alerts_sent': 0,
            'average_detection_time': 0.0,
            'last_run_time': None,
            'uptime_start': datetime.utcnow()
        }
        
        # Error tracking
        self.consecutive_failures = 0
        self.max_consecutive_failures = 5
        
    async def start(self):
        """Start the background conflict detection scheduler"""
        if self.is_running:
            logger.warning("Conflict detection scheduler is already running")
            return
        
        self.is_running = True
        self.stats['uptime_start'] = datetime.utcnow()
        
        logger.info("Starting conflict detection scheduler...")
        
        # Create the background task
        self.task = asyncio.create_task(self._detection_loop())
        
        # Log successful start
        logger.info(f"Conflict detection scheduler started successfully. Detection interval: {self.detection_interval}s")
    
    async def stop(self):
        """Stop the background conflict detection scheduler"""
        if not self.is_running:
            return
        
        logger.info("Stopping conflict detection scheduler...")
        
        self.is_running = False
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("Conflict detection scheduler stopped")
    
    async def _detection_loop(self):
        """Main detection loop that runs every 30 seconds"""
        while self.is_running:
            try:
                start_time = datetime.utcnow()
                
                # Run conflict detection
                conflicts_detected = await self._run_detection_cycle()
                
                # Update statistics
                detection_time = (datetime.utcnow() - start_time).total_seconds()
                self._update_stats(detection_time, conflicts_detected, success=True)
                
                # Reset consecutive failures on success
                self.consecutive_failures = 0
                
                logger.debug(f"Detection cycle completed in {detection_time:.2f}s, found {conflicts_detected} conflicts")
                
            except Exception as e:
                logger.error(f"Error in conflict detection cycle: {e}", exc_info=True)
                self.consecutive_failures += 1
                self._update_stats(0, 0, success=False)
                
                # Stop scheduler if too many consecutive failures
                if self.consecutive_failures >= self.max_consecutive_failures:
                    logger.critical(f"Stopping scheduler after {self.consecutive_failures} consecutive failures")
                    await self.stop()
                    break
            
            # Wait for next cycle
            if self.is_running:
                try:
                    await asyncio.sleep(self.detection_interval)
                except asyncio.CancelledError:
                    break
    
    async def _run_detection_cycle(self) -> int:
        """Run a single conflict detection cycle"""
        # Get database session
        db_session = next(get_db())
        
        try:
            # Initialize detector
            if not self.detector:
                self.detector = ConflictDetector(db_session, self.redis_client)
            else:
                # Update detector's database session
                self.detector.db = db_session
            
            # Run conflict detection
            conflicts = await self.detector.detect_conflicts()
            
            if not conflicts:
                logger.debug("No conflicts detected")
                return 0
            
            # Store conflicts in database
            stored_ids = await self.detector.store_conflicts(conflicts)
            logger.info(f"Stored {len(stored_ids)} conflicts in database")
            
            # Send alerts for high-severity conflicts
            await self.detector.send_alerts(conflicts)
            
            # Count alerts sent
            alerts_sent = sum(1 for c in conflicts if c.severity_score >= 6 and c.time_to_impact <= 5)
            self.stats['alerts_sent'] += alerts_sent
            
            # Send system status update
            await self._broadcast_system_status()
            
            return len(conflicts)
            
        finally:
            db_session.close()
    
    async def _broadcast_system_status(self):
        """Broadcast system status to connected clients"""
        try:
            status_data = {
                'conflict_detection': {
                    'status': 'active',
                    'last_run': self.stats['last_run_time'].isoformat() if self.stats['last_run_time'] else None,
                    'runs_completed': self.stats['runs_completed'],
                    'total_conflicts': self.stats['total_conflicts_detected'],
                    'alerts_sent': self.stats['alerts_sent'],
                    'average_detection_time': self.stats['average_detection_time'],
                    'consecutive_failures': self.consecutive_failures
                },
                'detector_metrics': self.detector.get_metrics() if self.detector else {},
                'uptime_seconds': (datetime.utcnow() - self.stats['uptime_start']).total_seconds(),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            await connection_manager.broadcast_system_status(status_data)
            
        except Exception as e:
            logger.error(f"Error broadcasting system status: {e}")
    
    def _update_stats(self, detection_time: float, conflicts_detected: int, success: bool):
        """Update performance statistics"""
        if success:
            self.stats['runs_completed'] += 1
            self.stats['total_conflicts_detected'] += conflicts_detected
            
            # Update average detection time
            total_runs = self.stats['runs_completed']
            current_avg = self.stats['average_detection_time']
            self.stats['average_detection_time'] = (
                (current_avg * (total_runs - 1) + detection_time) / total_runs
            )
        else:
            self.stats['runs_failed'] += 1
        
        self.stats['last_run_time'] = datetime.utcnow()
    
    async def run_manual_detection(self) -> Dict[str, Any]:
        """Run conflict detection manually (for testing/debugging)"""
        logger.info("Running manual conflict detection...")
        
        start_time = datetime.utcnow()
        
        # Get database session
        db_session = next(get_db())
        
        try:
            # Initialize detector
            detector = ConflictDetector(db_session, self.redis_client)
            
            # Run detection
            conflicts = await detector.detect_conflicts()
            
            # Store conflicts
            stored_ids = await detector.store_conflicts(conflicts)
            
            # Send alerts
            await detector.send_alerts(conflicts)
            
            detection_time = (datetime.utcnow() - start_time).total_seconds()
            
            result = {
                'success': True,
                'conflicts_detected': len(conflicts),
                'conflicts_stored': len(stored_ids),
                'detection_time_seconds': detection_time,
                'conflicts': [
                    {
                        'type': c.conflict_type.value,
                        'severity': c.severity_score,
                        'trains_involved': c.trains_involved,
                        'sections_involved': c.sections_involved,
                        'time_to_impact': c.time_to_impact,
                        'description': c.description,
                        'resolution_suggestions': c.resolution_suggestions
                    }
                    for c in conflicts
                ],
                'timestamp': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Manual detection completed: {len(conflicts)} conflicts found in {detection_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"Error in manual detection: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
        finally:
            db_session.close()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status and statistics"""
        uptime = (datetime.utcnow() - self.stats['uptime_start']).total_seconds()
        
        return {
            'is_running': self.is_running,
            'detection_interval_seconds': self.detection_interval,
            'uptime_seconds': uptime,
            'consecutive_failures': self.consecutive_failures,
            'max_consecutive_failures': self.max_consecutive_failures,
            'stats': {
                **self.stats,
                'last_run_time': self.stats['last_run_time'].isoformat() if self.stats['last_run_time'] else None,
                'uptime_start': self.stats['uptime_start'].isoformat()
            },
            'detector_available': self.detector is not None,
            'detector_metrics': self.detector.get_metrics() if self.detector else None
        }
    
    async def update_detection_interval(self, new_interval: int):
        """Update the detection interval (in seconds)"""
        if new_interval < 10:
            raise ValueError("Detection interval must be at least 10 seconds")
        if new_interval > 300:
            raise ValueError("Detection interval must not exceed 300 seconds")
        
        old_interval = self.detection_interval
        self.detection_interval = new_interval
        
        logger.info(f"Detection interval updated from {old_interval}s to {new_interval}s")
    
    async def force_cache_update(self):
        """Force update of detector cache"""
        if self.detector:
            await self.detector._update_cache()
            logger.info("Forced detector cache update")
        else:
            logger.warning("Detector not initialized, cannot update cache")


# Global scheduler instance
conflict_scheduler = ConflictDetectionScheduler()


async def start_conflict_detection(redis_client: Optional[RedisClient] = None):
    """Start the global conflict detection scheduler"""
    global conflict_scheduler
    
    if redis_client:
        conflict_scheduler.redis_client = redis_client
    
    await conflict_scheduler.start()


async def stop_conflict_detection():
    """Stop the global conflict detection scheduler"""
    global conflict_scheduler
    await conflict_scheduler.stop()


def get_conflict_detection_status() -> Dict[str, Any]:
    """Get current conflict detection status"""
    global conflict_scheduler
    return conflict_scheduler.get_status()


async def run_manual_conflict_detection() -> Dict[str, Any]:
    """Run conflict detection manually"""
    global conflict_scheduler
    return await conflict_scheduler.run_manual_detection()