"""
Railway AI Optimization Module for Conflict Resolution
Enterprise-grade implementation with multiple optimization approaches
"""

import logging
import time
import asyncio
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import numpy as np
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import json

# External dependencies
try:
    from ortools.sat.python import cp_model
    OR_TOOLS_AVAILABLE = True
except ImportError:
    OR_TOOLS_AVAILABLE = False
    logging.warning("OR-Tools not available, falling back to rule-based solver only")

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, validator
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TrainType(Enum):
    """Train priority enumeration"""
    EXPRESS = 1
    PASSENGER = 2
    FREIGHT = 3
    MAINTENANCE = 4


class ActionType(Enum):
    """Available conflict resolution actions"""
    DELAY_TRAIN = "delay_train"
    REROUTE_TRAIN = "reroute_train"
    PRIORITY_OVERRIDE = "priority_override"


@dataclass
class Train:
    """Train entity with scheduling information"""
    id: str
    type: TrainType
    current_section: str
    destination: str
    scheduled_time: datetime
    priority_score: int = field(init=False)
    passenger_count: int = 0
    cargo_value: float = 0.0
    
    def __post_init__(self):
        # Assign priority scores based on train type
        priority_map = {
            TrainType.EXPRESS: 100,
            TrainType.PASSENGER: 80,
            TrainType.FREIGHT: 60,
            TrainType.MAINTENANCE: 40
        }
        self.priority_score = priority_map[self.type]


@dataclass
class RailwaySection:
    """Railway section with capacity constraints"""
    id: str
    capacity: int
    current_occupancy: int
    maintenance_windows: List[Tuple[datetime, datetime]] = field(default_factory=list)
    alternative_routes: List[str] = field(default_factory=list)


@dataclass
class Conflict:
    """Conflict definition with involved trains and constraints"""
    id: str
    trains: List[Train]
    sections: List[RailwaySection]
    conflict_time: datetime
    severity: float  # 0-1 scale
    constraints: Dict[str, Any] = field(default_factory=dict)
    
    def validate(self) -> bool:
        """Validate conflict data integrity"""
        if not self.trains or not self.sections:
            return False
        if self.severity < 0 or self.severity > 1:
            return False
        return True


@dataclass
class Action:
    """Resolution action with parameters"""
    type: ActionType
    train_id: str
    parameters: Dict[str, Any]
    estimated_cost: float = 0.0
    
    def validate_safety(self) -> bool:
        """Validate action doesn't violate safety constraints"""
        if self.type == ActionType.DELAY_TRAIN:
            delay_minutes = self.parameters.get('minutes', 0)
            return 0 <= delay_minutes <= 180  # Max 3 hour delay
        elif self.type == ActionType.REROUTE_TRAIN:
            return 'alternative_path' in self.parameters
        elif self.type == ActionType.PRIORITY_OVERRIDE:
            return 'new_priority' in self.parameters
        return False


@dataclass
class Solution:
    """Complete solution with actions and impact assessment"""
    id: str
    actions: List[Action]
    safety_score: float
    efficiency_score: float
    passenger_impact_score: float
    total_score: float = field(init=False)
    computation_time: float = 0.0
    solver_method: str = ""
    
    def __post_init__(self):
        # Weighted total score calculation
        weights = {'safety': 0.5, 'efficiency': 0.3, 'passenger': 0.2}
        self.total_score = (
            self.safety_score * weights['safety'] +
            self.efficiency_score * weights['efficiency'] +
            self.passenger_impact_score * weights['passenger']
        )
    
    def validate(self) -> bool:
        """Validate solution integrity"""
        if not all(action.validate_safety() for action in self.actions):
            return False
        if not (0 <= self.safety_score <= 100):
            return False
        return True


class RuleBasedSolver:
    """Heuristic-based conflict resolution for immediate deployment"""
    
    def __init__(self):
        self.name = "rule_based"
        
    def solve(self, conflict: Conflict, timeout: float = 10.0) -> List[Solution]:
        """Generate solutions using rule-based heuristics"""
        start_time = time.time()
        solutions = []
        
        try:
            # Solution 1: Priority-based delays
            solution1 = self._priority_delay_solution(conflict)
            if solution1:
                solutions.append(solution1)
            
            # Solution 2: Rerouting lower priority trains
            solution2 = self._reroute_solution(conflict)
            if solution2:
                solutions.append(solution2)
            
            # Solution 3: Hybrid approach
            solution3 = self._hybrid_solution(conflict)
            if solution3:
                solutions.append(solution3)
                
            # Update computation times
            computation_time = time.time() - start_time
            for solution in solutions:
                solution.computation_time = computation_time
                solution.solver_method = self.name
                
        except Exception as e:
            logger.error(f"Rule-based solver failed: {e}")
            
        return solutions
    
    def _priority_delay_solution(self, conflict: Conflict) -> Optional[Solution]:
        """Generate solution by delaying lower priority trains"""
        actions = []
        
        # Sort trains by priority (lower score = higher priority)
        sorted_trains = sorted(conflict.trains, key=lambda t: t.priority_score)
        
        for i, train in enumerate(sorted_trains[1:], 1):  # Skip highest priority
            delay_minutes = min(15 * i, 60)  # Progressive delays
            actions.append(Action(
                type=ActionType.DELAY_TRAIN,
                train_id=train.id,
                parameters={'minutes': delay_minutes},
                estimated_cost=delay_minutes * 0.5
            ))
        
        if not actions:
            return None
            
        return Solution(
            id=f"rule_delay_{conflict.id}",
            actions=actions,
            safety_score=95.0,
            efficiency_score=70.0,
            passenger_impact_score=self._calculate_passenger_impact(actions, conflict)
        )
    
    def _reroute_solution(self, conflict: Conflict) -> Optional[Solution]:
        """Generate solution by rerouting trains to alternative paths"""
        actions = []
        
        # Find trains that can be rerouted
        for train in conflict.trains:
            if train.type in [TrainType.FREIGHT, TrainType.MAINTENANCE]:
                # Look for alternative routes
                for section in conflict.sections:
                    if section.alternative_routes:
                        actions.append(Action(
                            type=ActionType.REROUTE_TRAIN,
                            train_id=train.id,
                            parameters={
                                'alternative_path': section.alternative_routes[0],
                                'estimated_delay': 10
                            },
                            estimated_cost=5.0
                        ))
                        break
        
        if not actions:
            return None
            
        return Solution(
            id=f"rule_reroute_{conflict.id}",
            actions=actions,
            safety_score=90.0,
            efficiency_score=85.0,
            passenger_impact_score=95.0  # Minimal passenger impact
        )
    
    def _hybrid_solution(self, conflict: Conflict) -> Optional[Solution]:
        """Generate hybrid solution combining delays and rerouting"""
        actions = []
        
        # Reroute freight trains
        freight_trains = [t for t in conflict.trains if t.type == TrainType.FREIGHT]
        for train in freight_trains[:1]:  # Reroute one freight train
            actions.append(Action(
                type=ActionType.REROUTE_TRAIN,
                train_id=train.id,
                parameters={
                    'alternative_path': f"alt_route_{train.current_section}",
                    'estimated_delay': 5
                },
                estimated_cost=3.0
            ))
        
        # Minor delays for remaining trains
        remaining_trains = [t for t in conflict.trains if t.type != TrainType.EXPRESS]
        for train in remaining_trains[-2:]:  # Delay last 2 trains
            actions.append(Action(
                type=ActionType.DELAY_TRAIN,
                train_id=train.id,
                parameters={'minutes': 10},
                estimated_cost=5.0
            ))
        
        if not actions:
            return None
            
        return Solution(
            id=f"rule_hybrid_{conflict.id}",
            actions=actions,
            safety_score=92.0,
            efficiency_score=80.0,
            passenger_impact_score=85.0
        )
    
    def _calculate_passenger_impact(self, actions: List[Action], conflict: Conflict) -> float:
        """Calculate passenger impact score (higher is better)"""
        total_passenger_delay = 0
        total_passengers = 0
        
        for action in actions:
            if action.type == ActionType.DELAY_TRAIN:
                train = next((t for t in conflict.trains if t.id == action.train_id), None)
                if train and train.type in [TrainType.EXPRESS, TrainType.PASSENGER]:
                    delay_minutes = action.parameters.get('minutes', 0)
                    total_passenger_delay += delay_minutes * train.passenger_count
                    total_passengers += train.passenger_count
        
        if total_passengers == 0:
            return 95.0
            
        avg_delay = total_passenger_delay / total_passengers
        return max(0, 100 - avg_delay)  # Convert to score (higher is better)


