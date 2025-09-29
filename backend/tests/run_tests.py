"""
Railway Traffic Management System - Test Suite Runner
Comprehensive testing framework for all system components
"""
import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add the app directory to Python path
current_dir = Path(__file__).parent
backend_dir = current_dir.parent
sys.path.append(str(backend_dir / "app"))

def run_test_category(category: str, verbose: bool = False):
    """Run tests from a specific category"""
    test_dir = current_dir / category
    
    if not test_dir.exists():
        print(f"❌ Test category '{category}' not found")
        return False
    
    print(f"\n🚀 Running {category.upper()} tests...")
    print("=" * 50)
    
    success_count = 0
    total_count = 0
    
    # Find all Python test files
    test_files = list(test_dir.glob("test_*.py"))
    
    if not test_files:
        print(f"⚠️  No test files found in {category}")
        return True
    
    for test_file in test_files:
        total_count += 1
        print(f"\n📋 Running: {test_file.name}")
        
        try:
            # Run the test file
            result = subprocess.run(
                [sys.executable, str(test_file)],
                cwd=str(backend_dir),
                capture_output=not verbose,
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            if result.returncode == 0:
                print(f"✅ {test_file.name}: PASSED")
                success_count += 1
            else:
                print(f"❌ {test_file.name}: FAILED")
                if verbose and result.stderr:
                    print(f"Error output: {result.stderr}")
        
        except subprocess.TimeoutExpired:
            print(f"⏰ {test_file.name}: TIMEOUT")
        except Exception as e:
            print(f"❌ {test_file.name}: ERROR - {e}")
    
    print(f"\n📊 {category.upper()} Results: {success_count}/{total_count} passed")
    return success_count == total_count

def run_all_tests(verbose: bool = False):
    """Run all test categories"""
    print("🚂 Railway Traffic Management System - Full Test Suite")
    print("=" * 60)
    
    categories = ['ai', 'database', 'integration', 'phase2']
    results = {}
    
    for category in categories:
        results[category] = run_test_category(category, verbose)
    
    # API tests (existing)
    print(f"\n🚀 Running API tests...")
    print("=" * 50)
    api_test_file = current_dir / "test_api.py"
    if api_test_file.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(api_test_file)],
                cwd=str(backend_dir),
                capture_output=not verbose,
                text=True,
                timeout=60
            )
            results['api'] = result.returncode == 0
            print(f"{'✅' if results['api'] else '❌'} test_api.py: {'PASSED' if results['api'] else 'FAILED'}")
        except Exception as e:
            results['api'] = False
            print(f"❌ test_api.py: ERROR - {e}")
    else:
        results['api'] = True  # Skip if not found
        print("⚠️  test_api.py not found - skipping")
    
    # Final summary
    print("\n" + "=" * 60)
    print("📋 FINAL TEST RESULTS:")
    print("=" * 60)
    
    passed_categories = sum(1 for success in results.values() if success)
    total_categories = len(results)
    
    for category, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"   {category.upper():12} {status}")
    
    print(f"\n🎯 Overall: {passed_categories}/{total_categories} categories passed")
    
    if passed_categories == total_categories:
        print("🎉 ALL TESTS PASSED! System is ready for production.")
        return True
    else:
        print("⚠️  Some tests failed. Review the output above.")
        return False

def list_tests():
    """List all available tests"""
    print("📋 Available Tests:")
    print("=" * 40)
    
    categories = ['ai', 'database', 'integration', 'phase2']
    
    for category in categories:
        test_dir = current_dir / category
        if test_dir.exists():
            test_files = list(test_dir.glob("test_*.py"))
            print(f"\n📁 {category.upper()}:")
            for test_file in test_files:
                print(f"   - {test_file.name}")
        else:
            print(f"\n📁 {category.upper()}: (no tests)")
    
    # API tests
    api_test_file = current_dir / "test_api.py"
    print(f"\n📁 API:")
    if api_test_file.exists():
        print(f"   - test_api.py")
    else:
        print(f"   - (no tests)")

def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description='Railway Test Suite Runner')
    parser.add_argument('category', nargs='?', 
                       choices=['ai', 'database', 'integration', 'phase2', 'api', 'all'],
                       default='all',
                       help='Test category to run (default: all)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Show detailed output')
    parser.add_argument('-l', '--list', action='store_true',
                       help='List available tests')
    
    args = parser.parse_args()
    
    if args.list:
        list_tests()
        return
    
    if args.category == 'all':
        success = run_all_tests(args.verbose)
    elif args.category == 'api':
        api_test_file = current_dir / "test_api.py"
        if api_test_file.exists():
            result = subprocess.run([sys.executable, str(api_test_file)], cwd=str(backend_dir))
            success = result.returncode == 0
        else:
            print("❌ API test file not found")
            success = False
    else:
        success = run_test_category(args.category, args.verbose)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()