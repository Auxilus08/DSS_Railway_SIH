"""
Railway Repository AI Adapter
Integrates the railway optimization AI model with the existing repository system
"""

import logging
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import asyncio

# Import the AI optimization module
from railway_optimization import (
    Train as AITrain, TrainType as AITrainType, RailwaySection as AISection,
    Conflict as AIConflict, OptimizationEngine, Solution as AISolution,
    Action as AIAction, ActionType as AIActionType
)

# Configure logging
logger = logging.getLogger(__name__)


class IntegrationConfig:
    """Configuration for AI model integration"""
    
    # Data mapping configurations
    CARGO_VALUE_PER_TON = 500.0  # USD per ton for cargo value estimation
    DEFAULT_PASSENGER_COUNT = 150  # Default for local trains
    MAX_OPTIMIZATION_TIMEOUT = 15.0  # Maximum AI optimization time
    
    # Severity mapping
    SEVERITY_MAPPING = {
        'low': 0.25,
        'medium': 0.5,
        'high': 0.75,
        'critical': 1.0
    }
    
    # Train type mapping
    TRAIN_TYPE_MAPPING = {
        'express': AITrainType.EXPRESS,
        'local': AITrainType.PASSENGER,  # Map local to PASSENGER
        'freight': AITrainType.FREIGHT,
        'maintenance': AITrainType.MAINTENANCE
    }
    
    # Reverse mapping for responses
    TRAIN_TYPE_REVERSE = {v: k for k, v in TRAIN_TYPE_MAPPING.items()}
    
    # Default section capacity based on type
    DEFAULT_CAPACITIES = {
        'main_line': 3,
        'branch_line': 2,
        'station': 4,
        'junction': 2,
        'depot': 5
    }


@dataclass
class RepositoryTrain:
    """Repository train data structure"""
    id: str
    type: str  # express, local, freight, maintenance
    origin: str
    destination: str
    departure_time: str  # ISO format
    arrival_time: str  # ISO format
    status: str
    current_section: Optional[str] = None
    passenger_count: Optional[int] = None
    weight_tons: Optional[float] = None
    priority: Optional[int] = None


@dataclass
class RepositorySection:
    """Repository section data structure"""
    id: str
    name: str
    type: str  # main_line, branch_line, station, junction, depot
    capacity: Optional[int] = None
    current_trains: Optional[List[str]] = None
    maintenance_window: Optional[Dict[str, str]] = None
    alternative_routes: Optional[List[str]] = None


@dataclass
class RepositoryConflict:
    """Repository conflict data structure"""
    id: str
    severity: str  # low, medium, high, critical
    description: str
    affected_trains: List[str]
    affected_sections: List[str]
    detected_at: str  # ISO format
    status: str
    estimated_delay_minutes: Optional[int] = None


@dataclass
class OptimizationResult:
    """Result of AI optimization"""
    conflict_id: str
    solutions: List[Dict[str, Any]]
    best_solution_id: str
    optimization_time: float
    ai_confidence: float
    recommendations: List[str]
    fallback_used: bool = False