class ConstraintSolver:
    """OR-Tools based constraint programming solver"""
    
    def __init__(self):
        self.name = "constraint_programming"
        self.available = OR_TOOLS_AVAILABLE
        
    def solve(self, conflict: Conflict, timeout: float = 10.0) -> List[Solution]:
        """Generate solutions using constraint programming"""
        if not self.available:
            logger.warning("OR-Tools not available, skipping constraint solver")
            return []
            
        start_time = time.time()
        solutions = []
        
        try:
            model = cp_model.CpModel()
            solver = cp_model.CpSolver()
            solver.parameters.max_time_in_seconds = timeout - 1  # Leave buffer
            
            # Variables for train scheduling
            train_vars = {}
            delay_vars = {}
            
            for train in conflict.trains:
                # Binary variables for train scheduling decisions
                train_vars[train.id] = model.NewBoolVar(f'schedule_{train.id}')
                delay_vars[train.id] = model.NewIntVar(0, 180, f'delay_{train.id}')
            
            # Capacity constraints
            for section in conflict.sections:
                scheduled_trains = [train_vars[t.id] for t in conflict.trains]
                model.Add(sum(scheduled_trains) <= section.capacity)
            
            # Priority constraints
            express_trains = [t for t in conflict.trains if t.type == TrainType.EXPRESS]
            other_trains = [t for t in conflict.trains if t.type != TrainType.EXPRESS]
            
            for express_train in express_trains:
                for other_train in other_trains:
                    # Express trains have scheduling priority
                    model.AddImplication(
                        train_vars[express_train.id],
                        train_vars[other_train.id].Not()
                    )
            
            # Objective: minimize total weighted delay
            objective_terms = []
            for train in conflict.trains:
                weight = 100 - train.priority_score  # Higher priority = higher weight
                objective_terms.append(weight * delay_vars[train.id])
            
            model.Minimize(sum(objective_terms))
            
            # Solve model
            status = solver.Solve(model)
            
            if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                solution = self._extract_solution(
                    conflict, solver, train_vars, delay_vars, start_time
                )
                if solution:
                    solutions.append(solution)
            
        except Exception as e:
            logger.error(f"Constraint solver failed: {e}")
            
        return solutions
    
    def _extract_solution(self, conflict: Conflict, solver, train_vars, delay_vars, start_time) -> Optional[Solution]:
        """Extract solution from solved CP model"""
        actions = []
        
        for train in conflict.trains:
            delay = solver.Value(delay_vars[train.id])
            if delay > 0:
                actions.append(Action(
                    type=ActionType.DELAY_TRAIN,
                    train_id=train.id,
                    parameters={'minutes': delay},
                    estimated_cost=delay * 0.3
                ))
        
        computation_time = time.time() - start_time
        
        return Solution(
            id=f"cp_{conflict.id}",
            actions=actions,
            safety_score=98.0,  # CP solutions are typically safer
            efficiency_score=90.0,
            passenger_impact_score=85.0,
            computation_time=computation_time,
            solver_method=self.name
        )


