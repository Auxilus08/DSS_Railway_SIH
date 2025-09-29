"""
Advanced Railway AI Model Testing with Specialized Examples
Focus on model behavior analysis and performance characteristics
"""

import time
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple
from collections import defaultdict
import statistics

from railway_optimization import (
    Train, TrainType, RailwaySection, Conflict, 
    OptimizationEngine, ReinforcementLearningSolver
)

class AdvancedModelTester:
    """Advanced testing for railway optimization models"""
    
    def __init__(self):
        self.engine = OptimizationEngine()
        self.test_results = []
        
    def test_scalability_patterns(self):
        """Test model performance with increasing complexity"""
        print("📊 Scalability Testing: Performance vs Complexity")
        print("=" * 60)
        
        complexities = [2, 3, 5, 7, 10]  # Number of trains
        
        for num_trains in complexities:
            print(f"\n🎯 Testing with {num_trains} trains:")
            
            # Create conflict with varying number of trains
            sample_time = datetime.now() + timedelta(hours=1)
            trains = []
            
            for i in range(num_trains):
                train_types = [TrainType.EXPRESS, TrainType.PASSENGER, TrainType.FREIGHT]
                train_type = train_types[i % 3]
                
                trains.append(Train(
                    f"SCALE_TRAIN_{i:02d}",
                    train_type,
                    f"SCALE_SEC_{i % 2}",  # 2 sections to create conflicts
                    f"DEST_{i}",
                    sample_time + timedelta(minutes=i*2),
                    passenger_count=100 + i*50 if train_type != TrainType.FREIGHT else 0,
                    cargo_value=30000 + i*10000 if train_type == TrainType.FREIGHT else 0
                ))
            
            sections = [
                RailwaySection(f"SCALE_SEC_{i}", capacity=max(1, num_trains//3), 
                             current_occupancy=num_trains) for i in range(2)
            ]
            
            conflict = Conflict(f"SCALE_TEST_{num_trains}", trains, sections, sample_time, 0.8)
            
            # Test without RL
            start_time = time.time()
            solutions_pre = self.engine.solve_conflict(conflict)
            time_pre = time.time() - start_time
            
            # Train RL for this complexity
            self.engine.rl_solver.train([], episodes=min(200, num_trains * 40))
            
            # Test with RL
            start_time = time.time()
            solutions_post = self.engine.solve_conflict(conflict)
            time_post = time.time() - start_time
            
            print(f"   Pre-RL:  {len(solutions_pre)} solutions in {time_pre:.4f}s")
            print(f"   Post-RL: {len(solutions_post)} solutions in {time_post:.4f}s")
            
            if solutions_pre and solutions_post:
                improvement = solutions_post[0].total_score - solutions_pre[0].total_score
                print(f"   Improvement: {improvement:+.2f} points")
            
            print(f"   Complexity metric: {num_trains * 0.8:.1f}")
            
    def test_train_type_bias(self):
        """Test model behavior with different train type compositions"""
        print("\n🚂 Train Type Bias Testing")
        print("=" * 60)
        
        # Train the RL agent first
        print("Training RL agent for bias testing...")
        self.engine.rl_solver.train([], episodes=300)
        
        compositions = [
            ("All Express", [TrainType.EXPRESS] * 4),
            ("All Passenger", [TrainType.PASSENGER] * 4),
            ("All Freight", [TrainType.FREIGHT] * 4),
            ("Mixed Priority", [TrainType.EXPRESS, TrainType.PASSENGER, TrainType.FREIGHT, TrainType.MAINTENANCE]),
            ("Express Heavy", [TrainType.EXPRESS, TrainType.EXPRESS, TrainType.PASSENGER, TrainType.FREIGHT])
        ]
        
        for comp_name, train_types in compositions:
            print(f"\n🎯 Testing: {comp_name}")
            
            sample_time = datetime.now() + timedelta(hours=1)
            trains = []
            
            for i, train_type in enumerate(train_types):
                trains.append(Train(
                    f"BIAS_TRAIN_{i:02d}",
                    train_type,
                    "BIAS_SEC",
                    f"DEST_{i}",
                    sample_time + timedelta(minutes=i*3),
                    passenger_count=200 + i*25 if train_type != TrainType.FREIGHT else 0,
                    cargo_value=40000 + i*15000 if train_type == TrainType.FREIGHT else 0
                ))
            
            sections = [RailwaySection("BIAS_SEC", capacity=2, current_occupancy=len(trains))]
            conflict = Conflict(f"BIAS_{comp_name.replace(' ', '_')}", trains, sections, sample_time, 0.75)
            
            solutions = self.engine.solve_conflict(conflict)
            
            if solutions:
                best_solution = solutions[0]
                print(f"   Best solver: {best_solution.solver_method}")
                print(f"   Score: {best_solution.total_score:.2f}")
                print(f"   Actions: {len(best_solution.actions)}")
                
                # Analyze which trains got which actions
                action_by_train_type = defaultdict(list)
                for action in best_solution.actions:
                    train_id = action.train_id
                    train = next((t for t in trains if t.id == train_id), None)
                    if train:
                        action_by_train_type[train.type].append(action.type)
                
                for train_type, actions in action_by_train_type.items():
                    print(f"   {train_type.name}: {[a.value for a in actions]}")
    
    def test_timing_sensitivity(self):
        """Test model sensitivity to timing conflicts"""
        print("\n⏰ Timing Sensitivity Testing")
        print("=" * 60)
        
        # Train RL agent
        self.engine.rl_solver.train([], episodes=200)
        
        time_gaps = [1, 3, 5, 10, 15]  # Minutes between trains
        
        for gap in time_gaps:
            print(f"\n🎯 Testing with {gap}-minute gaps:")
            
            sample_time = datetime.now() + timedelta(hours=1)
            trains = [
                Train("TIME_EXP", TrainType.EXPRESS, "TIME_SEC", "DEST_1", sample_time, passenger_count=300),
                Train("TIME_PASS", TrainType.PASSENGER, "TIME_SEC", "DEST_2", 
                     sample_time + timedelta(minutes=gap), passenger_count=200),
                Train("TIME_FREIGHT", TrainType.FREIGHT, "TIME_SEC", "DEST_3", 
                     sample_time + timedelta(minutes=gap*2), cargo_value=75000)
            ]
            
            sections = [RailwaySection("TIME_SEC", capacity=1, current_occupancy=3)]
            conflict = Conflict(f"TIME_GAP_{gap}", trains, sections, sample_time, 
                              min(1.0, 0.5 + (10-gap)*0.05))  # Higher severity for smaller gaps
            
            solutions = self.engine.solve_conflict(conflict)
            
            if solutions:
                best_solution = solutions[0]
                print(f"   Severity: {conflict.severity:.2f}")
                print(f"   Best score: {best_solution.total_score:.2f}")
                print(f"   Solver: {best_solution.solver_method}")
                
                # Count delay actions and their magnitude
                delay_actions = [a for a in best_solution.actions if a.type.value == "delay_train"]
                if delay_actions:
                    total_delay = sum(a.parameters.get('minutes', 0) for a in delay_actions)
                    print(f"   Total delays: {total_delay} minutes across {len(delay_actions)} trains")
                else:
                    print(f"   No delay actions needed")
    
    def test_capacity_stress(self):
        """Test model under extreme capacity constraints"""
        print("\n🚧 Capacity Stress Testing")
        print("=" * 60)
        
        # Train RL agent
        self.engine.rl_solver.train([], episodes=400)
        
        # Test different overload ratios
        overload_ratios = [1.5, 2.0, 3.0, 4.0]  # trains/capacity ratio
        
        for ratio in overload_ratios:
            print(f"\n🎯 Testing {ratio:.1f}x overload:")
            
            capacity = 2
            num_trains = int(capacity * ratio)
            
            sample_time = datetime.now() + timedelta(hours=1)
            trains = []
            
            for i in range(num_trains):
                train_types = [TrainType.EXPRESS, TrainType.PASSENGER, TrainType.FREIGHT]
                train_type = train_types[i % 3]
                
                trains.append(Train(
                    f"STRESS_{i:02d}",
                    train_type,
                    "STRESS_SEC",
                    f"DEST_{i}",
                    sample_time + timedelta(minutes=i),
                    passenger_count=150 + i*25 if train_type != TrainType.FREIGHT else 0,
                    cargo_value=35000 + i*12000 if train_type == TrainType.FREIGHT else 0
                ))
            
            sections = [
                RailwaySection("STRESS_SEC", capacity=capacity, current_occupancy=num_trains,
                             alternative_routes=["SLOW_ALT", "LONG_ALT"])
            ]
            
            conflict = Conflict(f"STRESS_{ratio}", trains, sections, sample_time, 
                              min(1.0, ratio * 0.25))
            
            start_time = time.time()
            solutions = self.engine.solve_conflict(conflict)
            solve_time = time.time() - start_time
            
            if solutions:
                best_solution = solutions[0]
                print(f"   Trains: {num_trains}, Capacity: {capacity}")
                print(f"   Severity: {conflict.severity:.2f}")
                print(f"   Solutions: {len(solutions)} in {solve_time:.4f}s")
                print(f"   Best score: {best_solution.total_score:.2f}")
                
                # Analyze solution strategies
                action_types = defaultdict(int)
                for action in best_solution.actions:
                    action_types[action.type.value] += 1
                
                print(f"   Strategy: {dict(action_types)}")
            else:
                print(f"   ❌ No solutions found (system overloaded)")
    
    def test_learning_progression(self):
        """Test RL agent learning progression with different training sizes"""
        print("\n🧠 Learning Progression Analysis")
        print("=" * 60)
        
        episode_counts = [50, 100, 200, 400, 800]
        
        # Create a standard test conflict
        sample_time = datetime.now() + timedelta(hours=1)
        test_conflict = Conflict(
            "LEARNING_TEST",
            [
                Train("LEARN_EXP", TrainType.EXPRESS, "LEARN_SEC", "DEST_1", sample_time, passenger_count=400),
                Train("LEARN_PASS", TrainType.PASSENGER, "LEARN_SEC", "DEST_2", 
                     sample_time + timedelta(minutes=2), passenger_count=250),
                Train("LEARN_FREIGHT", TrainType.FREIGHT, "LEARN_SEC", "DEST_3", 
                     sample_time + timedelta(minutes=4), cargo_value=80000)
            ],
            [RailwaySection("LEARN_SEC", capacity=1, current_occupancy=3, alternative_routes=["ALT_1", "ALT_2"])],
            sample_time,
            0.85
        )
        
        print("Training progression results:")
        print("Episodes  |  Score  |  Actions  |  Epsilon  |  Memory")
        print("-" * 50)
        
        for episodes in episode_counts:
            # Reset and train RL agent
            self.engine.rl_solver = ReinforcementLearningSolver()
            self.engine.rl_solver.train([], episodes=episodes)
            
            # Test performance
            solutions = self.engine.solve_conflict(test_conflict)
            
            if solutions:
                rl_solutions = [s for s in solutions if s.solver_method == "reinforcement_learning"]
                if rl_solutions:
                    best_rl = rl_solutions[0]
                    epsilon = self.engine.rl_solver.agent.epsilon
                    memory_size = len(self.engine.rl_solver.agent.memory)
                    
                    print(f"{episodes:8d}  | {best_rl.total_score:6.2f} | {len(best_rl.actions):8d} | {epsilon:8.3f} | {memory_size:6d}")
                else:
                    print(f"{episodes:8d}  |   N/A   |    N/A   |    N/A   |   N/A")
            else:
                print(f"{episodes:8d}  |   N/A   |    N/A   |    N/A   |   N/A")
    
    def test_solver_consistency(self):
        """Test consistency of solver decisions across multiple runs"""
        print("\n🎯 Solver Consistency Testing")
        print("=" * 60)
        
        # Train RL agent
        self.engine.rl_solver.train([], episodes=300)
        
        # Create test conflict
        sample_time = datetime.now() + timedelta(hours=1)
        test_conflict = Conflict(
            "CONSISTENCY_TEST",
            [
                Train("CONS_EXP", TrainType.EXPRESS, "CONS_SEC", "DEST_1", sample_time, passenger_count=350),
                Train("CONS_PASS", TrainType.PASSENGER, "CONS_SEC", "DEST_2", 
                     sample_time + timedelta(minutes=3), passenger_count=180)
            ],
            [RailwaySection("CONS_SEC", capacity=1, current_occupancy=2, alternative_routes=["ALT_ROUTE"])],
            sample_time,
            0.7
        )
        
        # Run multiple times and analyze consistency
        num_runs = 10
        results = []
        
        print(f"Running {num_runs} consistency tests...")
        
        for run in range(num_runs):
            solutions = self.engine.solve_conflict(test_conflict)
            if solutions:
                best_solution = solutions[0]
                results.append({
                    'solver': best_solution.solver_method,
                    'score': best_solution.total_score,
                    'actions': len(best_solution.actions),
                    'action_types': [a.type.value for a in best_solution.actions]
                })
        
        if results:
            # Analyze consistency
            solvers = [r['solver'] for r in results]
            scores = [r['score'] for r in results]
            
            print(f"\nConsistency Analysis:")
            print(f"  Solver distribution: {dict(zip(*np.unique(solvers, return_counts=True)))}")
            print(f"  Score mean: {statistics.mean(scores):.2f}")
            print(f"  Score std: {statistics.stdev(scores):.2f}")
            print(f"  Score range: {min(scores):.2f} - {max(scores):.2f}")
            
            # Most common action patterns
            action_patterns = [tuple(r['action_types']) for r in results]
            pattern_counts = {}
            for pattern in action_patterns:
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
            
            print(f"  Most common action patterns:")
            for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
                print(f"    {pattern}: {count}/{num_runs} runs")

def main():
    """Run advanced model testing"""
    print("🚂 Advanced Railway AI Model Testing Suite")
    print("Analyzing model behavior patterns and performance characteristics")
    print("=" * 80)
    
    tester = AdvancedModelTester()
    
    # Run all advanced tests
    tester.test_scalability_patterns()
    tester.test_train_type_bias()
    tester.test_timing_sensitivity()
    tester.test_capacity_stress()
    tester.test_learning_progression()
    tester.test_solver_consistency()
    
    print(f"\n✅ Advanced testing completed!")
    print("=" * 80)

if __name__ == "__main__":
    main()