class DataMapper:
    """Handles data transformation between repository and AI model formats"""
    
    @staticmethod
    def map_train_to_ai(repo_train: RepositoryTrain, current_section: str = None) -> AITrain:
        """Convert repository train to AI train format"""
        try:
            # Map train type
            ai_train_type = IntegrationConfig.TRAIN_TYPE_MAPPING.get(
                repo_train.type.lower(), 
                AITrainType.PASSENGER
            )
            
            # Parse departure time
            try:
                scheduled_time = datetime.fromisoformat(repo_train.departure_time.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                scheduled_time = datetime.now() + timedelta(hours=1)
                logger.warning(f"Invalid departure time for train {repo_train.id}, using default")
            
            # Determine passenger count
            if repo_train.passenger_count is not None:
                passenger_count = repo_train.passenger_count
            elif ai_train_type == AITrainType.PASSENGER:
                passenger_count = IntegrationConfig.DEFAULT_PASSENGER_COUNT
            else:
                passenger_count = 0
            
            # Calculate cargo value from weight
            cargo_value = 0.0
            if repo_train.weight_tons and ai_train_type == AITrainType.FREIGHT:
                cargo_value = repo_train.weight_tons * IntegrationConfig.CARGO_VALUE_PER_TON
            
            # Use provided current section or derive from train data
            section = current_section or repo_train.current_section or "UNKNOWN_SECTION"
            
            ai_train = AITrain(
                id=repo_train.id,
                type=ai_train_type,
                current_section=section,
                destination=repo_train.destination,
                scheduled_time=scheduled_time,
                passenger_count=passenger_count,
                cargo_value=cargo_value
            )
            
            # Override priority if specified in repository data
            if repo_train.priority is not None:
                ai_train.priority_score = repo_train.priority
            
            return ai_train
            
        except Exception as e:
            logger.error(f"Failed to map train {repo_train.id}: {e}")
            raise ValueError(f"Train mapping failed for {repo_train.id}: {e}")
    
    @staticmethod
    def map_section_to_ai(repo_section: RepositorySection) -> AISection:
        """Convert repository section to AI section format"""
        try:
            # Determine capacity
            capacity = repo_section.capacity
            if capacity is None:
                capacity = IntegrationConfig.DEFAULT_CAPACITIES.get(
                    repo_section.type.lower(), 2
                )
            
            # Current occupancy
            current_occupancy = len(repo_section.current_trains) if repo_section.current_trains else 0
            
            # Parse maintenance windows
            maintenance_windows = []
            if repo_section.maintenance_window:
                try:
                    start_time = datetime.fromisoformat(
                        repo_section.maintenance_window.get('start', '').replace('Z', '+00:00')
                    )
                    end_time = datetime.fromisoformat(
                        repo_section.maintenance_window.get('end', '').replace('Z', '+00:00')
                    )
                    maintenance_windows.append((start_time, end_time))
                except (ValueError, AttributeError):
                    logger.warning(f"Invalid maintenance window for section {repo_section.id}")
            
            # Alternative routes
            alt_routes = repo_section.alternative_routes or []
            
            return AISection(
                id=repo_section.id,
                capacity=capacity,
                current_occupancy=current_occupancy,
                maintenance_windows=maintenance_windows,
                alternative_routes=alt_routes
            )
            
        except Exception as e:
            logger.error(f"Failed to map section {repo_section.id}: {e}")
            raise ValueError(f"Section mapping failed for {repo_section.id}: {e}")
    
    @staticmethod
    def map_conflict_to_ai(
        repo_conflict: RepositoryConflict,
        trains: List[AITrain],
        sections: List[AISection]
    ) -> AIConflict:
        """Convert repository conflict to AI conflict format"""
        try:
            # Map severity
            severity = IntegrationConfig.SEVERITY_MAPPING.get(
                repo_conflict.severity.lower(), 0.5
            )
            
            # Parse conflict time
            try:
                conflict_time = datetime.fromisoformat(repo_conflict.detected_at.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                conflict_time = datetime.now()
                logger.warning(f"Invalid conflict time for {repo_conflict.id}, using current time")
            
            # Filter trains and sections involved in conflict
            involved_trains = [t for t in trains if t.id in repo_conflict.affected_trains]
            involved_sections = [s for s in sections if s.id in repo_conflict.affected_sections]
            
            return AIConflict(
                id=repo_conflict.id,
                trains=involved_trains,
                sections=involved_sections,
                conflict_time=conflict_time,
                severity=severity,
                constraints={'description': repo_conflict.description}
            )
            
        except Exception as e:
            logger.error(f"Failed to map conflict {repo_conflict.id}: {e}")
            raise ValueError(f"Conflict mapping failed for {repo_conflict.id}: {e}")
    
    @staticmethod
    def map_ai_solution_to_result(
        ai_solutions: List[AISolution], 
        conflict_id: str,
        optimization_time: float
    ) -> OptimizationResult:
        """Convert AI solutions to repository result format"""
        try:
            solutions_data = []
            recommendations = []
            
            for solution in ai_solutions:
                # Convert actions to repository format
                actions = []
                for action in solution.actions:
                    action_data = {
                        'type': action.type.value,
                        'train_id': action.train_id,
                        'parameters': action.parameters,
                        'cost': action.estimated_cost
                    }
                    actions.append(action_data)
                    
                    # Generate human-readable recommendations
                    if action.type == AIActionType.DELAY_TRAIN:
                        delay_min = action.parameters.get('minutes', 0)
                        recommendations.append(
                            f"Delay train {action.train_id} by {delay_min} minutes"
                        )
                    elif action.type == AIActionType.REROUTE_TRAIN:
                        alt_route = action.parameters.get('alternative_path', 'alternative route')
                        recommendations.append(
                            f"Reroute train {action.train_id} via {alt_route}"
                        )
                    elif action.type == AIActionType.PRIORITY_OVERRIDE:
                        new_priority = action.parameters.get('new_priority', 'adjusted')
                        recommendations.append(
                            f"Adjust priority for train {action.train_id} to {new_priority}"
                        )
                
                solution_data = {
                    'id': solution.id,
                    'solver_method': solution.solver_method,
                    'total_score': round(solution.total_score, 2),
                    'safety_score': round(solution.safety_score, 1),
                    'efficiency_score': round(solution.efficiency_score, 1),
                    'passenger_impact_score': round(solution.passenger_impact_score, 1),
                    'computation_time': round(solution.computation_time, 4),
                    'actions': actions,
                    'estimated_total_cost': sum(a['cost'] for a in actions)
                }
                solutions_data.append(solution_data)
            
            # Calculate AI confidence based on solution scores and diversity
            if solutions_data:
                best_score = max(s['total_score'] for s in solutions_data)
                score_variance = max(s['total_score'] for s in solutions_data) - min(s['total_score'] for s in solutions_data)
                ai_confidence = min(1.0, best_score / 100.0)  # Normalize to 0-1
                if score_variance < 5.0:  # Low variance indicates consistent solutions
                    ai_confidence = min(1.0, ai_confidence + 0.1)
            else:
                ai_confidence = 0.0
            
            return OptimizationResult(
                conflict_id=conflict_id,
                solutions=solutions_data,
                best_solution_id=solutions_data[0]['id'] if solutions_data else None,
                optimization_time=optimization_time,
                ai_confidence=ai_confidence,
                recommendations=list(set(recommendations)),  # Remove duplicates
                fallback_used=False
            )
            
        except Exception as e:
            logger.error(f"Failed to map AI solutions: {e}")
            raise ValueError(f"Solution mapping failed: {e}")


class RailwayAIAdapter:
    """Main adapter interface for railway AI optimization"""
    
    def __init__(self, enable_ai: bool = True, train_rl_agent: bool = False):
        self.enable_ai = enable_ai
        self.optimization_engine = OptimizationEngine() if enable_ai else None
        self.data_mapper = DataMapper()
        self.health_status = {'ai_available': enable_ai, 'last_optimization': None}
        
        if enable_ai and train_rl_agent:
            self._train_rl_agent()
    
    def _train_rl_agent(self):
        """Train the RL agent on startup if requested"""
        try:
            logger.info("Training RL agent on startup...")
            if self.optimization_engine:
                self.optimization_engine.rl_solver.train([], episodes=300)
                logger.info("RL agent training completed")
        except Exception as e:
            logger.error(f"RL agent training failed: {e}")
    
    async def optimize_conflict(
        self,
        conflict: RepositoryConflict,
        trains: List[RepositoryTrain],
        sections: List[RepositorySection],
        timeout: float = None
    ) -> OptimizationResult:
        """
        Main optimization method - converts repository data to AI format and optimizes
        
        Args:
            conflict: Repository conflict data
            trains: List of involved trains
            sections: List of involved sections
            timeout: Maximum optimization time
            
        Returns:
            OptimizationResult with solutions and recommendations
        """
        if not self.enable_ai or not self.optimization_engine:
            return self._generate_fallback_result(conflict)
        
        optimization_start = datetime.now()
        timeout = timeout or IntegrationConfig.MAX_OPTIMIZATION_TIMEOUT
        
        try:
            # Convert repository data to AI format
            ai_trains = []
            for train in trains:
                try:
                    ai_train = self.data_mapper.map_train_to_ai(train)
                    ai_trains.append(ai_train)
                except ValueError as e:
                    logger.warning(f"Skipping train {train.id}: {e}")
            
            ai_sections = []
            for section in sections:
                try:
                    ai_section = self.data_mapper.map_section_to_ai(section)
                    ai_sections.append(ai_section)
                except ValueError as e:
                    logger.warning(f"Skipping section {section.id}: {e}")
            
            # Create AI conflict
            ai_conflict = self.data_mapper.map_conflict_to_ai(conflict, ai_trains, ai_sections)
            
            # Validate AI conflict
            if not ai_conflict.validate():
                logger.error(f"Invalid AI conflict for {conflict.id}")
                return self._generate_fallback_result(conflict)
            
            # Run AI optimization
            logger.info(f"Running AI optimization for conflict {conflict.id}")
            ai_solutions = await asyncio.get_event_loop().run_in_executor(
                None,
                self.optimization_engine.solve_conflict,
                ai_conflict,
                timeout
            )
            
            optimization_time = (datetime.now() - optimization_start).total_seconds()
            
            # Update health status
            self.health_status['last_optimization'] = datetime.now().isoformat()
            
            if not ai_solutions:
                logger.warning(f"No AI solutions found for conflict {conflict.id}")
                return self._generate_fallback_result(conflict, optimization_time)
            
            # Convert AI solutions back to repository format
            result = self.data_mapper.map_ai_solution_to_result(
                ai_solutions, conflict.id, optimization_time
            )
            
            logger.info(f"AI optimization completed for {conflict.id}: "
                       f"{len(result.solutions)} solutions, "
                       f"confidence: {result.ai_confidence:.2f}")
            
            return result
            
        except Exception as e:
            logger.error(f"AI optimization failed for conflict {conflict.id}: {e}")
            optimization_time = (datetime.now() - optimization_start).total_seconds()
            return self._generate_fallback_result(conflict, optimization_time)
    
    def _generate_fallback_result(
        self, 
        conflict: RepositoryConflict, 
        optimization_time: float = 0.0
    ) -> OptimizationResult:
        """Generate fallback result when AI optimization fails or is disabled"""
        
        # Simple rule-based fallback recommendations
        recommendations = []
        
        if conflict.severity in ['high', 'critical']:
            recommendations.append("High priority conflict - consider manual intervention")
            recommendations.append("Review train schedules for immediate adjustments")
        
        if conflict.estimated_delay_minutes and conflict.estimated_delay_minutes > 30:
            recommendations.append("Significant delays expected - notify passengers")
            recommendations.append("Consider alternative routing for affected trains")
        
        # Default fallback action
        if conflict.affected_trains:
            first_train = conflict.affected_trains[0]
            recommendations.append(f"Consider delaying train {first_train} by 15 minutes")
        
        fallback_solution = {
            'id': f'fallback_{conflict.id}',
            'solver_method': 'fallback',
            'total_score': 60.0,  # Moderate fallback score
            'safety_score': 90.0,  # Prioritize safety
            'efficiency_score': 40.0,
            'passenger_impact_score': 50.0,
            'computation_time': optimization_time,
            'actions': [],
            'estimated_total_cost': 0.0
        }
        
        return OptimizationResult(
            conflict_id=conflict.id,
            solutions=[fallback_solution],
            best_solution_id=fallback_solution['id'],
            optimization_time=optimization_time,
            ai_confidence=0.3,  # Low confidence for fallback
            recommendations=recommendations,
            fallback_used=True
        )
    
    async def train_rl_agent(self, episodes: int = 500) -> Dict[str, Any]:
        """Train or retrain the RL agent"""
        if not self.enable_ai or not self.optimization_engine:
            return {'status': 'disabled', 'message': 'AI optimization disabled'}
        
        try:
            training_start = datetime.now()
            
            # Train in background thread to avoid blocking
            await asyncio.get_event_loop().run_in_executor(
                None,
                self.optimization_engine.rl_solver.train,
                [],  # Use synthetic data
                episodes
            )
            
            training_time = (datetime.now() - training_start).total_seconds()
            
            return {
                'status': 'completed',
                'episodes': episodes,
                'training_time': training_time,
                'agent_epsilon': self.optimization_engine.rl_solver.agent.epsilon,
                'memory_size': len(self.optimization_engine.rl_solver.agent.memory)
            }
            
        except Exception as e:
            logger.error(f"RL training failed: {e}")
            return {'status': 'failed', 'error': str(e)}
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health and status of the AI adapter"""
        if not self.enable_ai or not self.optimization_engine:
            return {
                'ai_enabled': False,
                'status': 'disabled',
                'message': 'AI optimization is disabled'
            }
        
        try:
            rl_status = {
                'trained': self.optimization_engine.rl_solver.trained,
                'episodes': self.optimization_engine.rl_solver.training_episodes,
                'epsilon': self.optimization_engine.rl_solver.agent.epsilon if self.optimization_engine.rl_solver.trained else None
            }
            
            return {
                'ai_enabled': True,
                'status': 'healthy',
                'rule_based_solver': True,
                'constraint_solver': self.optimization_engine.constraint_solver.available,
                'reinforcement_learning': rl_status,
                'last_optimization': self.health_status.get('last_optimization'),
                'integration_version': '1.0.0'
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'ai_enabled': True,
                'status': 'unhealthy',
                'error': str(e)
            }
    
    def get_optimization_capabilities(self) -> Dict[str, Any]:
        """Get information about available optimization capabilities"""
        if not self.enable_ai:
            return {'capabilities': 'fallback_only'}
        
        capabilities = {
            'solvers': ['rule_based'],
            'max_trains_per_conflict': 10,
            'max_sections_per_conflict': 5,
            'supported_train_types': list(IntegrationConfig.TRAIN_TYPE_MAPPING.keys()),
            'supported_severity_levels': list(IntegrationConfig.SEVERITY_MAPPING.keys()),
            'max_optimization_time': IntegrationConfig.MAX_OPTIMIZATION_TIMEOUT
        }
        
        if self.optimization_engine:
            if self.optimization_engine.constraint_solver.available:
                capabilities['solvers'].append('constraint_programming')
            
            if self.optimization_engine.rl_solver.trained:
                capabilities['solvers'].append('reinforcement_learning')
                capabilities['rl_episodes'] = self.optimization_engine.rl_solver.training_episodes
        
        return capabilities


# Integration test utilities
class IntegrationTester:
    """Test utilities for validating the integration"""
    
    @staticmethod
    def create_test_data():
        """Create test data for integration validation"""
        
        # Test trains
        trains = [
            RepositoryTrain(
                id="EXP_001",
                type="express",
                origin="Station_A",
                destination="Station_B",
                departure_time="2024-01-01T10:00:00Z",
                arrival_time="2024-01-01T12:00:00Z",
                status="scheduled",
                current_section="SEC_001",
                passenger_count=300,
                priority=100
            ),
            RepositoryTrain(
                id="LOCAL_002",
                type="local",
                origin="Station_B",
                destination="Station_C",
                departure_time="2024-01-01T10:05:00Z",
                arrival_time="2024-01-01T11:30:00Z",
                status="scheduled",
                current_section="SEC_001",
                passenger_count=150
            ),
            RepositoryTrain(
                id="FREIGHT_003",
                type="freight",
                origin="Depot_X",
                destination="Port_Y",
                departure_time="2024-01-01T10:10:00Z",
                arrival_time="2024-01-01T14:00:00Z",
                status="scheduled",
                current_section="SEC_001",
                weight_tons=500.0
            )
        ]
        
        # Test sections
        sections = [
            RepositorySection(
                id="SEC_001",
                name="Main Junction",
                type="junction",
                capacity=2,
                current_trains=["EXP_001", "LOCAL_002", "FREIGHT_003"],
                alternative_routes=["SEC_002", "SEC_003"]
            )
        ]
        
        # Test conflict
        conflict = RepositoryConflict(
            id="CONFLICT_TEST_001",
            severity="high",
            description="Multiple trains competing for limited track capacity",
            affected_trains=["EXP_001", "LOCAL_002", "FREIGHT_003"],
            affected_sections=["SEC_001"],
            detected_at="2024-01-01T09:55:00Z",
            status="active",
            estimated_delay_minutes=20
        )
        
        return trains, sections, conflict
    
    @staticmethod
    async def run_integration_test():
        """Run a complete integration test"""
        logger.info("Starting integration test...")
        
        # Create test data
        trains, sections, conflict = IntegrationTester.create_test_data()
        
        # Initialize adapter
        adapter = RailwayAIAdapter(enable_ai=True, train_rl_agent=True)
        
        try:
            # Test optimization
            result = await adapter.optimize_conflict(conflict, trains, sections)
            
            logger.info(f"Integration test results:")
            logger.info(f"  Solutions generated: {len(result.solutions)}")
            logger.info(f"  Best solution: {result.best_solution_id}")
            logger.info(f"  AI confidence: {result.ai_confidence:.2f}")
            logger.info(f"  Optimization time: {result.optimization_time:.3f}s")
            logger.info(f"  Fallback used: {result.fallback_used}")
            logger.info(f"  Recommendations: {len(result.recommendations)}")
            
            # Test health check
            health = adapter.get_health_status()
            logger.info(f"  Health status: {health['status']}")
            
            # Test capabilities
            capabilities = adapter.get_optimization_capabilities()
            logger.info(f"  Available solvers: {capabilities['solvers']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Integration test failed: {e}")
            return False


# Usage example
if __name__ == "__main__":
    import asyncio
    
    # Configure logging for testing
    logging.basicConfig(level=logging.INFO)
    
    # Run integration test
    async def main():
        success = await IntegrationTester.run_integration_test()
        print(f"Integration test {'PASSED' if success else 'FAILED'}")
    
    asyncio.run(main())