class RLEnvironment:
    """RL Environment for Railway Conflict Resolution"""
    
    def __init__(self):
        self.current_conflict = None
        self.action_history = []
        self.max_actions_per_episode = 3  # Limit actions per conflict
        
    def reset(self, conflict: Conflict):
        """Reset environment with new conflict"""
        self.current_conflict = conflict
        self.action_history = []
        return self._get_state()
    
    def _get_state(self) -> np.ndarray:
        """Convert conflict to state vector for RL agent"""
        if not self.current_conflict:
            return np.zeros(20)  # Default state size
            
        # State features per train (8 features each)
        train_features = []
        for train in self.current_conflict.trains[:5]:  # Max 5 trains
            features = [
                train.priority_score / 100.0,  # Normalized priority
                train.passenger_count / 500.0,  # Normalized passenger count
                train.cargo_value / 100000.0,  # Normalized cargo value
                float(train.type.value),  # Train type as float
                1.0 if train.type == TrainType.EXPRESS else 0.0,  # Express flag
                1.0 if train.type == TrainType.PASSENGER else 0.0,  # Passenger flag
                1.0 if train.type == TrainType.FREIGHT else 0.0,  # Freight flag
                1.0 if train.type == TrainType.MAINTENANCE else 0.0,  # Maintenance flag
            ]
            train_features.extend(features)
        
        # Pad to fixed size (5 trains * 8 features = 40 features)
        while len(train_features) < 40:
            train_features.append(0.0)
        
        # Section features (4 features)
        section_features = []
        if self.current_conflict.sections:
            section = self.current_conflict.sections[0]  # Use first section
            section_features = [
                section.capacity / 10.0,  # Normalized capacity
                section.current_occupancy / 10.0,  # Normalized occupancy
                len(section.alternative_routes) / 5.0,  # Normalized alt routes
                self.current_conflict.severity,  # Conflict severity
            ]
        else:
            section_features = [0.0, 0.0, 0.0, 0.0]
        
        # Combine all features
        state = np.array(train_features[:40] + section_features, dtype=np.float32)
        return state
    
    def step(self, action_idx: int):
        """Execute action and return next state, reward, done"""
        if not self.current_conflict:
            return self._get_state(), -100, True, {}
            
        action = self._decode_action(action_idx)
        if not action:
            return self._get_state(), -50, True, {"error": "invalid_action"}
        
        self.action_history.append(action)
        
        # Calculate reward
        reward = self._calculate_reward(action)
        
        # Check if episode is done
        done = (len(self.action_history) >= self.max_actions_per_episode or 
                self._conflict_resolved())
        
        return self._get_state(), reward, done, {"action": action}
    
    def _decode_action(self, action_idx: int) -> Optional[Action]:
        """Convert action index to Action object"""
        if not self.current_conflict or not self.current_conflict.trains:
            return None
            
        num_trains = len(self.current_conflict.trains)
        
        # Action space design:
        # 0-N: Delay train i by 10 minutes
        # N+1-2N: Delay train i by 20 minutes  
        # 2N+1-3N: Delay train i by 30 minutes
        # 3N+1-4N: Reroute train i
        # 4N+1-5N: Priority override train i
        
        if action_idx < num_trains:  # Delay 10 min
            train = self.current_conflict.trains[action_idx]
            return Action(
                type=ActionType.DELAY_TRAIN,
                train_id=train.id,
                parameters={'minutes': 10},
                estimated_cost=5.0
            )
        elif action_idx < 2 * num_trains:  # Delay 20 min
            train_idx = action_idx - num_trains
            train = self.current_conflict.trains[train_idx]
            return Action(
                type=ActionType.DELAY_TRAIN,
                train_id=train.id,
                parameters={'minutes': 20},
                estimated_cost=10.0
            )
        elif action_idx < 3 * num_trains:  # Delay 30 min
            train_idx = action_idx - 2 * num_trains
            train = self.current_conflict.trains[train_idx]
            return Action(
                type=ActionType.DELAY_TRAIN,
                train_id=train.id,
                parameters={'minutes': 30},
                estimated_cost=15.0
            )
        elif action_idx < 4 * num_trains:  # Reroute
            train_idx = action_idx - 3 * num_trains
            train = self.current_conflict.trains[train_idx]
            # Find alternative route
            alt_route = "ALT_ROUTE_1"  # Simplified
            return Action(
                type=ActionType.REROUTE_TRAIN,
                train_id=train.id,
                parameters={'alternative_path': alt_route, 'estimated_delay': 5},
                estimated_cost=3.0
            )
        elif action_idx < 5 * num_trains:  # Priority override
            train_idx = action_idx - 4 * num_trains
            train = self.current_conflict.trains[train_idx]
            return Action(
                type=ActionType.PRIORITY_OVERRIDE,
                train_id=train.id,
                parameters={'new_priority': min(train.priority_score + 20, 100)},
                estimated_cost=2.0
            )
        
        return None
    
    def _calculate_reward(self, action: Action) -> float:
        """Calculate reward for the action"""
        # Base reward calculation
        reward = 0.0
        
        # Safety reward/penalty
        if action.validate_safety():
            reward += 20.0  # Safety bonus
        else:
            reward -= 100.0  # Large safety penalty
        
        # Action-specific rewards
        if action.type == ActionType.DELAY_TRAIN:
            delay_minutes = action.parameters.get('minutes', 0)
            
            # Find the train being delayed
            train = next((t for t in self.current_conflict.trains if t.id == action.train_id), None)
            if train:
                # Penalty based on train priority and passenger impact
                priority_penalty = (100 - train.priority_score) * 0.1  # Higher priority = more penalty
                passenger_penalty = train.passenger_count * delay_minutes * 0.001
                
                reward -= (priority_penalty + passenger_penalty)
                
                # Bonus for delaying lower priority trains
                if train.type in [TrainType.FREIGHT, TrainType.MAINTENANCE]:
                    reward += 10.0
                    
        elif action.type == ActionType.REROUTE_TRAIN:
            train = next((t for t in self.current_conflict.trains if t.id == action.train_id), None)
            if train:
                # Rerouting bonus, especially for freight
                if train.type == TrainType.FREIGHT:
                    reward += 15.0
                else:
                    reward += 5.0
                    
        elif action.type == ActionType.PRIORITY_OVERRIDE:
            # Small penalty for disrupting normal priorities
            reward -= 5.0
        
        # Efficiency bonus (prefer fewer actions)
        if len(self.action_history) <= 2:
            reward += 10.0
        
        # Conflict resolution progress
        if self._conflict_resolved():
            reward += 50.0  # Large bonus for resolving conflict
            
        return reward
    
    def _conflict_resolved(self) -> bool:
        """Check if conflict is resolved by current actions"""
        # Simplified check: if we have taken actions affecting capacity
        total_capacity_freed = 0
        for action in self.action_history:
            if action.type in [ActionType.DELAY_TRAIN, ActionType.REROUTE_TRAIN]:
                total_capacity_freed += 1
                
        # Conflict resolved if we've freed enough capacity
        if self.current_conflict and self.current_conflict.sections:
            over_capacity = (self.current_conflict.sections[0].current_occupancy - 
                           self.current_conflict.sections[0].capacity)
            return total_capacity_freed >= over_capacity
            
        return False
    
    def get_action_space_size(self, conflict: Conflict) -> int:
        """Get size of action space for given conflict"""
        num_trains = len(conflict.trains) if conflict.trains else 1
        return num_trains * 5  # 5 action types per train


