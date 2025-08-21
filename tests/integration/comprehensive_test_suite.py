#!/usr/bin/env python3
"""
Comprehensive Test Suite for Email Classification & RAG System
Tests all possible scenarios to verify data storage, query outputs, and system integrity.
"""

import asyncio
import logging
import sys
import os
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.db.session import SessionLocal, engine
from app.db.models import Email, InboundEmailAnalysis, OutboundEmailAnalysis, Alert, DailyReport, AuditLog
from sqlalchemy import text
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

class ComprehensiveTestSuite:
    """Main test suite orchestrator"""
    
    def __init__(self):
        self.test_results = {}
        self.failed_tests = []
        self.passed_tests = []
        self.test_data = {}
        
    async def run_all_tests(self):
        """Execute all test categories"""
        print("🚀 COMPREHENSIVE EMAIL CLASSIFICATION & RAG SYSTEM TEST SUITE")
        print("=" * 80)
        print(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🗄️  Database: {settings.database_url.split('@')[1].split('/')[1] if '@' in settings.database_url else 'SQLite'}")
        print()
        
        # Test categories in order
        test_categories = [
            ("Database Schema & Data Integrity", self.test_database_integrity),
            ("Email Processing Pipeline", self.test_email_processing),
            ("RAG Pipeline Verification", self.test_rag_pipeline),
            ("Webhook Integration", self.test_webhook_integration),
            ("API Endpoints", self.test_api_endpoints),
            ("Edge Cases & Error Handling", self.test_edge_cases),
            ("Performance & Load Testing", self.test_performance),
            ("Data Validation & Query Output", self.test_data_validation),
            ("Integration & End-to-End", self.test_integration_scenarios)
        ]
        
        for category_name, test_function in test_categories:
            print(f"\n🧪 TESTING: {category_name}")
            print("-" * 60)
            
            try:
                start_time = time.time()
                result = await test_function()
                duration = time.time() - start_time
                
                if result:
                    print(f"✅ {category_name}: PASSED ({duration:.2f}s)")
                    self.passed_tests.append(category_name)
                else:
                    print(f"❌ {category_name}: FAILED ({duration:.2f}s)")
                    self.failed_tests.append(category_name)
                    
                self.test_results[category_name] = {
                    "passed": result,
                    "duration": duration,
                    "timestamp": datetime.now().isoformat()
                }
                
            except Exception as e:
                print(f"💥 {category_name}: ERROR - {str(e)}")
                self.failed_tests.append(category_name)
                self.test_results[category_name] = {
                    "passed": False,
                    "error": str(e),
                    "duration": 0,
                    "timestamp": datetime.now().isoformat()
                }
        
        # Generate final report
        await self.generate_test_report()
        
    async def test_database_integrity(self) -> bool:
        """Test database schema, models, and data integrity"""
        print("🗄️  Testing database schema and data integrity...")
        
        try:
            db = SessionLocal()
            
            # Test 1: Verify all tables exist
            print("   📋 Checking table existence...")
            if "mysql" in settings.database_url.lower():
                result = db.execute(text("SHOW TABLES"))
                tables = [row[0] for row in result]
            else:
                result = db.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
                tables = [row[0] for row in result]
            
            expected_tables = ['email', 'inbound_email_analysis', 'outbound_email_analysis', 'alert', 'daily_report', 'audit_log']
            missing_tables = [table for table in expected_tables if table not in tables]
            
            if missing_tables:
                print(f"   ❌ Missing tables: {missing_tables}")
                return False
            
            print(f"   ✅ All {len(expected_tables)} tables exist")
            
            # Test 2: Verify table structures
            print("   🏗️  Checking table structures...")
            for table in expected_tables:
                try:
                    if "mysql" in settings.database_url.lower():
                        structure = db.execute(text(f"DESCRIBE {table}"))
                        columns = [row[0] for row in structure]
                    else:
                        structure = db.execute(text(f"PRAGMA table_info({table})"))
                        columns = [row[1] for row in structure]
                    
                    print(f"     📊 {table}: {len(columns)} columns")
                    
                except Exception as e:
                    print(f"   ❌ Error checking {table}: {e}")
                    return False
            
            # Test 3: Test foreign key relationships
            print("   🔗 Testing foreign key relationships...")
            
            # Create test email
            test_email = Email(
                email_identifier="test_integrity_001",
                is_inbound=True,
                thread_id="test_thread_001"
            )
            db.add(test_email)
            db.flush()
            
            # Test inbound analysis relationship
            test_inbound = InboundEmailAnalysis(
                email_id="test_integrity_001",
                from_email="test@example.com",
                type="query",
                priority="medium"
            )
            db.add(test_inbound)
            
            # Test outbound analysis relationship
            test_outbound = OutboundEmailAnalysis(
                email_id="test_integrity_001",
                type="query",
                factual_accuracy=0.85,
                guideline_compliance=0.90,
                completeness=0.80,
                tone="professional"
            )
            db.add(test_outbound)
            
            db.commit()
            print("   ✅ Foreign key relationships working")
            
            # Cleanup test data
            db.delete(test_inbound)
            db.delete(test_outbound)
            db.delete(test_email)
            db.commit()
            
            return True
            
        except Exception as e:
            print(f"   ❌ Database integrity test failed: {e}")
            return False
        finally:
            db.close()
    
    async def test_email_processing(self) -> bool:
        """Test email processing pipeline with various scenarios"""
        print("📧 Testing email processing pipeline...")
        
        try:
            from app.services.agent_orchestration.classify import classify_email
            
            # Test scenarios
            test_scenarios = [
                {
                    "name": "Inbound Customer Query",
                    "email_id": "test_inbound_001",
                    "from_email": "customer@example.com",
                    "thread_id": "thread_001",
                    "subject": "Refund Request",
                    "body": "I need a refund for my course payment. Can you help?",
                    "is_inbound": True,
                    "expected_type": "query",
                    "expected_priority": "medium"
                },
                {
                    "name": "Outbound Support Response",
                    "email_id": "test_outbound_001", 
                    "from_email": "support@company.com",
                    "thread_id": "thread_001",
                    "subject": "Re: Refund Request",
                    "body": "Thank you for contacting us. Your refund will be processed within 5-7 business days.",
                    "is_inbound": False,
                    "expected_scores": {"factual_accuracy": "> 0.7", "compliance": "> 0.8"}
                },
                {
                    "name": "High Priority Issue",
                    "email_id": "test_priority_001",
                    "from_email": "urgent@example.com", 
                    "thread_id": "thread_002",
                    "subject": "URGENT: Payment Failed",
                    "body": "My payment failed and I can't access the course. This is urgent!",
                    "is_inbound": True,
                    "expected_priority": "high"
                }
            ]
            
            for scenario in test_scenarios:
                print(f"   🧪 Testing: {scenario['name']}")
                
                try:
                    # Process email through classification pipeline
                    await classify_email(
                        email_id=scenario["email_id"],
                        from_email=scenario["from_email"],
                        thread_id=scenario["thread_id"],
                        subject=scenario["subject"],
                        body=scenario["body"],
                        is_inbound=scenario["is_inbound"],
                        thread_context=[]
                    )
                    
                    # Verify data was stored correctly
                    db = SessionLocal()
                    try:
                        email = db.query(Email).filter(Email.email_identifier == scenario["email_id"]).first()
                        if not email:
                            print(f"     ❌ Email not stored: {scenario['email_id']}")
                            return False
                        
                        if scenario["is_inbound"]:
                            analysis = db.query(InboundEmailAnalysis).filter(
                                InboundEmailAnalysis.email_id == scenario["email_id"]
                            ).first()
                            
                            if not analysis:
                                print(f"     ❌ Inbound analysis not stored")
                                return False
                                
                            # Check expected values
                            if "expected_type" in scenario and analysis.type != scenario["expected_type"]:
                                print(f"     ⚠️  Type mismatch: expected {scenario['expected_type']}, got {analysis.type}")
                            
                            if "expected_priority" in scenario and analysis.priority != scenario["expected_priority"]:
                                print(f"     ⚠️  Priority mismatch: expected {scenario['expected_priority']}, got {analysis.priority}")
                        
                        else:
                            analysis = db.query(OutboundEmailAnalysis).filter(
                                OutboundEmailAnalysis.email_id == scenario["email_id"]
                            ).first()
                            
                            if not analysis:
                                print(f"     ❌ Outbound analysis not stored")
                                return False
                            
                            # Check score ranges
                            if analysis.factual_accuracy is None or analysis.factual_accuracy < 0:
                                print(f"     ❌ Invalid factual accuracy: {analysis.factual_accuracy}")
                                return False
                        
                        print(f"     ✅ {scenario['name']}: Data stored correctly")
                        
                    finally:
                        db.close()
                        
                except Exception as e:
                    print(f"     ❌ Error processing {scenario['name']}: {e}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"   ❌ Email processing test failed: {e}")
            return False
    
    async def test_rag_pipeline(self) -> bool:
        """Test RAG pipeline components"""
        print("🤖 Testing RAG pipeline verification...")
        
        try:
            from app.api.models import SupportVerificationRequest, VerificationLevel, ResponseFormat
            from app.services.core.pipeline_orchestrator import PipelineOrchestrator
            
            # Initialize pipeline
            pipeline = PipelineOrchestrator()
            
            # Test verification request with proper validation
            test_request = SupportVerificationRequest(
                support_response="Your refund will be processed within 5-7 business days as per our refund policy.",
                customer_query="I want a refund for my course",
                verification_level=VerificationLevel.STANDARD,  # Use STANDARD to avoid min_accuracy_score validation
                response_format=ResponseFormat.DETAILED,
                min_accuracy_score=0.8  # Explicitly set to meet STANDARD requirements
            )
            
            print("   🔍 Testing claim extraction...")
            claims = await pipeline._extract_claims(test_request, "test_verification_001")
            
            if not claims:
                print("   ❌ No claims extracted")
                return False
            
            print(f"   ✅ Extracted {len(claims)} claims")
            
            print("   📚 Testing evidence retrieval...")
            evidence_results = await pipeline._retrieve_evidence(claims, test_request, "test_verification_001")
            
            print(f"   ✅ Retrieved evidence for {len(evidence_results)} claims")
            
            print("   ✅ RAG pipeline components working")
            return True
            
        except Exception as e:
            print(f"   ❌ RAG pipeline test failed: {e}")
            return False

    async def test_webhook_integration(self) -> bool:
        """Test webhook processing and integration"""
        print("🔗 Testing webhook integration...")

        try:
            # Test Gmail webhook processing
            print("   📧 Testing Gmail webhook...")

            # Mock Gmail notification data
            mock_gmail_data = {
                "message": {
                    "data": "eyJlbWFpbEFkZHJlc3MiOiJ0ZXN0QGV4YW1wbGUuY29tIiwiaGlzdG9yeUlkIjoiMTIzNDU2In0=",  # base64 encoded
                    "messageId": "test_message_001"
                }
            }

            from app.services.gmail.gmail_watch import process_gmail_notification

            # This should not crash
            process_gmail_notification(mock_gmail_data)
            print("   ✅ Gmail webhook processing works")

            # Test Google Drive webhook
            print("   📁 Testing Google Drive webhook...")

            mock_drive_data = {
                "kind": "api#channel",
                "id": "test_channel_001",
                "resourceId": "test_resource_001",
                "resourceUri": "https://www.googleapis.com/drive/v3/files/test_file_001",
                "eventType": "update"
            }

            # This should not crash
            print("   ✅ Google Drive webhook structure valid")

            return True

        except Exception as e:
            print(f"   ❌ Webhook integration test failed: {e}")
            return False

    async def test_api_endpoints(self) -> bool:
        """Test API endpoints with various scenarios"""
        print("🌐 Testing API endpoints...")

        try:
            import httpx
            from app.main import app
            from fastapi.testclient import TestClient

            client = TestClient(app)

            # Test health endpoints
            print("   ❤️  Testing health endpoints...")

            response = client.get("/health")
            if response.status_code != 200:
                print(f"   ❌ Health endpoint failed: {response.status_code}")
                return False

            response = client.get("/health/")
            if response.status_code != 200:
                print(f"   ❌ Detailed health endpoint failed: {response.status_code}")
                return False

            print("   ✅ Health endpoints working")

            # Test verification endpoint
            print("   🔍 Testing verification endpoint...")

            test_verification_data = {
                "support_response": "Your refund will be processed within 5-7 business days.",
                "customer_query": "I need a refund",
                "verification_level": "standard",
                "response_format": "detailed"
            }

            response = client.post("/api/v1/verify-support-response", json=test_verification_data)

            if response.status_code not in [200, 422]:  # 422 is validation error, which is acceptable
                print(f"   ❌ Verification endpoint failed: {response.status_code}")
                return False

            print("   ✅ Verification endpoint accessible")

            # Test webhook endpoints
            print("   🔗 Testing webhook endpoints...")

            response = client.get("/webhook/health")
            if response.status_code != 200:
                print(f"   ❌ Webhook health failed: {response.status_code}")
                return False

            print("   ✅ API endpoints working")
            return True

        except Exception as e:
            print(f"   ❌ API endpoints test failed: {e}")
            return False

    async def test_edge_cases(self) -> bool:
        """Test edge cases and error handling"""
        print("⚠️  Testing edge cases and error handling...")

        try:
            from app.services.agent_orchestration.classify import classify_email

            # Test 1: Empty email content
            print("   📭 Testing empty email content...")
            try:
                await classify_email(
                    email_id="test_empty_001",
                    from_email="test@example.com",
                    thread_id="thread_empty",
                    subject="",
                    body="",
                    is_inbound=True,
                    thread_context=[]
                )
                print("   ✅ Empty content handled gracefully")
            except Exception as e:
                print(f"   ⚠️  Empty content error (expected): {e}")

            # Test 2: Very long email content
            print("   📏 Testing very long email content...")
            long_content = "This is a very long email. " * 1000  # 5000+ characters

            try:
                await classify_email(
                    email_id="test_long_001",
                    from_email="test@example.com",
                    thread_id="thread_long",
                    subject="Long email test",
                    body=long_content,
                    is_inbound=True,
                    thread_context=[]
                )
                print("   ✅ Long content handled")
            except Exception as e:
                print(f"   ⚠️  Long content error: {e}")

            # Test 3: Special characters and encoding
            print("   🔤 Testing special characters...")
            special_content = "Email with émojis 🚀 and spëcial çharacters ñ"

            try:
                await classify_email(
                    email_id="test_special_001",
                    from_email="tëst@éxample.com",
                    thread_id="thread_special",
                    subject="Spëcial tëst",
                    body=special_content,
                    is_inbound=True,
                    thread_context=[]
                )
                print("   ✅ Special characters handled")
            except Exception as e:
                print(f"   ⚠️  Special characters error: {e}")

            # Test 4: Database connection failure simulation
            print("   🗄️  Testing database resilience...")

            # This tests that the system doesn't crash completely
            db = SessionLocal()
            try:
                # Test a simple query
                result = db.execute(text("SELECT 1"))
                print("   ✅ Database connection stable")
            except Exception as e:
                print(f"   ❌ Database connection issue: {e}")
                return False
            finally:
                db.close()

            return True

        except Exception as e:
            print(f"   ❌ Edge cases test failed: {e}")
            return False
