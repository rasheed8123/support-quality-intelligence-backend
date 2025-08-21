#!/usr/bin/env python3
"""
Daily Reports Test Script
Test the daily report generation functionality.
"""

import sys
import os
import asyncio
from datetime import datetime, date, timedelta

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.analytics.daily_report_generator import (
    generate_daily_report,
    get_admin_report_text,
    DailyReportGenerator
)
from app.db.session import SessionLocal

async def test_daily_report_generation():
    """Test daily report generation for yesterday's data"""
    
    print("🧪 Daily Report Generation Test")
    print("=" * 50)
    
    # Test date (yesterday)
    test_date = datetime.utcnow().date() - timedelta(days=1)
    print(f"📅 Testing report generation for: {test_date}")
    
    try:
        # Test 1: Generate complete report
        print("\n🔄 Test 1: Generating complete daily report...")
        result = await generate_daily_report(test_date)
        
        if result['success']:
            print("✅ Report generation successful!")
            print(f"📊 Metrics calculated: {len(result['metrics'])} fields")
            
            # Show key metrics
            metrics = result['metrics']
            print(f"📧 Total emails: {metrics.get('total_emails', 0)}")
            print(f"📊 Queries: {metrics.get('queries_count', 0)}")
            print(f"🎯 High priority: {metrics.get('high_priority_count', 0)}")
            print(f"📈 Response rate: {metrics.get('overall_response_rate', 0)}%")
            print(f"😊 Tone score: {metrics.get('tone_score_avg', 0)}/10")
            print(f"🚨 Alerts: {metrics.get('alerts_count', 0)}")
        else:
            print("❌ Report generation failed!")
            return False
        
        # Test 2: Get formatted admin report
        print("\n🔄 Test 2: Getting formatted admin report...")
        admin_report = await get_admin_report_text(test_date)
        
        if admin_report and "Support Performance" in admin_report:
            print("✅ Admin report formatting successful!")
            print("\n📋 Admin Report Preview:")
            print("-" * 40)
            # Show first 10 lines
            lines = admin_report.split('\n')[:10]
            for line in lines:
                print(line)
            print("...")
            print(f"📄 Total lines: {len(admin_report.split('\n'))}")
        else:
            print("❌ Admin report formatting failed!")
            return False
        
        # Test 3: Test individual components
        print("\n🔄 Test 3: Testing individual components...")
        generator = DailyReportGenerator(test_date)
        
        # Test volume metrics
        generator.db = generator.db or SessionLocal()
        try:
            await generator._calculate_volume_metrics()
            print(f"✅ Volume metrics: {generator.metrics.get('total_emails', 0)} emails")
            
            await generator._calculate_priority_breakdown()
            print(f"✅ Priority breakdown: H:{generator.metrics.get('high_priority_count', 0)}, M:{generator.metrics.get('medium_priority_count', 0)}, L:{generator.metrics.get('low_priority_count', 0)}")
            
            await generator._calculate_response_metrics()
            print(f"✅ Response metrics: {generator.metrics.get('overall_response_rate', 0)}% rate")
            
            await generator._calculate_quality_metrics()
            print(f"✅ Quality metrics: {generator.metrics.get('tone_score_avg', 0)}/10 tone")
            
        finally:
            if generator.db:
                generator.db.close()
        
        print("\n🎉 All tests passed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

async def test_api_endpoints():
    """Test API endpoints (requires server to be running)"""
    
    print("\n🌐 API Endpoints Test")
    print("=" * 30)
    
    try:
        import httpx
        
        base_url = "http://localhost:5000"
        test_date = datetime.utcnow().date() - timedelta(days=1)
        
        async with httpx.AsyncClient() as client:
            # Test health endpoint
            print("🔄 Testing /reports/health...")
            response = await client.get(f"{base_url}/reports/health")
            if response.status_code == 200:
                print("✅ Health endpoint working")
                health_data = response.json()
                print(f"📊 Total reports in DB: {health_data.get('total_reports', 0)}")
            else:
                print(f"❌ Health endpoint failed: {response.status_code}")
            
            # Test report generation
            print(f"🔄 Testing report generation for {test_date}...")
            response = await client.post(f"{base_url}/reports/generate/now?target_date={test_date}")
            if response.status_code == 200:
                print("✅ Report generation endpoint working")
            else:
                print(f"❌ Report generation failed: {response.status_code}")
            
            # Test admin report
            print(f"🔄 Testing admin report for {test_date}...")
            response = await client.get(f"{base_url}/reports/admin/{test_date}")
            if response.status_code == 200:
                print("✅ Admin report endpoint working")
                print(f"📄 Report length: {len(response.text)} characters")
            else:
                print(f"❌ Admin report failed: {response.status_code}")
        
        print("🎉 API tests completed!")
        
    except ImportError:
        print("⚠️ httpx not installed, skipping API tests")
        print("💡 Install with: pip install httpx")
    except Exception as e:
        print(f"❌ API tests failed: {str(e)}")

async def show_sample_report():
    """Show a sample report for demonstration"""
    
    print("\n📋 Sample Daily Report")
    print("=" * 40)
    
    try:
        test_date = datetime.utcnow().date() - timedelta(days=1)
        admin_report = await get_admin_report_text(test_date)
        
        print(admin_report)
        
    except Exception as e:
        print(f"❌ Error showing sample report: {str(e)}")

async def main():
    """Main test function"""
    
    print("🚀 Daily Reports System Test Suite")
    print("=" * 60)
    
    # Test 1: Core functionality
    success = await test_daily_report_generation()
    
    if success:
        # Test 2: API endpoints (if server is running)
        await test_api_endpoints()
        
        # Test 3: Show sample report
        await show_sample_report()
        
        print("\n✅ All tests completed successfully!")
        print("\n💡 Next steps:")
        print("   1. Check the database for stored reports")
        print("   2. Test the API endpoints at http://localhost:5000/docs")
        print("   3. Set up scheduled report generation")
        
    else:
        print("\n❌ Tests failed. Please check the errors above.")
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