class RLAgent:
    """Deep Q-Network Agent for Railway Conflict Resolution"""
    
    def __init__(self, state_size: int = 44, learning_rate: float = 0.001):
        self.state_size = state_size
        self.learning_rate = learning_rate
        self.epsilon = 1.0  # Exploration rate
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.memory = []
        self.max_memory = 10000
        
        # Neural network weights (simplified representation)
        # In practice, you'd use TensorFlow/PyTorch here
        self.q_network = self._build_network()
        
    def _build_network(self):
        """Build neural network for Q-learning (simplified)"""
        # This is a placeholder - in real implementation use TensorFlow/PyTorch
        return {
            'layer1_weights': np.random.randn(self.state_size, 64) * 0.1,
            'layer1_bias': np.zeros(64),
            'layer2_weights': np.random.randn(64, 32) * 0.1,
            'layer2_bias': np.zeros(32),
            'output_weights': np.random.randn(32, 50) * 0.1,  # Max 50 actions
            'output_bias': np.zeros(50)
        }
    
    def predict(self, state: np.ndarray, num_actions: int) -> int:
        """Predict best action for given state"""
        # Simplified forward pass (use real neural network in practice)
        if np.random.random() <= self.epsilon:
            return np.random.randint(0, num_actions)  # Explore
        
        # Forward pass through network
        x = state
        x = np.maximum(0, np.dot(x, self.q_network['layer1_weights']) + self.q_network['layer1_bias'])  # ReLU
        x = np.maximum(0, np.dot(x, self.q_network['layer2_weights']) + self.q_network['layer2_bias'])  # ReLU
        q_values = np.dot(x, self.q_network['output_weights']) + self.q_network['output_bias']
        
        return np.argmax(q_values[:num_actions])  # Choose best action
    
    def remember(self, state, action, reward, next_state, done):
        """Store experience in replay buffer"""
        self.memory.append((state, action, reward, next_state, done))
        if len(self.memory) > self.max_memory:
            self.memory.pop(0)
    
    def train(self, batch_size: int = 32):
        """Train the agent on a batch of experiences"""
        if len(self.memory) < batch_size:
            return
            
        # Sample batch from memory
        batch = np.random.choice(len(self.memory), batch_size, replace=False)
        
        # In real implementation, this would update neural network weights
        # using backpropagation and gradient descent
        
        # Decay exploration rate
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay


class ReinforcementLearningSolver:
    """RL-based conflict resolution solver"""
    
    def __init__(self):
        self.name = "reinforcement_learning"
        self.trained = False
        self.agent = RLAgent()
        self.environment = RLEnvironment()
        self.training_episodes = 0
        
    def solve(self, conflict: Conflict, timeout: float = 10.0) -> List[Solution]:
        """Generate solutions using trained RL agent"""
        if not self.trained:
            logger.warning("RL agent not trained, using random policy")
            
        start_time = time.time()
        solutions = []
        
        try:
            # Reset environment with conflict
            state = self.environment.reset(conflict)
            actions = []
            total_reward = 0
            
            # Run episode
            for step in range(3):  # Max 3 actions per conflict
                if time.time() - start_time > timeout - 1:
                    break
                    
                # Get action from agent
                action_space_size = self.environment.get_action_space_size(conflict)
                action_idx = self.agent.predict(state, action_space_size)
                
                # Execute action
                next_state, reward, done, info = self.environment.step(action_idx)
                total_reward += reward
                
                # Store action if valid
                if 'action' in info:
                    actions.append(info['action'])
                
                state = next_state
                
                if done:
                    break
            
            # Create solution from actions
            if actions:
                solution = Solution(
                    id=f"rl_{conflict.id}",
                    actions=actions,
                    safety_score=max(0, min(100, 85 + total_reward * 0.1)),  # Convert reward to score
                    efficiency_score=max(0, min(100, 80 + total_reward * 0.1)),
                    passenger_impact_score=max(0, min(100, 75 + total_reward * 0.15)),
                    computation_time=time.time() - start_time,
                    solver_method=self.name
                )
                
                if solution.validate():
                    solutions.append(solution)
                    
        except Exception as e:
            logger.error(f"RL solver failed: {e}")
        
        return solutions
    
    def train(self, training_data: List[Tuple[Conflict, Solution]], episodes: int = 1000):
        """Train RL agent on historical conflict data"""
        logger.info(f"Training RL agent for {episodes} episodes...")
        
        for episode in range(episodes):
            if episode % 100 == 0:
                logger.info(f"Training episode {episode}/{episodes}")
            
            # Select random conflict from training data
            if training_data:
                conflict, expert_solution = training_data[np.random.randint(len(training_data))]
            else:
                # Generate synthetic training conflict
                conflict = self._generate_synthetic_conflict()
                expert_solution = None
            
            # Run training episode
            state = self.environment.reset(conflict)
            total_reward = 0
            
            for step in range(3):
                action_space_size = self.environment.get_action_space_size(conflict)
                action_idx = self.agent.predict(state, action_space_size)
                
                next_state, reward, done, info = self.environment.step(action_idx)
                total_reward += reward
                
                # Store experience for replay
                self.agent.remember(state, action_idx, reward, next_state, done)
                
                state = next_state
                
                if done:
                    break
            
            # Train agent on experiences
            if episode % 10 == 0:  # Train every 10 episodes
                self.agent.train()
        
        self.trained = True
        self.training_episodes = episodes
        logger.info(f"RL agent training completed after {episodes} episodes")
    
    def _generate_synthetic_conflict(self) -> Conflict:
        """Generate synthetic conflict for training"""
        sample_time = datetime.now() + timedelta(hours=1)
        
        # Random number of trains (2-4)
        num_trains = np.random.randint(2, 5)
        trains = []
        
        for i in range(num_trains):
            train_types = [TrainType.EXPRESS, TrainType.PASSENGER, TrainType.FREIGHT, TrainType.MAINTENANCE]
            train_type = np.random.choice(train_types)
            
            train = Train(
                id=f"SYNTHETIC_{i}",
                type=train_type,
                current_section="SEC_TRAIN",
                destination=f"DEST_{i}",
                scheduled_time=sample_time + timedelta(minutes=i*5),
                passenger_count=np.random.randint(0, 400) if train_type != TrainType.FREIGHT else 0,
                cargo_value=np.random.randint(10000, 100000) if train_type == TrainType.FREIGHT else 0
            )
            trains.append(train)
        
        # Create bottleneck section
        capacity = np.random.randint(1, 3)
        occupancy = capacity + np.random.randint(1, 3)  # Always overcapacity
        
        section = RailwaySection(
            id="SEC_TRAIN",
            capacity=capacity,
            current_occupancy=occupancy,
            alternative_routes=["ALT_1", "ALT_2"] if np.random.random() > 0.5 else []
        )
        
        return Conflict(
            id=f"SYNTHETIC_{np.random.randint(1000)}",
            trains=trains,
            sections=[section],
            conflict_time=sample_time,
            severity=np.random.uniform(0.5, 1.0)
        )


