#!/usr/bin/env python3
"""
Run REAL Comprehensive Tests
Executes the actual comprehensive test runner with real code validation.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from comprehensive_test_runner import ComprehensiveTestRunner

async def main():
    """Run the real comprehensive tests"""
    print("🚀 STARTING REAL COMPREHENSIVE TESTS")
    print("=" * 80)
    print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    print("⚠️  IMPORTANT: This will execute REAL code with:")
    print("   🤖 Real OpenAI API calls (will consume credits)")
    print("   💾 Real database operations (will create/delete test data)")
    print("   🔍 Real Qdrant vector searches")
    print("   🌐 Real HTTP requests to your server")
    print()
    
    # Confirm execution
    try:
        confirm = input("Continue with REAL tests? (yes/no): ").strip().lower()
        if confirm not in ['yes', 'y']:
            print("❌ Tests cancelled by user")
            return
    except KeyboardInterrupt:
        print("\n❌ Tests cancelled by user")
        return
    
    print("\n🔄 Initializing comprehensive test runner...")
    
    # Create and run the test runner
    runner = ComprehensiveTestRunner()
    
    try:
        # Execute all real tests
        report = await runner.run_all_tests()
        
        # Display results
        print("\n" + "="*80)
        print("🎉 REAL COMPREHENSIVE TESTS COMPLETED")
        print("="*80)
        
        execution_summary = report.get('execution_summary', {})
        print(f"📊 RESULTS SUMMARY:")
        print(f"   Status: {report.get('status', 'UNKNOWN')}")
        print(f"   Total Tests: {execution_summary.get('total_tests', 0)}")
        print(f"   Passed: {execution_summary.get('total_passed', 0)}")
        print(f"   Failed: {execution_summary.get('total_failed', 0)}")
        print(f"   Success Rate: {execution_summary.get('success_rate_percent', 0):.1f}%")
        print(f"   Execution Time: {execution_summary.get('execution_time_seconds', 0):.2f} seconds")
        
        # Category breakdown
        print(f"\n📋 CATEGORY BREAKDOWN:")
        category_results = report.get('category_results', {})
        for category, results in category_results.items():
            passed = results.get('passed', 0)
            failed = results.get('failed', 0)
            total = passed + failed
            if total > 0:
                success_rate = (passed / total * 100)
                status_icon = "✅" if failed == 0 else "⚠️" if success_rate >= 80 else "❌"
                print(f"   {status_icon} {category.replace('_', ' ').title()}: {passed}/{total} ({success_rate:.1f}%)")
        
        # Show failures if any
        total_failed = execution_summary.get('total_failed', 0)
        if total_failed > 0:
            print(f"\n❌ FAILURE DETAILS:")
            for category, results in category_results.items():
                if results.get('failed', 0) > 0:
                    print(f"\n   {category.replace('_', ' ').title()} Failures:")
                    for detail in results.get('details', []):
                        if not detail.get('success', True):
                            test_id = detail.get('test_id', 'unknown')
                            error = detail.get('details', {}).get('error', 'Unknown error')
                            print(f"     - {test_id}: {error}")
        
        # Report file location
        print(f"\n📄 Detailed report saved to:")
        print(f"   tests/docs/test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        
        # Recommendations
        success_rate = execution_summary.get('success_rate_percent', 0)
        print(f"\n💡 RECOMMENDATIONS:")
        if success_rate >= 95:
            print("   🎉 Excellent! Your system is production-ready.")
        elif success_rate >= 85:
            print("   ✅ Good! Address the failed tests before production deployment.")
        elif success_rate >= 70:
            print("   ⚠️  Needs improvement. Several issues need to be fixed.")
        else:
            print("   ❌ Critical issues found. System needs significant fixes.")
        
        print(f"\n🔧 NEXT STEPS:")
        if total_failed > 0:
            print("   1. Review failure details above")
            print("   2. Fix the identified issues")
            print("   3. Re-run tests to verify fixes")
            print("   4. Check the detailed JSON report for more information")
        else:
            print("   1. Your system passed all tests!")
            print("   2. Consider running tests regularly")
            print("   3. Monitor performance metrics")
            print("   4. Keep test data updated with new features")
        
        print("="*80)
        
        # Exit with appropriate code
        if report.get('status') == 'PASSED':
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n❌ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        print("🔧 Check your system configuration:")
        print("   - Is the FastAPI server running on port 5001?")
        print("   - Are your API keys configured correctly?")
        print("   - Is the database accessible?")
        print("   - Are all dependencies installed?")
        sys.exit(1)

def check_prerequisites():
    """Check if prerequisites are met before running tests"""
    print("🔍 Checking prerequisites...")
    
    issues = []
    
    # Check if server is running
    try:
        import requests
        response = requests.get("http://localhost:5001/health", timeout=5)
        if response.status_code != 200:
            issues.append("FastAPI server not responding properly")
    except Exception:
        issues.append("FastAPI server not running on port 5001")
    
    # Check environment variables
    required_env_vars = ['OPENAI_API_KEY', 'DATABASE_URL', 'QDRANT_API_KEY']
    for var in required_env_vars:
        if not os.getenv(var):
            issues.append(f"Missing environment variable: {var}")
    
    # Check database connection
    try:
        from app.db.session import SessionLocal
        from sqlalchemy import text
        db = SessionLocal()
        db.execute(text("SELECT 1")).fetchone()
        db.close()
    except Exception as e:
        issues.append(f"Database connection failed: {e}")
    
    if issues:
        print("❌ Prerequisites not met:")
        for issue in issues:
            print(f"   - {issue}")
        print("\n🔧 Please fix these issues before running tests.")
        return False
    
    print("✅ All prerequisites met!")
    return True

if __name__ == "__main__":
    print("🧪 REAL COMPREHENSIVE TEST EXECUTION")
    print("This script will execute actual code with real API calls and database operations.")
    print()
    
    # Check prerequisites first
    if not check_prerequisites():
        sys.exit(1)
    
    # Run the tests
    asyncio.run(main())
