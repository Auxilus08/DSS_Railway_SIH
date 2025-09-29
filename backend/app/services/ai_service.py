"""
AI Optimization Service Layer

This service integrates the railway optimization AI model with the database,
providing methods to optimize conflicts, store AI results, and manage the
AI optimization lifecycle.

Key Features:
- Automatic conflict optimization using multiple AI solvers
- Database integration for storing AI results and recommendations
- Performance tracking and confidence scoring
- Background processing and result caching
- Integration with existing railway traffic management workflows

Dependencies:
- railway_optimization.py: Core AI optimization engine
- railway_adapter.py: Data mapping layer
- models.py: Database models for conflicts and decisions
- ai_config.py: AI configuration management
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import json
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models import Conflict, Decision, Train, Section, Controller
from app.railway_optimization import OptimizationEngine
from app.railway_adapter import RailwayAIAdapter, DataMapper
from app.ai_config import AIConfig


class AIOptimizationService:
    """
    Service for AI-powered railway conflict optimization
    
    This service provides the main interface between the railway traffic management
    system and the AI optimization engine. It handles:
    - Conflict analysis and optimization
    - Database storage of AI results
    - Performance tracking and metrics
    - Integration with existing workflows
    """
    
    def __init__(self, db_session: Session, config: Optional[AIConfig] = None):
        """
        Initialize the AI optimization service
        
        Args:
            db_session: SQLAlchemy database session
            config: AI configuration (uses default if not provided)
        """
        self.db = db_session
        self.config = config or AIConfig()
        
        # Initialize AI components if enabled
        if self.config.ENABLE_AI_OPTIMIZATION:
            self.optimization_engine = OptimizationEngine()
            self.adapter = RailwayAIAdapter(enable_ai=True)
            self.data_mapper = DataMapper()
        else:
            self.optimization_engine = None
            self.adapter = None
            self.data_mapper = None
    
    def is_ai_enabled(self) -> bool:
        """Check if AI optimization is enabled"""
        return self.config.ENABLE_AI_OPTIMIZATION and self.optimization_engine is not None
    
    async def optimize_conflict(
        self, 
        conflict_id: int, 
        solver_preference: Optional[str] = None,
        force_reanalysis: bool = False
    ) -> Dict[str, Any]:
        """
        Optimize a specific conflict using AI
        
        Args:
            conflict_id: ID of the conflict to optimize
            solver_preference: Preferred solver ('rule_based', 'constraint_programming', 'reinforcement_learning')
            force_reanalysis: Force re-analysis even if already analyzed
            
        Returns:
            Dictionary containing optimization results and metadata
        """
        if not self.is_ai_enabled():
            raise RuntimeError("AI optimization is not enabled")
        
        # Get the conflict from database
        conflict = self.db.query(Conflict).filter(Conflict.id == conflict_id).first()
        if not conflict:
            raise ValueError(f"Conflict with ID {conflict_id} not found")
        
        # Check if already analyzed and not forcing reanalysis
        if conflict.ai_analyzed and not force_reanalysis:
            return {
                'status': 'already_analyzed',
                'conflict_id': conflict_id,
                'ai_confidence': float(conflict.ai_confidence) if conflict.ai_confidence else None,
                'ai_recommendations': conflict.ai_recommendations,
                'analysis_time': conflict.ai_analysis_time.isoformat() if conflict.ai_analysis_time else None
            }
        
        try:
            # Get related data for the conflict
            trains = self._get_conflict_trains(conflict)
            sections = self._get_conflict_sections(conflict)
            
            # Convert to AI format using adapter
            ai_conflict = self.adapter.convert_conflict_to_ai(conflict, trains, sections)
            
            # Perform AI optimization
            optimization_result = await self._run_optimization(
                ai_conflict, 
                solver_preference
            )
            
            # Generate unique solution ID
            solution_id = f"ai_sol_{uuid.uuid4().hex[:12]}"
            
            # Update conflict with AI results
            await self._store_conflict_analysis(
                conflict, 
                optimization_result,
                solution_id
            )
            
            # Create AI-generated decisions if recommendations provided
            decisions_created = await self._create_ai_decisions(
                conflict,
                optimization_result,
                solution_id
            )
            
            # Commit changes
            self.db.commit()
            
            return {
                'status': 'success',
                'conflict_id': conflict_id,
                'solution_id': solution_id,
                'solver_used': optimization_result.get('solver_method'),
                'ai_confidence': optimization_result.get('confidence'),
                'optimization_score': optimization_result.get('score'),
                'recommendations': optimization_result.get('recommendations'),
                'decisions_created': len(decisions_created),
                'analysis_time': datetime.utcnow().isoformat(),
                'performance_metrics': optimization_result.get('performance_metrics', {})
            }
            
        except Exception as e:
            self.db.rollback()
            # Log error but don't expose internal details
            error_msg = f"AI optimization failed for conflict {conflict_id}"
            return {
                'status': 'error',
                'conflict_id': conflict_id,
                'error': error_msg,
                'error_type': type(e).__name__
            }
    
    async def batch_optimize_conflicts(
        self,
        conflict_ids: List[int],
        solver_preference: Optional[str] = None,
        max_concurrent: int = 3
    ) -> Dict[str, Any]:
        """
        Optimize multiple conflicts in batch
        
        Args:
            conflict_ids: List of conflict IDs to optimize
            solver_preference: Preferred solver method
            max_concurrent: Maximum concurrent optimizations
            
        Returns:
            Summary of batch optimization results
        """
        if not self.is_ai_enabled():
            raise RuntimeError("AI optimization is not enabled")
        
        results = []
        successful = 0
        failed = 0
        
        # Process conflicts (simplified sequential for now)
        for conflict_id in conflict_ids:
            try:
                result = await self.optimize_conflict(conflict_id, solver_preference)
                results.append(result)
                if result['status'] == 'success':
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                results.append({
                    'status': 'error',
                    'conflict_id': conflict_id,
                    'error': str(e)
                })
                failed += 1
        
        return {
            'batch_status': 'completed',
            'total_conflicts': len(conflict_ids),
            'successful': successful,
            'failed': failed,
            'results': results
        }
    
    def get_ai_performance_metrics(
        self, 
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get AI performance metrics for the specified time period
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary containing performance metrics
        """
        from datetime import timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Query AI-analyzed conflicts
        ai_conflicts = self.db.query(Conflict).filter(
            and_(
                Conflict.ai_analyzed == True,
                Conflict.ai_analysis_time >= cutoff_time
            )
        ).all()
        
        # Query AI-generated decisions
        ai_decisions = self.db.query(Decision).filter(
            and_(
                Decision.ai_generated == True,
                Decision.created_at >= cutoff_time
            )
        ).all()
        
        # Calculate metrics
        total_conflicts = len(ai_conflicts)
        avg_confidence = sum(float(c.ai_confidence or 0) for c in ai_conflicts) / max(total_conflicts, 1)
        
        solver_usage = {}
        for decision in ai_decisions:
            solver = decision.ai_solver_method or 'unknown'
            solver_usage[solver] = solver_usage.get(solver, 0) + 1
        
        return {
            'time_period_hours': hours,
            'conflicts_analyzed': total_conflicts,
            'decisions_generated': len(ai_decisions),
            'average_confidence': round(avg_confidence, 4),
            'solver_usage': solver_usage,
            'ai_enabled': self.is_ai_enabled(),
            'generated_at': datetime.utcnow().isoformat()
        }
    
    async def _run_optimization(
        self,
        ai_conflict: Dict[str, Any],
        solver_preference: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run the AI optimization engine on a conflict"""
        
        # Determine which solver to use
        if solver_preference and solver_preference in ['rule_based', 'constraint_programming', 'reinforcement_learning']:
            solver_method = solver_preference
        else:
            # Use configuration default or auto-select based on conflict complexity
            solver_method = self.config.settings.get('default_solver', 'rule_based')
        
        # Run optimization
        result = self.optimization_engine.optimize_conflict(
            conflict_data=ai_conflict,
            solver_method=solver_method
        )
        
        return result
    
    async def _store_conflict_analysis(
        self,
        conflict: Conflict,
        optimization_result: Dict[str, Any],
        solution_id: str
    ) -> None:
        """Store AI analysis results in the conflict record"""
        
        conflict.ai_analyzed = True
        conflict.ai_confidence = optimization_result.get('confidence')
        conflict.ai_solution_id = solution_id
        conflict.ai_recommendations = optimization_result.get('recommendations')
        conflict.ai_analysis_time = datetime.utcnow()
    
    async def _create_ai_decisions(
        self,
        conflict: Conflict,
        optimization_result: Dict[str, Any],
        solution_id: str
    ) -> List[Decision]:
        """Create AI-generated decisions based on optimization results"""
        
        decisions = []
        recommendations = optimization_result.get('recommendations', [])
        
        for i, recommendation in enumerate(recommendations[:5]):  # Limit to 5 decisions
            decision = Decision(
                controller_id=1,  # System AI controller (you may need to create this)
                conflict_id=conflict.id,
                action_taken=recommendation.get('action', 'manual_override'),
                rationale=f"AI-generated solution (ID: {solution_id}): {recommendation.get('description', 'AI optimization recommendation')}",
                parameters=recommendation.get('parameters', {}),
                ai_generated=True,
                ai_solver_method=optimization_result.get('solver_method'),
                ai_score=recommendation.get('score'),
                ai_confidence=optimization_result.get('confidence')
            )
            
            self.db.add(decision)
            decisions.append(decision)
        
        return decisions
    
    def _get_conflict_trains(self, conflict: Conflict) -> List[Train]:
        """Get trains involved in the conflict"""
        if not conflict.trains_involved:
            return []
        
        return self.db.query(Train).filter(
            Train.id.in_(conflict.trains_involved)
        ).all()
    
    def _get_conflict_sections(self, conflict: Conflict) -> List[Section]:
        """Get sections involved in the conflict"""
        if not conflict.sections_involved:
            return []
        
        return self.db.query(Section).filter(
            Section.id.in_(conflict.sections_involved)
        ).all()


class AIMetricsService:
    """Service for AI performance monitoring and metrics collection"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
    
    def get_solver_performance_comparison(self, days: int = 7) -> Dict[str, Any]:
        """Compare performance across different AI solvers"""
        from datetime import timedelta
        
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        # Query AI decisions by solver method
        decisions = self.db.query(Decision).filter(
            and_(
                Decision.ai_generated == True,
                Decision.created_at >= cutoff_time,
                Decision.ai_solver_method.isnot(None)
            )
        ).all()
        
        solver_stats = {}
        for decision in decisions:
            solver = decision.ai_solver_method
            if solver not in solver_stats:
                solver_stats[solver] = {
                    'count': 0,
                    'total_score': 0,
                    'total_confidence': 0,
                    'executed_count': 0
                }
            
            stats = solver_stats[solver]
            stats['count'] += 1
            stats['total_score'] += float(decision.ai_score or 0)
            stats['total_confidence'] += float(decision.ai_confidence or 0)
            if decision.executed:
                stats['executed_count'] += 1
        
        # Calculate averages
        for solver, stats in solver_stats.items():
            if stats['count'] > 0:
                stats['avg_score'] = round(stats['total_score'] / stats['count'], 4)
                stats['avg_confidence'] = round(stats['total_confidence'] / stats['count'], 4)
                stats['execution_rate'] = round(stats['executed_count'] / stats['count'], 4)
        
        return {
            'period_days': days,
            'solver_comparison': solver_stats,
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def get_ai_accuracy_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Calculate AI accuracy metrics based on resolved conflicts"""
        # This would compare AI recommendations vs actual outcomes
        # Implementation depends on how you track resolution success
        return {
            'period_days': days,
            'accuracy_score': 0.85,  # Placeholder
            'note': 'Accuracy calculation requires outcome tracking implementation'
        }