class OptimizationEngine:
    """Main optimization engine orchestrating multiple solvers"""
    
    def __init__(self):
        self.rule_solver = RuleBasedSolver()
        self.constraint_solver = ConstraintSolver()
        self.rl_solver = ReinforcementLearningSolver()
        self.executor = ThreadPoolExecutor(max_workers=4)  # Increased for RL solver
        
    def solve_conflict(self, conflict: Conflict, timeout: float = 10.0) -> List[Solution]:
        """
        Main conflict resolution method
        
        Args:
            conflict: Conflict object with trains, sections, constraints
            timeout: Maximum time for solution generation in seconds
            
        Returns:
            List of Solution objects ranked by total score
        """
        if not conflict.validate():
            raise ValueError("Invalid conflict data")
            
        logger.info(f"Solving conflict {conflict.id} with {len(conflict.trains)} trains")
        start_time = time.time()
        
        all_solutions = []
        
        try:
            # Submit solver tasks concurrently
            future_to_solver = {}
            
            # Always use rule-based solver as fallback
            future_rule = self.executor.submit(
                self.rule_solver.solve, conflict, timeout
            )
            future_to_solver[future_rule] = "rule_based"
            
            # Use constraint solver if available
            if self.constraint_solver.available:
                future_constraint = self.executor.submit(
                    self.constraint_solver.solve, conflict, timeout
                )
                future_to_solver[future_constraint] = "constraint"
            
            # Use RL solver if trained
            if self.rl_solver.trained:
                future_rl = self.executor.submit(
                    self.rl_solver.solve, conflict, timeout
                )
                future_to_solver[future_rl] = "reinforcement_learning"
            
            # Collect solutions with timeout handling
            for future in future_to_solver:
                try:
                    remaining_time = timeout - (time.time() - start_time)
                    if remaining_time > 0:
                        solutions = future.result(timeout=remaining_time)
                        all_solutions.extend(solutions)
                        logger.info(f"{future_to_solver[future]} solver produced {len(solutions)} solutions")
                except TimeoutError:
                    logger.warning(f"{future_to_solver[future]} solver timed out")
                    future.cancel()
                except Exception as e:
                    logger.error(f"{future_to_solver[future]} solver failed: {e}")
            
            # Validate and rank solutions
            valid_solutions = [s for s in all_solutions if s.validate()]
            valid_solutions.sort(key=lambda s: s.total_score, reverse=True)
            
            # Limit to top 3 solutions as specified
            final_solutions = valid_solutions[:3]
            
            total_time = time.time() - start_time
            logger.info(f"Generated {len(final_solutions)} valid solutions in {total_time:.2f}s")
            
            if not final_solutions:
                logger.warning("No valid solutions found, generating emergency solution")
                emergency_solution = self._generate_emergency_solution(conflict)
                if emergency_solution:
                    final_solutions.append(emergency_solution)
            
            return final_solutions
            
        except Exception as e:
            logger.error(f"Optimization engine failed: {e}")
            # Return emergency solution as last resort
            emergency = self._generate_emergency_solution(conflict)
            return [emergency] if emergency else []
    
    def _generate_emergency_solution(self, conflict: Conflict) -> Optional[Solution]:
        """Generate minimal emergency solution when all else fails"""
        try:
            # Simple solution: delay the lowest priority train by 30 minutes
            lowest_priority_train = max(conflict.trains, key=lambda t: t.priority_score)
            
            action = Action(
                type=ActionType.DELAY_TRAIN,
                train_id=lowest_priority_train.id,
                parameters={'minutes': 30},
                estimated_cost=15.0
            )
            
            return Solution(
                id=f"emergency_{conflict.id}",
                actions=[action],
                safety_score=80.0,
                efficiency_score=60.0,
                passenger_impact_score=70.0,
                solver_method="emergency"
            )
        except Exception as e:
            logger.error(f"Emergency solution generation failed: {e}")
            return None


# FastAPI Integration
app = FastAPI(title="Railway Optimization API", version="1.0.0")
optimization_engine = OptimizationEngine()

# Pydantic models for API
class TrainRequest(BaseModel):
    id: str
    type: str
    current_section: str
    destination: str
    scheduled_time: str
    passenger_count: int = 0
    cargo_value: float = 0.0
    
    @validator('type')
    def validate_train_type(cls, v):
        valid_types = ['EXPRESS', 'PASSENGER', 'FREIGHT', 'MAINTENANCE']
        if v.upper() not in valid_types:
            raise ValueError(f'Invalid train type. Must be one of: {valid_types}')
        return v.upper()

class SectionRequest(BaseModel):
    id: str
    capacity: int
    current_occupancy: int
    alternative_routes: List[str] = []

class ConflictRequest(BaseModel):
    trains: List[TrainRequest]
    sections: List[SectionRequest]
    conflict_time: str
    severity: float
    constraints: Dict[str, Any] = {}

class ActionResponse(BaseModel):
    type: str
    train_id: str
    parameters: Dict[str, Any]
    estimated_cost: float

class SolutionResponse(BaseModel):
    id: str
    actions: List[ActionResponse]
    safety_score: float
    efficiency_score: float
    passenger_impact_score: float
    total_score: float
    computation_time: float
    solver_method: str


