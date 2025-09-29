"""
Test Status Checker
Quick validation of all test files in organized structure
"""
import os
import sys
from pathlib import Path

def check_test_files():
    """Check all test files in organized structure"""
    
    # Setup paths
    current_dir = Path(__file__).parent
    test_categories = ['ai', 'database', 'integration', 'phase2']
    
    print("📊 TEST FILE ORGANIZATION STATUS")
    print("=" * 50)
    
    total_tests = 0
    
    for category in test_categories:
        category_dir = current_dir / category
        
        if category_dir.exists():
            test_files = list(category_dir.glob('test_*.py'))
            print(f"\n📁 {category.upper()} Tests ({len(test_files)} files):")
            
            for test_file in test_files:
                file_size = test_file.stat().st_size
                print(f"   ✅ {test_file.name} ({file_size:,} bytes)")
                total_tests += 1
        else:
            print(f"\n📁 {category.upper()} Tests: ❌ Directory not found")
    
    print(f"\n📈 SUMMARY:")
    print(f"   Total test files: {total_tests}")
    print(f"   Test categories: {len(test_categories)}")
    
    # Check for main test files
    main_files = ['run_tests.py', 'conftest.py', 'README.md']
    print(f"\n🔧 INFRASTRUCTURE FILES:")
    
    for file in main_files:
        file_path = current_dir / file
        if file_path.exists():
            print(f"   ✅ {file}")
        else:
            print(f"   ❌ {file} (missing)")
    
    return total_tests

if __name__ == "__main__":
    check_test_files()
    print(f"\n✨ Test organization complete!")