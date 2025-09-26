#!/usr/bin/env python3
"""
Performance test script for Railway Traffic Management API
Tests handling of 100 concurrent trains with position updates
"""

import asyncio
import aiohttp
import time
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "http://localhost:8000"
NUM_TRAINS = 100
UPDATES_PER_TRAIN = 10
CONCURRENT_REQUESTS = 20
TEST_DURATION_SECONDS = 60


class PerformanceTester:
    """Performance testing client for Railway Traffic Management API"""
    
    def __init__(self):
        self.session = None
        self.token = None
        self.results = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "response_times": [],
            "errors": [],
            "start_time": None,
            "end_time": None
        }
    
    async def setup(self):
        """Setup test environment"""
        logger.info("🔧 Setting up performance test environment...")
        
        # Create HTTP session
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
        
        # Authenticate
        await self.authenticate()
        
        logger.info("✅ Setup completed")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
        logger.info("🧹 Cleanup completed")
    
    async def authenticate(self):
        """Get authentication token"""
        try:
            async with self.session.post(f"{BASE_URL}/api/auth/login", json={
                "employee_id": "CTR001",
                "password": "password_CTR001"
            }) as response:
                if response.status == 200:
                    data = await response.json()
                    self.token = data["access_token"]
                    logger.info("✅ Authentication successful")
                else:
                    logger.error(f"❌ Authentication failed: {response.status}")
                    raise Exception("Authentication failed")
        
        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            raise
    
    def generate_train_position(self, train_id: int, section_id: int) -> Dict[str, Any]:
        """Generate realistic train position data"""
        # Base coordinates (New York area)
        base_lat = 40.7128
        base_lon = -74.0060
        
        # Add some randomness for different trains
        lat_offset = random.uniform(-0.1, 0.1)
        lon_offset = random.uniform(-0.1, 0.1)
        
        return {
            "train_id": train_id,
            "section_id": section_id,
            "coordinates": {
                "latitude": base_lat + lat_offset,
                "longitude": base_lon + lon_offset,
                "altitude": random.uniform(0, 100)
            },
            "speed_kmh": random.uniform(0, 160),
            "heading": random.uniform(0, 360),
            "timestamp": datetime.utcnow().isoformat(),
            "distance_from_start": random.uniform(0, 1000),
            "signal_strength": random.randint(70, 100),
            "gps_accuracy": random.uniform(1.0, 5.0)
        }
    
    async def send_position_update(self, train_id: int, section_id: int) -> Dict[str, Any]:
        """Send single position update and measure performance"""
        position_data = self.generate_train_position(train_id, section_id)
        
        start_time = time.time()
        
        try:
            async with self.session.post(
                f"{BASE_URL}/api/trains/position",
                json=position_data,
                headers={"Content-Type": "application/json"}
            ) as response:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                
                self.results["total_requests"] += 1
                self.results["response_times"].append(response_time)
                
                if response.status == 200:
                    self.results["successful_requests"] += 1
                    return {
                        "success": True,
                        "response_time": response_time,
                        "status": response.status,
                        "train_id": train_id
                    }
                else:
                    self.results["failed_requests"] += 1
                    error_text = await response.text()
                    self.results["errors"].append({
                        "train_id": train_id,
                        "status": response.status,
                        "error": error_text
                    })
                    return {
                        "success": False,
                        "response_time": response_time,
                        "status": response.status,
                        "train_id": train_id,
                        "error": error_text
                    }
        
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            self.results["total_requests"] += 1
            self.results["failed_requests"] += 1
            self.results["response_times"].append(response_time)
            self.results["errors"].append({
                "train_id": train_id,
                "error": str(e)
            })
            
            return {
                "success": False,
                "response_time": response_time,
                "train_id": train_id,
                "error": str(e)
            }
    
    async def send_bulk_position_update(self, train_positions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Send bulk position update"""
        bulk_data = {"positions": train_positions}
        
        start_time = time.time()
        
        try:
            async with self.session.post(
                f"{BASE_URL}/api/trains/position/bulk",
                json=bulk_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.token}"
                }
            ) as response:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                
                self.results["total_requests"] += 1
                self.results["response_times"].append(response_time)
                
                if response.status == 200:
                    self.results["successful_requests"] += 1
                    data = await response.json()
                    return {
                        "success": True,
                        "response_time": response_time,
                        "updated_count": data.get("data", {}).get("updated_count", 0)
                    }
                else:
                    self.results["failed_requests"] += 1
                    error_text = await response.text()
                    self.results["errors"].append({
                        "bulk_update": True,
                        "status": response.status,
                        "error": error_text
                    })
                    return {
                        "success": False,
                        "response_time": response_time,
                        "error": error_text
                    }
        
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            
            self.results["total_requests"] += 1
            self.results["failed_requests"] += 1
            self.results["response_times"].append(response_time)
            self.results["errors"].append({
                "bulk_update": True,
                "error": str(e)
            })
            
            return {
                "success": False,
                "response_time": response_time,
                "error": str(e)
            }
    
    async def test_concurrent_position_updates(self):
        """Test concurrent position updates from multiple trains"""
        logger.info(f"🚄 Testing {NUM_TRAINS} concurrent trains with {UPDATES_PER_TRAIN} updates each...")
        
        self.results["start_time"] = time.time()
        
        # Create semaphore to limit concurrent requests
        semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
        
        async def send_train_updates(train_id: int):
            """Send multiple updates for a single train"""
            async with semaphore:
                for update_num in range(UPDATES_PER_TRAIN):
                    section_id = random.randint(1, 20)  # Assuming 20 sections exist
                    result = await self.send_position_update(train_id, section_id)
                    
                    if update_num % 5 == 0:  # Log every 5th update
                        logger.info(f"Train {train_id}: Update {update_num + 1}/{UPDATES_PER_TRAIN} - "
                                  f"{'✅' if result['success'] else '❌'} "
                                  f"({result['response_time']:.1f}ms)")
                    
                    # Small delay between updates from same train
                    await asyncio.sleep(0.1)
        
        # Create tasks for all trains
        tasks = [send_train_updates(train_id) for train_id in range(1, NUM_TRAINS + 1)]
        
        # Execute all tasks concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
        
        self.results["end_time"] = time.time()
        
        logger.info("✅ Concurrent position updates test completed")
    
    async def test_bulk_updates(self):
        """Test bulk position updates"""
        logger.info("📦 Testing bulk position updates...")
        
        # Create bulk updates in batches of 10
        batch_size = 10
        num_batches = NUM_TRAINS // batch_size
        
        for batch_num in range(num_batches):
            start_train_id = batch_num * batch_size + 1
            end_train_id = start_train_id + batch_size
            
            # Generate positions for this batch
            positions = []
            for train_id in range(start_train_id, end_train_id):
                section_id = random.randint(1, 20)
                position = self.generate_train_position(train_id, section_id)
                positions.append(position)
            
            # Send bulk update
            result = await self.send_bulk_position_update(positions)
            
            logger.info(f"Batch {batch_num + 1}/{num_batches}: "
                       f"{'✅' if result['success'] else '❌'} "
                       f"({result['response_time']:.1f}ms)")
            
            # Small delay between batches
            await asyncio.sleep(0.2)
        
        logger.info("✅ Bulk updates test completed")
    
    async def test_sustained_load(self):
        """Test sustained load over time"""
        logger.info(f"⏱️ Testing sustained load for {TEST_DURATION_SECONDS} seconds...")
        
        start_time = time.time()
        update_count = 0
        
        while time.time() - start_time < TEST_DURATION_SECONDS:
            # Send updates for random trains
            tasks = []
            for _ in range(10):  # 10 concurrent updates per iteration
                train_id = random.randint(1, NUM_TRAINS)
                section_id = random.randint(1, 20)
                task = self.send_position_update(train_id, section_id)
                tasks.append(task)
            
            # Execute batch
            await asyncio.gather(*tasks, return_exceptions=True)
            update_count += 10
            
            # Small delay
            await asyncio.sleep(0.5)
        
        logger.info(f"✅ Sustained load test completed: {update_count} updates in {TEST_DURATION_SECONDS}s")
    
    async def test_api_endpoints_performance(self):
        """Test performance of various API endpoints"""
        logger.info("🔍 Testing API endpoints performance...")
        
        endpoints = [
            ("GET", "/api/health", None),
            ("GET", "/api/performance", None),
            ("GET", "/api/trains/1/position", None),
            ("GET", "/api/sections/status", {"Authorization": f"Bearer {self.token}"}),
            ("GET", "/api/trains/1/position/history?hours=1", None),
        ]
        
        for method, endpoint, headers in endpoints:
            start_time = time.time()
            
            try:
                if method == "GET":
                    async with self.session.get(f"{BASE_URL}{endpoint}", headers=headers) as response:
                        end_time = time.time()
                        response_time = (end_time - start_time) * 1000
                        
                        logger.info(f"{method} {endpoint}: "
                                   f"{'✅' if response.status == 200 else '❌'} "
                                   f"({response_time:.1f}ms)")
            
            except Exception as e:
                end_time = time.time()
                response_time = (end_time - start_time) * 1000
                logger.error(f"{method} {endpoint}: ❌ Error ({response_time:.1f}ms) - {e}")
    
    def calculate_statistics(self):
        """Calculate performance statistics"""
        if not self.results["response_times"]:
            return {}
        
        response_times = self.results["response_times"]
        response_times.sort()
        
        total_time = self.results["end_time"] - self.results["start_time"] if self.results["start_time"] else 0
        
        stats = {
            "total_requests": self.results["total_requests"],
            "successful_requests": self.results["successful_requests"],
            "failed_requests": self.results["failed_requests"],
            "success_rate": (self.results["successful_requests"] / self.results["total_requests"] * 100) if self.results["total_requests"] > 0 else 0,
            "total_time_seconds": total_time,
            "requests_per_second": self.results["total_requests"] / total_time if total_time > 0 else 0,
            "response_times": {
                "min": min(response_times),
                "max": max(response_times),
                "mean": sum(response_times) / len(response_times),
                "median": response_times[len(response_times) // 2],
                "p95": response_times[int(len(response_times) * 0.95)],
                "p99": response_times[int(len(response_times) * 0.99)]
            }
        }
        
        return stats
    
    def print_results(self):
        """Print performance test results"""
        stats = self.calculate_statistics()
        
        logger.info("\n" + "="*60)
        logger.info("PERFORMANCE TEST RESULTS")
        logger.info("="*60)
        
        logger.info(f"📊 Request Statistics:")
        logger.info(f"   Total Requests: {stats['total_requests']}")
        logger.info(f"   Successful: {stats['successful_requests']}")
        logger.info(f"   Failed: {stats['failed_requests']}")
        logger.info(f"   Success Rate: {stats['success_rate']:.1f}%")
        
        logger.info(f"\n⏱️ Performance Metrics:")
        logger.info(f"   Total Time: {stats['total_time_seconds']:.1f}s")
        logger.info(f"   Requests/Second: {stats['requests_per_second']:.1f}")
        
        logger.info(f"\n📈 Response Times (ms):")
        logger.info(f"   Min: {stats['response_times']['min']:.1f}")
        logger.info(f"   Max: {stats['response_times']['max']:.1f}")
        logger.info(f"   Mean: {stats['response_times']['mean']:.1f}")
        logger.info(f"   Median: {stats['response_times']['median']:.1f}")
        logger.info(f"   95th Percentile: {stats['response_times']['p95']:.1f}")
        logger.info(f"   99th Percentile: {stats['response_times']['p99']:.1f}")
        
        # Performance assessment
        logger.info(f"\n🎯 Performance Assessment:")
        
        if stats['response_times']['p95'] < 100:
            logger.info("   ✅ Excellent: 95% of requests under 100ms")
        elif stats['response_times']['p95'] < 200:
            logger.info("   ✅ Good: 95% of requests under 200ms")
        elif stats['response_times']['p95'] < 500:
            logger.info("   ⚠️ Acceptable: 95% of requests under 500ms")
        else:
            logger.info("   ❌ Poor: 95% of requests over 500ms")
        
        if stats['success_rate'] >= 99:
            logger.info("   ✅ Excellent reliability: >99% success rate")
        elif stats['success_rate'] >= 95:
            logger.info("   ✅ Good reliability: >95% success rate")
        elif stats['success_rate'] >= 90:
            logger.info("   ⚠️ Acceptable reliability: >90% success rate")
        else:
            logger.info("   ❌ Poor reliability: <90% success rate")
        
        if stats['requests_per_second'] >= 100:
            logger.info("   ✅ High throughput: >100 requests/second")
        elif stats['requests_per_second'] >= 50:
            logger.info("   ✅ Good throughput: >50 requests/second")
        elif stats['requests_per_second'] >= 20:
            logger.info("   ⚠️ Moderate throughput: >20 requests/second")
        else:
            logger.info("   ❌ Low throughput: <20 requests/second")
        
        # Error summary
        if self.results["errors"]:
            logger.info(f"\n❌ Errors ({len(self.results['errors'])}):")
            error_types = {}
            for error in self.results["errors"][:10]:  # Show first 10 errors
                error_key = error.get("status", "unknown")
                error_types[error_key] = error_types.get(error_key, 0) + 1
            
            for error_type, count in error_types.items():
                logger.info(f"   {error_type}: {count} occurrences")
        
        logger.info("="*60)
    
    async def run_all_tests(self):
        """Run all performance tests"""
        logger.info("🚀 Starting Railway Traffic Management API Performance Tests")
        
        try:
            await self.setup()
            
            # Test 1: Concurrent position updates
            await self.test_concurrent_position_updates()
            
            # Test 2: Bulk updates
            await self.test_bulk_updates()
            
            # Test 3: Sustained load
            await self.test_sustained_load()
            
            # Test 4: API endpoints performance
            await self.test_api_endpoints_performance()
            
            # Print results
            self.print_results()
            
            logger.info("🎉 All performance tests completed!")
            
        except Exception as e:
            logger.error(f"❌ Performance test error: {e}")
            raise
        
        finally:
            await self.cleanup()


async def main():
    """Main test function"""
    tester = PerformanceTester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())