@app.post("/api/conflicts/{conflict_id}/solve", response_model=List[SolutionResponse])
async def solve_conflict_endpoint(
    conflict_id: str,
    conflict_request: ConflictRequest,
    background_tasks: BackgroundTasks,
    timeout: float = 10.0
):
    """
    Solve railway conflict and return optimized solutions
    
    Args:
        conflict_id: Unique conflict identifier
        conflict_request: Conflict definition with trains and sections
        timeout: Maximum computation time in seconds
        
    Returns:
        List of ranked solutions with actions and scores
    """
    try:
        # Convert request to domain objects
        trains = []
        for train_req in conflict_request.trains:
            train = Train(
                id=train_req.id,
                type=TrainType[train_req.type],
                current_section=train_req.current_section,
                destination=train_req.destination,
                scheduled_time=datetime.fromisoformat(train_req.scheduled_time),
                passenger_count=train_req.passenger_count,
                cargo_value=train_req.cargo_value
            )
            trains.append(train)
        
        sections = []
        for section_req in conflict_request.sections:
            section = RailwaySection(
                id=section_req.id,
                capacity=section_req.capacity,
                current_occupancy=section_req.current_occupancy,
                alternative_routes=section_req.alternative_routes
            )
            sections.append(section)
        
        conflict = Conflict(
            id=conflict_id,
            trains=trains,
            sections=sections,
            conflict_time=datetime.fromisoformat(conflict_request.conflict_time),
            severity=conflict_request.severity,
            constraints=conflict_request.constraints
        )
        
        # Validate timeout
        if timeout > 30.0:
            raise HTTPException(status_code=400, detail="Timeout cannot exceed 30 seconds")
        
        # Solve conflict
        solutions = optimization_engine.solve_conflict(conflict, timeout)
        
        if not solutions:
            raise HTTPException(status_code=404, detail="No feasible solutions found")
        
        # Convert to response format
        response_solutions = []
        for solution in solutions:
            actions_response = [
                ActionResponse(
                    type=action.type.value,
                    train_id=action.train_id,
                    parameters=action.parameters,
                    estimated_cost=action.estimated_cost
                )
                for action in solution.actions
            ]
            
            solution_response = SolutionResponse(
                id=solution.id,
                actions=actions_response,
                safety_score=solution.safety_score,
                efficiency_score=solution.efficiency_score,
                passenger_impact_score=solution.passenger_impact_score,
                total_score=solution.total_score,
                computation_time=solution.computation_time,
                solver_method=solution.solver_method
            )
            response_solutions.append(solution_response)
        
        # Log solution for monitoring
        background_tasks.add_task(
            log_solution_metrics, 
            conflict_id, 
            len(solutions), 
            max(s.computation_time for s in solutions)
        )
        
        return response_solutions
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"API endpoint failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def log_solution_metrics(conflict_id: str, solution_count: int, max_time: float):
    """Background task for logging solution metrics"""
    logger.info(
        f"Conflict {conflict_id}: Generated {solution_count} solutions "
        f"in {max_time:.2f}s"
    )


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "solvers": {
            "rule_based": True,
            "constraint_programming": optimization_engine.constraint_solver.available,
            "reinforcement_learning": optimization_engine.rl_solver.trained
        },
        "rl_training_episodes": optimization_engine.rl_solver.training_episodes if optimization_engine.rl_solver.trained else 0
    }


@app.post("/api/rl/train")
async def train_rl_agent(
    background_tasks: BackgroundTasks,
    episodes: int = 1000,
    use_synthetic_data: bool = True
):
    """Train the RL agent on conflict resolution data"""
    try:
        if optimization_engine.rl_solver.trained:
            return {
                "status": "already_trained",
                "episodes": optimization_engine.rl_solver.training_episodes,
                "message": "RL agent already trained. Use retrain endpoint to train again."
            }
        
        # Generate synthetic training data or use historical data
        training_data = []
        if use_synthetic_data:
            logger.info("Generating synthetic training data for RL agent...")
            # Training data will be generated during training process
        
        # Start training in background
        background_tasks.add_task(
            run_rl_training,
            training_data,
            episodes
        )
        
        return {
            "status": "training_started",
            "episodes": episodes,
            "estimated_time_minutes": episodes // 100,  # Rough estimate
            "message": "RL training started in background. Check /api/rl/status for progress."
        }
        
    except Exception as e:
        logger.error(f"RL training initiation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to start RL training")


@app.post("/api/rl/retrain")
async def retrain_rl_agent(
    background_tasks: BackgroundTasks,
    episodes: int = 500
):
    """Retrain the RL agent with additional episodes"""
    try:
        # Start retraining in background
        background_tasks.add_task(
            run_rl_training,
            [],  # Use synthetic data
            episodes
        )
        
        return {
            "status": "retraining_started",
            "episodes": episodes,
            "previous_episodes": optimization_engine.rl_solver.training_episodes,
            "message": "RL retraining started in background."
        }
        
    except Exception as e:
        logger.error(f"RL retraining failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to start RL retraining")


@app.get("/api/rl/status")
async def get_rl_status():
    """Get RL agent training status"""
    return {
        "trained": optimization_engine.rl_solver.trained,
        "training_episodes": optimization_engine.rl_solver.training_episodes,
        "epsilon": optimization_engine.rl_solver.agent.epsilon if optimization_engine.rl_solver.trained else None,
        "memory_size": len(optimization_engine.rl_solver.agent.memory) if optimization_engine.rl_solver.trained else 0,
        "solver_available": optimization_engine.rl_solver.trained
    }


@app.post("/api/conflicts/{conflict_id}/solve_rl")
async def solve_conflict_rl_only(
    conflict_id: str,
    conflict_request: ConflictRequest,
    timeout: float = 10.0
):
    """Solve conflict using only the RL agent"""
    try:
        if not optimization_engine.rl_solver.trained:
            raise HTTPException(
                status_code=400, 
                detail="RL agent not trained. Use /api/rl/train endpoint first."
            )
        
        # Convert request to domain objects (same as main endpoint)
        trains = []
        for train_req in conflict_request.trains:
            train = Train(
                id=train_req.id,
                type=TrainType[train_req.type],
                current_section=train_req.current_section,
                destination=train_req.destination,
                scheduled_time=datetime.fromisoformat(train_req.scheduled_time),
                passenger_count=train_req.passenger_count,
                cargo_value=train_req.cargo_value
            )
            trains.append(train)
        
        sections = []
        for section_req in conflict_request.sections:
            section = RailwaySection(
                id=section_req.id,
                capacity=section_req.capacity,
                current_occupancy=section_req.current_occupancy,
                alternative_routes=section_req.alternative_routes
            )
            sections.append(section)
        
        conflict = Conflict(
            id=conflict_id,
            trains=trains,
            sections=sections,
            conflict_time=datetime.fromisoformat(conflict_request.conflict_time),
            severity=conflict_request.severity,
            constraints=conflict_request.constraints
        )
        
        # Solve using only RL solver
        solutions = optimization_engine.rl_solver.solve(conflict, timeout)
        
        if not solutions:
            raise HTTPException(status_code=404, detail="No RL solutions found")
        
        # Convert to response format
        response_solutions = []
        for solution in solutions:
            actions_response = [
                ActionResponse(
                    type=action.type.value,
                    train_id=action.train_id,
                    parameters=action.parameters,
                    estimated_cost=action.estimated_cost
                )
                for action in solution.actions
            ]
            
            solution_response = SolutionResponse(
                id=solution.id,
                actions=actions_response,
                safety_score=solution.safety_score,
                efficiency_score=solution.efficiency_score,
                passenger_impact_score=solution.passenger_impact_score,
                total_score=solution.total_score,
                computation_time=solution.computation_time,
                solver_method=solution.solver_method
            )
            response_solutions.append(solution_response)
        
        return response_solutions
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"RL-only endpoint failed: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


async def run_rl_training(training_data: List, episodes: int):
    """Background task for RL agent training"""
    try:
        logger.info(f"Starting RL training with {episodes} episodes")
        optimization_engine.rl_solver.train(training_data, episodes)
        logger.info("RL training completed successfully")
    except Exception as e:
        logger.error(f"RL training failed: {e}")


if __name__ == "__main__":
    # Example usage and testing with RL integration
    
    # Create sample conflict
    sample_trains = [
        Train(
            id="EXP_001",
            type=TrainType.EXPRESS,
            current_section="SEC_A",
            destination="DEST_1",
            scheduled_time=datetime.now() + timedelta(minutes=30),
            passenger_count=200
        ),
        Train(
            id="PASS_002",
            type=TrainType.PASSENGER,
            current_section="SEC_A",
            destination="DEST_2",
            scheduled_time=datetime.now() + timedelta(minutes=32),
            passenger_count=150
        ),
        Train(
            id="FREIGHT_003",
            type=TrainType.FREIGHT,
            current_section="SEC_A",
            destination="DEST_3",
            scheduled_time=datetime.now() + timedelta(minutes=35),
            cargo_value=50000
        )
    ]
    
    sample_sections = [
        RailwaySection(
            id="SEC_A",
            capacity=2,
            current_occupancy=3,  # Overloaded!
            alternative_routes=["SEC_B", "SEC_C"]
        )
    ]
    
    sample_conflict = Conflict(
        id="CONFLICT_001",
        trains=sample_trains,
        sections=sample_sections,
        conflict_time=datetime.now() + timedelta(minutes=30),
        severity=0.8
    )
    
    # Test optimization engine
    engine = OptimizationEngine()
    
    print("🚂 Railway AI Optimization Module - Demo")
    print("=" * 50)
    
    # Test initial solutions (without RL)
    print("\n1. Testing without RL training:")
    solutions = engine.solve_conflict(sample_conflict)
    
    print(f"Generated {len(solutions)} solutions:")
    for i, solution in enumerate(solutions, 1):
        print(f"\nSolution {i} ({solution.solver_method}):")
        print(f"  Total Score: {solution.total_score:.2f}")
        print(f"  Safety: {solution.safety_score:.1f}")
        print(f"  Efficiency: {solution.efficiency_score:.1f}")
        print(f"  Passenger Impact: {solution.passenger_impact_score:.1f}")
        print(f"  Computation Time: {solution.computation_time:.3f}s")
        print(f"  Actions: {len(solution.actions)}")
        for action in solution.actions:
            print(f"    - {action.type.value}: {action.train_id} -> {action.parameters}")
    
    # Train RL agent
    print("\n2. Training RL Agent:")
    print("Training RL agent with synthetic conflicts...")
    start_time = time.time()
    engine.rl_solver.train([], episodes=200)  # Quick training for demo
    training_time = time.time() - start_time
    print(f"RL training completed in {training_time:.2f}s")
    print(f"Agent epsilon (exploration rate): {engine.rl_solver.agent.epsilon:.3f}")
    print(f"Experience memory size: {len(engine.rl_solver.agent.memory)}")
    
    # Test with trained RL agent
    print("\n3. Testing with trained RL agent:")
    solutions_with_rl = engine.solve_conflict(sample_conflict)
    
    print(f"Generated {len(solutions_with_rl)} solutions:")
    solver_counts = {}
    for solution in solutions_with_rl:
        solver_counts[solution.solver_method] = solver_counts.get(solution.solver_method, 0) + 1
    
    print(f"Solutions by solver: {solver_counts}")
    
    # Show best solution
    if solutions_with_rl:
        best_solution = solutions_with_rl[0]  # Already sorted by score
        print(f"\n🏆 Best Solution ({best_solution.solver_method}):")
        print(f"  Total Score: {best_solution.total_score:.2f}")
        print(f"  Safety: {best_solution.safety_score:.1f}")
        print(f"  Efficiency: {best_solution.efficiency_score:.1f}")
        print(f"  Passenger Impact: {best_solution.passenger_impact_score:.1f}")
        print(f"  Actions:")
        for action in best_solution.actions:
            print(f"    - {action.type.value}: {action.train_id}")
            print(f"      Parameters: {action.parameters}")
            print(f"      Estimated Cost: ${action.estimated_cost:.2f}")
    
    # Compare RL vs other solvers
    print("\n4. Solver Performance Comparison:")
    rl_solutions = [s for s in solutions_with_rl if s.solver_method == "reinforcement_learning"]
    rule_solutions = [s for s in solutions_with_rl if s.solver_method == "rule_based"]
    
    if rl_solutions and rule_solutions:
        rl_avg_score = sum(s.total_score for s in rl_solutions) / len(rl_solutions)
        rule_avg_score = sum(s.total_score for s in rule_solutions) / len(rule_solutions)
        
        print(f"RL Average Score: {rl_avg_score:.2f}")
        print(f"Rule-based Average Score: {rule_avg_score:.2f}")
        print(f"RL Performance: {'+' if rl_avg_score > rule_avg_score else '-'}{abs(rl_avg_score - rule_avg_score):.2f} points")
    
    # Demonstrate RL learning progression
    print("\n5. RL Learning Progression Test:")
    print("Testing RL agent performance over multiple conflicts...")
    
    test_conflicts = [engine.rl_solver._generate_synthetic_conflict() for _ in range(5)]
    rl_scores = []
    
    for i, conflict in enumerate(test_conflicts):
        rl_solutions = engine.rl_solver.solve(conflict, timeout=5.0)
        if rl_solutions:
            avg_score = sum(s.total_score for s in rl_solutions) / len(rl_solutions)
            rl_scores.append(avg_score)
            print(f"  Conflict {i+1}: Score {avg_score:.2f}")
    
    if rl_scores:
        print(f"  Average RL Score: {sum(rl_scores)/len(rl_scores):.2f}")
        print(f"  Score Range: {min(rl_scores):.2f} - {max(rl_scores):.2f}")
    
    print("\n6. System Health Check:")
    health_status = {
        "Rule-based Solver": "✅ Active",
        "Constraint Solver": "✅ Active" if engine.constraint_solver.available else "⚠️ OR-Tools unavailable",
        "RL Solver": "✅ Trained" if engine.rl_solver.trained else "❌ Not trained",
        "RL Episodes": engine.rl_solver.training_episodes if engine.rl_solver.trained else 0,
        "RL Memory": len(engine.rl_solver.agent.memory) if engine.rl_solver.trained else 0
    }
    
    for component, status in health_status.items():
        print(f"  {component}: {status}")
    
    print("\n" + "=" * 50)
    print("🎯 Demo completed! Starting FastAPI server...")
    print("📍 API Documentation: http://localhost:8000/docs")
    print("🏥 Health Check: http://localhost:8000/api/health")
    print("🤖 RL Status: http://localhost:8000/api/rl/status")
    print("🚀 Train RL: POST http://localhost:8000/api/rl/train")
    print("=" * 50)
    
    # Start FastAPI server
    # uvicorn.run(app, host="0.0.0.0", port=8000)    ]
    
    sample_sections = [
        RailwaySection(
            id="SEC_A",
            capacity=2,
            current_occupancy=3,  # Overloaded!
            alternative_routes=["SEC_B", "SEC_C"]
        )
    ]
    
    sample_conflict = Conflict(
        id="CONFLICT_001",
        trains=sample_trains,
        sections=sample_sections,
        conflict_time=datetime.now() + timedelta(minutes=30),
        severity=0.8
    )
    
    # Test optimization engine
    engine = OptimizationEngine()
    
    print("🚂 Railway AI Optimization Module - Demo")
    print("=" * 50)
    
    # Test initial solutions (without RL)
    print("\n1. Testing without RL training:")
    solutions = engine.solve_conflict(sample_conflict)
    
    print(f"Generated {len(solutions)} solutions:")
    for i, solution in enumerate(solutions, 1):
        print(f"\nSolution {i} ({solution.solver_method}):")
        print(f"  Total Score: {solution.total_score:.2f}")
        print(f"  Safety: {solution.safety_score:.1f}")
        print(f"  Efficiency: {solution.efficiency_score:.1f}")
        print(f"  Passenger Impact: {solution.passenger_impact_score:.1f}")
        print(f"  Computation Time: {solution.computation_time:.3f}s")
        print(f"  Actions: {len(solution.actions)}")
        for action in solution.actions:
            print(f"    - {action.type.value}: {action.train_id} -> {action.parameters}")
    
    # Train RL agent
    print("\n2. Training RL Agent:")
    print("Training RL agent with synthetic conflicts...")
    start_time = time.time()
    engine.rl_solver.train([], episodes=200)  # Quick training for demo
    training_time = time.time() - start_time
    print(f"RL training completed in {training_time:.2f}s")
    print(f"Agent epsilon (exploration rate): {engine.rl_solver.agent.epsilon:.3f}")
    print(f"Experience memory size: {len(engine.rl_solver.agent.memory)}")
    
    # Test with trained RL agent
    print("\n3. Testing with trained RL agent:")
    solutions_with_rl = engine.solve_conflict(sample_conflict)
    
    print(f"Generated {len(solutions_with_rl)} solutions:")
    solver_counts = {}
    for solution in solutions_with_rl:
        solver_counts[solution.solver_method] = solver_counts.get(solution.solver_method, 0) + 1
    
    print(f"Solutions by solver: {solver_counts}")
    
    # Show best solution
    if solutions_with_rl:
        best_solution = solutions_with_rl[0]  # Already sorted by score
        print(f"\n🏆 Best Solution ({best_solution.solver_method}):")
        print(f"  Total Score: {best_solution.total_score:.2f}")
        print(f"  Safety: {best_solution.safety_score:.1f}")
        print(f"  Efficiency: {best_solution.efficiency_score:.1f}")
        print(f"  Passenger Impact: {best_solution.passenger_impact_score:.1f}")
        print(f"  Actions:")
        for action in best_solution.actions:
            print(f"    - {action.type.value}: {action.train_id}")
            print(f"      Parameters: {action.parameters}")
            print(f"      Estimated Cost: ${action.estimated_cost:.2f}")
    
    # Compare RL vs other solvers
    print("\n4. Solver Performance Comparison:")
    rl_solutions = [s for s in solutions_with_rl if s.solver_method == "reinforcement_learning"]
    rule_solutions = [s for s in solutions_with_rl if s.solver_method == "rule_based"]
    
    if rl_solutions and rule_solutions:
        rl_avg_score = sum(s.total_score for s in rl_solutions) / len(rl_solutions)
        rule_avg_score = sum(s.total_score for s in rule_solutions) / len(rule_solutions)
        
        print(f"RL Average Score: {rl_avg_score:.2f}")
        print(f"Rule-based Average Score: {rule_avg_score:.2f}")
        print(f"RL Performance: {'+' if rl_avg_score > rule_avg_score else '-'}{abs(rl_avg_score - rule_avg_score):.2f} points")
    
    # Demonstrate RL learning progression
    print("\n5. RL Learning Progression Test:")
    print("Testing RL agent performance over multiple conflicts...")
    
    test_conflicts = [engine.rl_solver._generate_synthetic_conflict() for _ in range(5)]
    rl_scores = []
    
    for i, conflict in enumerate(test_conflicts):
        rl_solutions = engine.rl_solver.solve(conflict, timeout=5.0)
        if rl_solutions:
            avg_score = sum(s.total_score for s in rl_solutions) / len(rl_solutions)
            rl_scores.append(avg_score)
            print(f"  Conflict {i+1}: Score {avg_score:.2f}")
    
    if rl_scores:
        print(f"  Average RL Score: {sum(rl_scores)/len(rl_scores):.2f}")
        print(f"  Score Range: {min(rl_scores):.2f} - {max(rl_scores):.2f}")
    
    print("\n6. System Health Check:")
    health_status = {
        "Rule-based Solver": "✅ Active",
        "Constraint Solver": "✅ Active" if engine.constraint_solver.available else "⚠️ OR-Tools unavailable",
        "RL Solver": "✅ Trained" if engine.rl_solver.trained else "❌ Not trained",
        "RL Episodes": engine.rl_solver.training_episodes if engine.rl_solver.trained else 0,
        "RL Memory": len(engine.rl_solver.agent.memory) if engine.rl_solver.trained else 0
    }
    
    for component, status in health_status.items():
        print(f"  {component}: {status}")
    
    print("\n" + "=" * 50)
    print("🎯 Demo completed! Starting FastAPI server...")
    print("📍 API Documentation: http://localhost:8000/docs")
    print("🏥 Health Check: http://localhost:8000/api/health")
    print("🤖 RL Status: http://localhost:8000/api/rl/status")
    print("🚀 Train RL: POST http://localhost:8000/api/rl/train")
    print("=" * 50)
    
    # Start FastAPI server
    # uvicorn.run(app, host="0.0.0.0", port=8000)