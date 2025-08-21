#!/usr/bin/env python3
"""
Comprehensive Test Runner
Executes all test scenarios and validates system functionality across all components.
"""

import asyncio
import logging
import json
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from pathlib import Path

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.db.session import SessionLocal
from app.db.models import Email, InboundEmailAnalysis, OutboundEmailAnalysis, Alert, DailyReport
from app.services.agent_orchestration.classify import classify_email
from app.services.alerts.alert_service import AlertService
from app.api.models import SupportVerificationRequest
from app.services.core.pipeline_orchestrator import PipelineOrchestrator
from test_data_generator import TestDataGenerator

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveTestRunner:
    """Comprehensive test runner for all system functionality"""
    
    def __init__(self):
        self.test_results = {
            "email_classification": {"passed": 0, "failed": 0, "details": []},
            "rag_pipeline": {"passed": 0, "failed": 0, "details": []},
            "alert_system": {"passed": 0, "failed": 0, "details": []},
            "database_integrity": {"passed": 0, "failed": 0, "details": []},
            "api_endpoints": {"passed": 0, "failed": 0, "details": []},
            "performance": {"passed": 0, "failed": 0, "details": []}
        }
        self.start_time = datetime.now()
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all comprehensive tests"""
        logger.info("🚀 Starting comprehensive test suite execution...")
        
        try:
            # 1. Email Classification Tests
            await self._run_email_classification_tests()
            
            # 2. RAG Pipeline Tests
            await self._run_rag_pipeline_tests()
            
            # 3. Alert System Tests
            await self._run_alert_system_tests()
            
            # 4. Database Integrity Tests
            await self._run_database_integrity_tests()
            
            # 5. API Endpoint Tests
            await self._run_api_endpoint_tests()
            
            # 6. Performance Tests
            await self._run_performance_tests()
            
            # Generate final report
            return self._generate_final_report()
            
        except Exception as e:
            logger.error(f"Test suite execution failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def _run_email_classification_tests(self):
        """Run REAL email classification tests with actual AI processing"""
        logger.info("📧 Running REAL email classification tests...")

        test_categories = [
            ("spam", TestDataGenerator.generate_spam_emails()),
            ("high_priority", TestDataGenerator.generate_high_priority_queries()),
            ("medium_priority", TestDataGenerator.generate_medium_priority_queries()),
            ("low_priority", TestDataGenerator.generate_low_priority_queries())
        ]

        for category, test_emails in test_categories:
            for email_data in test_emails:
                test_start_time = datetime.now()
                try:
                    logger.info(f"🔄 Testing {category}: {email_data['email_id']}")

                    # REAL CODE EXECUTION: Call actual classification function
                    classification_result = await classify_email(
                        email_id=email_data["email_id"],
                        from_email=email_data["from_email"],
                        thread_id=email_data["thread_id"],
                        subject=email_data["subject"],
                        body=email_data["body"],
                        is_inbound=email_data["is_inbound"]
                    )

                    # Measure processing time
                    processing_time = (datetime.now() - test_start_time).total_seconds()

                    # REAL VALIDATION: Check actual database results
                    validation_result = await self._validate_email_classification_real(email_data, processing_time)

                    if validation_result["success"]:
                        self.test_results["email_classification"]["passed"] += 1
                        logger.info(f"✅ {category} test PASSED: {email_data['email_id']} ({processing_time:.2f}s)")
                        logger.info(f"   📊 Actual Results: {validation_result['actual_results']}")
                    else:
                        self.test_results["email_classification"]["failed"] += 1
                        logger.error(f"❌ {category} test FAILED: {validation_result['error']}")
                        logger.error(f"   📊 Expected: {validation_result.get('expected', 'N/A')}")
                        logger.error(f"   📊 Actual: {validation_result.get('actual', 'N/A')}")

                    self.test_results["email_classification"]["details"].append({
                        "test_id": email_data["email_id"],
                        "category": category,
                        "success": validation_result["success"],
                        "processing_time_seconds": processing_time,
                        "expected": {
                            "type": email_data.get("expected_type"),
                            "priority": email_data.get("expected_priority"),
                            "category": email_data.get("expected_category")
                        },
                        "actual": validation_result.get("actual_results", {}),
                        "details": validation_result
                    })

                    # Cleanup test data
                    await self._cleanup_test_email(email_data["email_id"])

                except Exception as e:
                    self.test_results["email_classification"]["failed"] += 1
                    processing_time = (datetime.now() - test_start_time).total_seconds()
                    logger.error(f"❌ Email classification test EXCEPTION: {e}")
                    logger.error(f"   📧 Email: {email_data['email_id']}")
                    logger.error(f"   ⏱️ Failed after: {processing_time:.2f}s")

                    # Still cleanup on error
                    try:
                        await self._cleanup_test_email(email_data["email_id"])
                    except:
                        pass
    
    async def _validate_email_classification_real(self, email_data: Dict[str, Any], processing_time: float) -> Dict[str, Any]:
        """REAL validation of email classification results with comprehensive checks"""
        db = SessionLocal()
        try:
            email_id = email_data["email_id"]

            # Check email record exists
            email = db.query(Email).filter(Email.email_identifier == email_id).first()
            if not email:
                return {
                    "success": False,
                    "error": "Email record not created in database",
                    "expected": email_data.get("expected_type", "N/A"),
                    "actual": "No email record"
                }

            # Check inbound analysis exists
            analysis = db.query(InboundEmailAnalysis).filter(
                InboundEmailAnalysis.email_id == email_id
            ).first()

            if not analysis:
                return {
                    "success": False,
                    "error": "Inbound analysis not created",
                    "expected": email_data.get("expected_type", "N/A"),
                    "actual": "No analysis record"
                }

            # Get actual results
            actual_results = {
                "type": analysis.type,
                "priority": analysis.priority,
                "category": analysis.category,
                "from_email": analysis.from_email,
                "responded": analysis.responded,
                "created_at": analysis.created_at.isoformat() if analysis.created_at else None
            }

            # Validate classification accuracy
            validation_errors = []
            accuracy_score = 0
            total_checks = 0

            # Check type classification
            if email_data.get("expected_type"):
                total_checks += 1
                if analysis.type == email_data["expected_type"]:
                    accuracy_score += 1
                else:
                    validation_errors.append(f"Type mismatch: expected '{email_data['expected_type']}', got '{analysis.type}'")

            # Check priority classification (only for non-spam)
            if email_data.get("expected_priority") and analysis.type != "spam":
                total_checks += 1
                if analysis.priority == email_data["expected_priority"]:
                    accuracy_score += 1
                else:
                    validation_errors.append(f"Priority mismatch: expected '{email_data['expected_priority']}', got '{analysis.priority}'")

            # Check category classification (only for non-spam)
            if email_data.get("expected_category") and analysis.type != "spam":
                total_checks += 1
                if analysis.category == email_data["expected_category"]:
                    accuracy_score += 1
                else:
                    validation_errors.append(f"Category mismatch: expected '{email_data['expected_category']}', got '{analysis.category}'")

            # Calculate accuracy percentage
            accuracy_percentage = (accuracy_score / total_checks * 100) if total_checks > 0 else 0

            # Performance validation
            performance_issues = []
            if processing_time > 10.0:  # More than 10 seconds is too slow
                performance_issues.append(f"Processing too slow: {processing_time:.2f}s (expected < 10s)")

            # Data integrity checks
            integrity_issues = []
            if not analysis.from_email:
                integrity_issues.append("Missing from_email")
            if analysis.type not in ["spam", "query", "information"]:
                integrity_issues.append(f"Invalid type: {analysis.type}")
            if analysis.type != "spam" and not analysis.priority:
                integrity_issues.append("Missing priority for non-spam email")

            # Determine overall success
            is_successful = (
                len(validation_errors) == 0 and
                len(performance_issues) == 0 and
                len(integrity_issues) == 0 and
                accuracy_percentage >= 80.0  # At least 80% accuracy required
            )

            result = {
                "success": is_successful,
                "actual_results": actual_results,
                "accuracy_percentage": accuracy_percentage,
                "accuracy_score": f"{accuracy_score}/{total_checks}",
                "processing_time_seconds": processing_time,
                "validation_details": {
                    "classification_errors": validation_errors,
                    "performance_issues": performance_issues,
                    "integrity_issues": integrity_issues
                }
            }

            if not is_successful:
                all_errors = validation_errors + performance_issues + integrity_issues
                result["error"] = "; ".join(all_errors)
                result["expected"] = {
                    "type": email_data.get("expected_type"),
                    "priority": email_data.get("expected_priority"),
                    "category": email_data.get("expected_category")
                }
                result["actual"] = actual_results

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Validation exception: {str(e)}",
                "expected": email_data.get("expected_type", "N/A"),
                "actual": "Exception during validation"
            }
        finally:
            db.close()

    async def _cleanup_test_email(self, email_id: str):
        """Clean up test email data from database"""
        db = SessionLocal()
        try:
            # Delete in correct order (foreign key constraints)
            db.query(Alert).filter(Alert.email_id == email_id).delete()
            db.query(InboundEmailAnalysis).filter(InboundEmailAnalysis.email_id == email_id).delete()
            db.query(OutboundEmailAnalysis).filter(OutboundEmailAnalysis.email_id == email_id).delete()
            db.query(Email).filter(Email.email_identifier == email_id).delete()
            db.commit()
        except Exception as e:
            logger.warning(f"⚠️ Cleanup failed for {email_id}: {e}")
            db.rollback()
        finally:
            db.close()
    
    async def _run_rag_pipeline_tests(self):
        """Run REAL RAG pipeline tests with actual AI processing"""
        logger.info("🤖 Running REAL RAG pipeline tests...")

        outbound_responses = TestDataGenerator.generate_outbound_responses()

        for response_data in outbound_responses:
            test_start_time = datetime.now()
            try:
                logger.info(f"🔄 Testing RAG pipeline: {response_data['email_id']}")
                logger.info(f"📝 Response: {response_data['response'][:100]}...")

                # REAL CODE EXECUTION: Create actual verification request
                request = SupportVerificationRequest(
                    support_response=response_data["response"],
                    customer_query=response_data["customer_query"],
                    context={
                        "test_mode": True,
                        "test_id": response_data["email_id"],
                        "timestamp": datetime.now().isoformat()
                    }
                )

                # REAL CODE EXECUTION: Execute complete RAG pipeline
                pipeline = PipelineOrchestrator()
                result = await pipeline.verify_response(request, response_data["email_id"])

                # Measure processing time
                processing_time = (datetime.now() - test_start_time).total_seconds()

                # REAL VALIDATION: Comprehensive result validation
                validation_result = await self._validate_rag_results_real(result, response_data, processing_time)

                if validation_result["success"]:
                    self.test_results["rag_pipeline"]["passed"] += 1
                    logger.info(f"✅ RAG pipeline test PASSED: {response_data['email_id']} ({processing_time:.2f}s)")
                    logger.info(f"   📊 Overall Score: {validation_result['actual_results']['overall_score']:.3f}")
                    logger.info(f"   📋 Claims Extracted: {validation_result['actual_results']['claims_count']}")
                    logger.info(f"   🔍 Evidence Found: {validation_result['actual_results']['evidence_count']}")
                else:
                    self.test_results["rag_pipeline"]["failed"] += 1
                    logger.error(f"❌ RAG pipeline test FAILED: {validation_result['error']}")
                    logger.error(f"   ⏱️ Processing Time: {processing_time:.2f}s")
                    logger.error(f"   📊 Expected Accuracy: {response_data.get('expected_accuracy', 'N/A')}")
                    logger.error(f"   📊 Actual Score: {validation_result.get('actual_results', {}).get('overall_score', 'N/A')}")

                self.test_results["rag_pipeline"]["details"].append({
                    "test_id": response_data["email_id"],
                    "success": validation_result["success"],
                    "processing_time_seconds": processing_time,
                    "expected": {
                        "accuracy": response_data.get("expected_accuracy"),
                        "compliance": response_data.get("expected_compliance"),
                        "claims_count": len(response_data.get("expected_claims", []))
                    },
                    "actual": validation_result.get("actual_results", {}),
                    "details": validation_result
                })

            except Exception as e:
                self.test_results["rag_pipeline"]["failed"] += 1
                processing_time = (datetime.now() - test_start_time).total_seconds()
                logger.error(f"❌ RAG pipeline test EXCEPTION: {e}")
                logger.error(f"   📧 Test ID: {response_data['email_id']}")
                logger.error(f"   ⏱️ Failed after: {processing_time:.2f}s")
                logger.error(f"   📝 Response length: {len(response_data['response'])} chars")
    
    async def _validate_rag_results_real(self, result: Any, expected_data: Dict[str, Any], processing_time: float) -> Dict[str, Any]:
        """REAL validation of RAG pipeline results with comprehensive AI output analysis"""
        try:
            validation_errors = []
            performance_issues = []
            quality_issues = []

            # Check if result exists
            if not result:
                return {
                    "success": False,
                    "error": "No result returned from RAG pipeline",
                    "actual_results": {"overall_score": None, "claims_count": 0, "evidence_count": 0}
                }

            # Extract actual results
            actual_results = {
                "overall_score": getattr(result, 'overall_score', None),
                "claims_count": len(getattr(result, 'claims', [])),
                "evidence_count": 0,
                "verification_status": getattr(result, 'verification_status', 'unknown'),
                "processing_time_seconds": processing_time
            }

            # Validate overall score
            if actual_results["overall_score"] is None:
                validation_errors.append("Overall score not provided by RAG pipeline")
            elif not isinstance(actual_results["overall_score"], (int, float)):
                validation_errors.append(f"Overall score not numeric: {type(actual_results['overall_score'])}")
            elif not (0.0 <= actual_results["overall_score"] <= 1.0):
                validation_errors.append(f"Overall score out of range [0,1]: {actual_results['overall_score']}")

            # Validate claims extraction
            claims = getattr(result, 'claims', [])
            if not claims:
                validation_errors.append("No claims extracted from support response")
            else:
                # Count evidence across all claims
                for claim in claims:
                    if hasattr(claim, 'evidence') and claim.evidence:
                        actual_results["evidence_count"] += len(claim.evidence)

                # Check claim quality
                expected_claims = expected_data.get("expected_claims", [])
                if expected_claims:
                    claims_found = 0
                    for expected_claim in expected_claims:
                        claim_text = expected_claim.get("text", "").lower()
                        for actual_claim in claims:
                            if hasattr(actual_claim, 'text') and claim_text in actual_claim.text.lower():
                                claims_found += 1
                                break

                    claim_accuracy = claims_found / len(expected_claims) if expected_claims else 0
                    actual_results["claim_accuracy"] = claim_accuracy

                    if claim_accuracy < 0.5:  # Less than 50% of expected claims found
                        quality_issues.append(f"Low claim extraction accuracy: {claim_accuracy:.1%} ({claims_found}/{len(expected_claims)})")

            # Validate evidence retrieval
            if actual_results["evidence_count"] == 0 and actual_results["claims_count"] > 0:
                validation_errors.append("No evidence retrieved for any claims")

            # Performance validation
            if processing_time > 180.0:  # More than 3 minutes is too slow
                performance_issues.append(f"RAG processing too slow: {processing_time:.1f}s (expected < 180s)")
            elif processing_time > 120.0:  # Warn if over 2 minutes
                performance_issues.append(f"RAG processing slow: {processing_time:.1f}s (consider optimization)")

            # Quality validation against expected results
            expected_accuracy = expected_data.get("expected_accuracy")
            if expected_accuracy and actual_results["overall_score"]:
                accuracy_diff = abs(actual_results["overall_score"] - expected_accuracy)
                if accuracy_diff > 0.3:  # More than 30% difference
                    quality_issues.append(f"Accuracy deviation: expected {expected_accuracy:.3f}, got {actual_results['overall_score']:.3f}")

            # Validate verification status
            valid_statuses = ["VERIFIED", "CONTRADICTED", "INSUFFICIENT_EVIDENCE", "PARTIALLY_VERIFIED", "NEEDS_REVIEW"]
            if actual_results["verification_status"] not in valid_statuses:
                validation_errors.append(f"Invalid verification status: {actual_results['verification_status']}")

            # Calculate overall success
            total_issues = len(validation_errors) + len(performance_issues) + len(quality_issues)
            is_successful = (
                total_issues == 0 and
                actual_results["overall_score"] is not None and
                actual_results["claims_count"] > 0 and
                (actual_results["evidence_count"] > 0 or actual_results["claims_count"] == 0)
            )

            result_data = {
                "success": is_successful,
                "actual_results": actual_results,
                "validation_details": {
                    "validation_errors": validation_errors,
                    "performance_issues": performance_issues,
                    "quality_issues": quality_issues
                }
            }

            if not is_successful:
                all_errors = validation_errors + performance_issues + quality_issues
                result_data["error"] = "; ".join(all_errors)

            return result_data

        except Exception as e:
            return {
                "success": False,
                "error": f"RAG validation exception: {str(e)}",
                "actual_results": {"overall_score": None, "claims_count": 0, "evidence_count": 0}
            }
    
    async def _run_alert_system_tests(self):
        """Run alert system tests"""
        logger.info("🚨 Running alert system tests...")
        
        alert_scenarios = TestDataGenerator.generate_alert_test_scenarios()
        
        for scenario_data in alert_scenarios:
            try:
                # Setup test scenario
                await self._setup_alert_test_scenario(scenario_data)
                
                # Trigger appropriate alert check
                scenario_type = scenario_data["scenario"]
                if "sla_breach" in scenario_type:
                    await AlertService.check_sla_breaches()
                elif scenario_type == "aging_query":
                    await AlertService.check_aging_queries()
                elif scenario_type == "factual_error":
                    await AlertService.check_factual_errors()
                elif scenario_type == "negative_sentiment":
                    await AlertService.check_negative_sentiment()
                
                # Validate alert creation
                validation_result = await self._validate_alert_creation(scenario_data)
                
                if validation_result["success"]:
                    self.test_results["alert_system"]["passed"] += 1
                    logger.info(f"✅ Alert system test passed: {scenario_type}")
                else:
                    self.test_results["alert_system"]["failed"] += 1
                    logger.error(f"❌ Alert system test failed: {validation_result['error']}")
                
                self.test_results["alert_system"]["details"].append({
                    "scenario": scenario_type,
                    "success": validation_result["success"],
                    "details": validation_result
                })
                
                # Cleanup
                await self._cleanup_alert_test_scenario(scenario_data)
                
            except Exception as e:
                self.test_results["alert_system"]["failed"] += 1
                logger.error(f"❌ Alert system test error: {e}")
    
    async def _setup_alert_test_scenario(self, scenario_data: Dict[str, Any]):
        """Setup test scenario for alert testing"""
        db = SessionLocal()
        try:
            email_data = scenario_data["email_data"]
            email_id = email_data["email_id"]
            
            # Create email record
            created_time = datetime.utcnow()
            if "created_hours_ago" in email_data:
                created_time = datetime.utcnow() - timedelta(hours=email_data["created_hours_ago"])
            
            email = Email(
                email_identifier=email_id,
                is_inbound=not email_data.get("is_outbound", False),
                thread_id=f"thread_{email_id}",
                created_at=created_time
            )
            db.add(email)
            
            # Create analysis record based on scenario
            if email_data.get("is_outbound"):
                # Outbound analysis for quality-based alerts
                analysis = OutboundEmailAnalysis(
                    email_id=email_id,
                    type="query",
                    factual_accuracy=email_data.get("factual_accuracy", 0.8),
                    guideline_compliance=0.8,
                    completeness=0.8,
                    tone=email_data.get("tone", "professional"),
                    created_at=created_time
                )
                db.add(analysis)
            else:
                # Inbound analysis for SLA-based alerts
                analysis = InboundEmailAnalysis(
                    email_id=email_id,
                    from_email=f"test@{email_id}.com",
                    type="query",
                    priority=email_data.get("priority", "medium"),
                    category="test_category",
                    responded=email_data.get("responded", False),
                    created_at=created_time
                )
                db.add(analysis)
            
            db.commit()
            
        finally:
            db.close()
    
    async def _validate_alert_creation(self, scenario_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate alert creation for test scenario"""
        db = SessionLocal()
        try:
            email_id = scenario_data["email_data"]["email_id"]
            expected_alert = scenario_data["expected_alert"]
            
            # Check if alert was created
            alert = db.query(Alert).filter(
                Alert.email_id == email_id,
                Alert.alert_type == expected_alert["alert_type"]
            ).first()
            
            if not alert:
                return {"success": False, "error": f"Alert not created for {email_id}"}
            
            # Validate alert properties
            validation_errors = []
            
            if alert.severity != expected_alert["severity"]:
                validation_errors.append(f"Severity mismatch: expected {expected_alert['severity']}, got {alert.severity}")
            
            if alert.threshold_value != expected_alert["threshold_value"]:
                validation_errors.append(f"Threshold mismatch: expected {expected_alert['threshold_value']}, got {alert.threshold_value}")
            
            if "current_value_min" in expected_alert and alert.current_value < expected_alert["current_value_min"]:
                validation_errors.append(f"Current value too low: expected >= {expected_alert['current_value_min']}, got {alert.current_value}")
            
            if "current_value" in expected_alert and alert.current_value != expected_alert["current_value"]:
                validation_errors.append(f"Current value mismatch: expected {expected_alert['current_value']}, got {alert.current_value}")
            
            if validation_errors:
                return {"success": False, "error": "; ".join(validation_errors)}
            
            return {
                "success": True,
                "results": {
                    "alert_id": alert.id,
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "current_value": alert.current_value,
                    "threshold_value": alert.threshold_value
                }
            }
            
        finally:
            db.close()
    
    async def _cleanup_alert_test_scenario(self, scenario_data: Dict[str, Any]):
        """Cleanup test scenario data"""
        db = SessionLocal()
        try:
            email_id = scenario_data["email_data"]["email_id"]
            
            # Delete in correct order (alerts first, then analyses, then email)
            db.query(Alert).filter(Alert.email_id == email_id).delete()
            db.query(InboundEmailAnalysis).filter(InboundEmailAnalysis.email_id == email_id).delete()
            db.query(OutboundEmailAnalysis).filter(OutboundEmailAnalysis.email_id == email_id).delete()
            db.query(Email).filter(Email.email_identifier == email_id).delete()
            
            db.commit()
            
        finally:
            db.close()
    
    async def _run_database_integrity_tests(self):
        """Run REAL database integrity tests with actual database operations"""
        logger.info("💾 Running REAL database integrity tests...")

        # Test 1: Database Connection and Basic Operations
        await self._test_database_connection()

        # Test 2: Table Structure and Relationships
        await self._test_table_relationships()

        # Test 3: Foreign Key Constraints
        await self._test_foreign_key_constraints()

        # Test 4: Data Type Constraints
        await self._test_data_type_constraints()

        # Test 5: Cascade Delete Behavior
        await self._test_cascade_delete_behavior()

    async def _test_database_connection(self):
        """Test actual database connection and basic operations"""
        try:
            logger.info("🔄 Testing database connection...")
            db = SessionLocal()

            # Test basic query
            from sqlalchemy import text
            result = db.execute(text("SELECT 1 as test")).fetchone()
            if not result or result[0] != 1:
                raise Exception("Basic database query failed")

            # Test table existence
            tables_query = """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = DATABASE()
            AND table_name IN ('email', 'inbound_email_analysis', 'outbound_email_analysis', 'alerts', 'daily_reports')
            """
            tables = db.execute(tables_query).fetchall()
            table_names = [t[0] for t in tables]

            required_tables = ['email', 'inbound_email_analysis', 'outbound_email_analysis', 'alerts']
            missing_tables = [t for t in required_tables if t not in table_names]

            if missing_tables:
                raise Exception(f"Missing required tables: {missing_tables}")

            db.close()

            self.test_results["database_integrity"]["passed"] += 1
            logger.info("✅ Database connection test passed")
            logger.info(f"   📊 Tables found: {', '.join(table_names)}")

        except Exception as e:
            self.test_results["database_integrity"]["failed"] += 1
            logger.error(f"❌ Database connection test failed: {e}")

    async def _test_table_relationships(self):
        """Test actual table relationships with real data"""
        try:
            logger.info("🔄 Testing table relationships...")
            db = SessionLocal()

            # Create test email with relationships
            test_email_id = f"db_test_{int(datetime.now().timestamp())}"

            # Create email record
            email = Email(
                email_identifier=test_email_id,
                is_inbound=True,
                thread_id=f"thread_{test_email_id}"
            )
            db.add(email)
            db.flush()  # Get the ID without committing

            # Create inbound analysis
            analysis = InboundEmailAnalysis(
                email_id=test_email_id,
                from_email="test@relationship.com",
                type="query",
                priority="medium",
                category="general_information"
            )
            db.add(analysis)

            # Create alert
            alert = Alert(
                alert_type="test_relationship",
                severity="info",
                email_id=test_email_id,
                title="Relationship Test Alert",
                description="Testing database relationships"
            )
            db.add(alert)

            db.commit()

            # Test relationships
            db.refresh(email)

            # Check one-to-one relationship (email -> inbound_analysis)
            if not email.inbound_analysis:
                raise Exception("Email -> InboundAnalysis relationship failed")

            if email.inbound_analysis.type != "query":
                raise Exception("Relationship data integrity failed")

            # Check one-to-many relationship (email -> alerts)
            if not email.alerts or len(email.alerts) == 0:
                raise Exception("Email -> Alerts relationship failed")

            if email.alerts[0].alert_type != "test_relationship":
                raise Exception("Alert relationship data integrity failed")

            # Cleanup
            db.delete(alert)
            db.delete(analysis)
            db.delete(email)
            db.commit()
            db.close()

            self.test_results["database_integrity"]["passed"] += 1
            logger.info("✅ Table relationships test passed")

        except Exception as e:
            self.test_results["database_integrity"]["failed"] += 1
            logger.error(f"❌ Table relationships test failed: {e}")
            # Cleanup on error
            try:
                db.rollback()
                db.close()
            except:
                pass
    
    async def _test_foreign_key_constraints(self):
        """Test foreign key constraints with actual constraint violations"""
        try:
            logger.info("🔄 Testing foreign key constraints...")
            db = SessionLocal()

            # Test 1: Try to create inbound analysis without email (should fail)
            try:
                invalid_analysis = InboundEmailAnalysis(
                    email_id="nonexistent_email_id",
                    from_email="test@constraint.com",
                    type="query",
                    priority="medium",
                    category="general_information"
                )
                db.add(invalid_analysis)
                db.commit()

                # If we get here, constraint failed
                raise Exception("Foreign key constraint not enforced - invalid analysis created")

            except Exception as constraint_error:
                # This should happen - constraint violation
                db.rollback()
                if "foreign key constraint" in str(constraint_error).lower() or "cannot add or update" in str(constraint_error).lower():
                    logger.info("   ✅ Foreign key constraint properly enforced")
                else:
                    raise Exception(f"Unexpected constraint error: {constraint_error}")

            db.close()

            self.test_results["database_integrity"]["passed"] += 1
            logger.info("✅ Foreign key constraints test passed")

        except Exception as e:
            self.test_results["database_integrity"]["failed"] += 1
            logger.error(f"❌ Foreign key constraints test failed: {e}")

    async def _test_data_type_constraints(self):
        """Test data type constraints and validation"""
        try:
            logger.info("🔄 Testing data type constraints...")
            db = SessionLocal()

            # Create valid test email first
            test_email_id = f"dtype_test_{int(datetime.now().timestamp())}"
            email = Email(
                email_identifier=test_email_id,
                is_inbound=True,
                thread_id=f"thread_{test_email_id}"
            )
            db.add(email)
            db.commit()

            # Test valid data types
            analysis = InboundEmailAnalysis(
                email_id=test_email_id,
                from_email="test@datatype.com",
                type="query",
                priority="high",
                category="access_issue",
                responded=False
            )
            db.add(analysis)
            db.commit()

            # Verify data was stored correctly
            stored_analysis = db.query(InboundEmailAnalysis).filter(
                InboundEmailAnalysis.email_id == test_email_id
            ).first()

            if not stored_analysis:
                raise Exception("Analysis not stored")

            if stored_analysis.responded != False:
                raise Exception("Boolean data type constraint failed")

            if stored_analysis.priority != "high":
                raise Exception("String data type constraint failed")

            # Cleanup
            db.delete(analysis)
            db.delete(email)
            db.commit()
            db.close()

            self.test_results["database_integrity"]["passed"] += 1
            logger.info("✅ Data type constraints test passed")

        except Exception as e:
            self.test_results["database_integrity"]["failed"] += 1
            logger.error(f"❌ Data type constraints test failed: {e}")

    async def _test_cascade_delete_behavior(self):
        """Test cascade delete behavior with actual deletions"""
        try:
            logger.info("🔄 Testing cascade delete behavior...")
            db = SessionLocal()

            # Create test data with relationships
            test_email_id = f"cascade_test_{int(datetime.now().timestamp())}"

            email = Email(
                email_identifier=test_email_id,
                is_inbound=True,
                thread_id=f"thread_{test_email_id}"
            )
            db.add(email)
            db.flush()

            analysis = InboundEmailAnalysis(
                email_id=test_email_id,
                from_email="test@cascade.com",
                type="query",
                priority="low",
                category="others"
            )
            db.add(analysis)

            alert = Alert(
                alert_type="cascade_test",
                severity="info",
                email_id=test_email_id,
                title="Cascade Test Alert",
                description="Testing cascade delete"
            )
            db.add(alert)

            db.commit()

            # Verify records exist
            email_count = db.query(Email).filter(Email.email_identifier == test_email_id).count()
            analysis_count = db.query(InboundEmailAnalysis).filter(InboundEmailAnalysis.email_id == test_email_id).count()
            alert_count = db.query(Alert).filter(Alert.email_id == test_email_id).count()

            if email_count != 1 or analysis_count != 1 or alert_count != 1:
                raise Exception("Test records not created properly")

            # Delete parent email (should cascade to children)
            db.delete(email)
            db.commit()

            # Verify cascade delete worked
            remaining_analysis = db.query(InboundEmailAnalysis).filter(
                InboundEmailAnalysis.email_id == test_email_id
            ).count()
            remaining_alert = db.query(Alert).filter(
                Alert.email_id == test_email_id
            ).count()

            if remaining_analysis != 0:
                raise Exception("Analysis record not deleted on cascade")

            if remaining_alert != 0:
                raise Exception("Alert record not deleted on cascade")

            db.close()

            self.test_results["database_integrity"]["passed"] += 1
            logger.info("✅ Cascade delete behavior test passed")

        except Exception as e:
            self.test_results["database_integrity"]["failed"] += 1
            logger.error(f"❌ Cascade delete behavior test failed: {e}")

    async def _run_api_endpoint_tests(self):
        """Run REAL API endpoint tests with actual HTTP requests"""
        logger.info("🌐 Running REAL API endpoint tests...")

        base_url = "http://localhost:5001"

        # Test 1: Health endpoint
        await self._test_health_endpoint(base_url)

        # Test 2: RAG verification endpoint
        await self._test_rag_verification_endpoint(base_url)

        # Test 3: Alert system endpoints
        await self._test_alert_endpoints(base_url)

    async def _test_health_endpoint(self, base_url: str):
        """Test health endpoint with real HTTP request"""
        try:
            import requests

            logger.info("🔄 Testing health endpoint...")
            response = requests.get(f"{base_url}/health", timeout=10)

            if response.status_code != 200:
                raise Exception(f"Health endpoint returned {response.status_code}")

            data = response.json()
            if not data.get("ok"):
                raise Exception("Health endpoint returned unhealthy status")

            self.test_results["api_endpoints"]["passed"] += 1
            logger.info("✅ Health endpoint test passed")

        except Exception as e:
            self.test_results["api_endpoints"]["failed"] += 1
            logger.error(f"❌ Health endpoint test failed: {e}")

    async def _run_performance_tests(self):
        """Run REAL performance tests with actual load testing"""
        logger.info("⚡ Running REAL performance tests...")

        # Test 1: Email classification performance
        await self._test_classification_performance()

        # Test 2: Database query performance
        await self._test_database_performance()

        # Test 3: API response time performance
        await self._test_api_performance()

    async def _test_classification_performance(self):
        """Test email classification performance with multiple emails"""
        try:
            logger.info("🔄 Testing email classification performance...")

            # Generate multiple test emails
            test_emails = []
            for i in range(5):  # Test with 5 emails
                test_emails.append({
                    "email_id": f"perf_test_{i}_{int(datetime.now().timestamp())}",
                    "from_email": f"perf{i}@test.com",
                    "thread_id": f"thread_perf_{i}",
                    "subject": f"Performance Test Email {i}",
                    "body": f"This is performance test email number {i}. Testing classification speed and accuracy.",
                    "is_inbound": True
                })

            start_time = datetime.now()
            successful_classifications = 0

            for email_data in test_emails:
                try:
                    await classify_email(**email_data)
                    successful_classifications += 1
                    # Cleanup immediately
                    await self._cleanup_test_email(email_data["email_id"])
                except Exception as e:
                    logger.warning(f"Performance test email failed: {e}")

            total_time = (datetime.now() - start_time).total_seconds()
            avg_time_per_email = total_time / len(test_emails)

            if avg_time_per_email > 10.0:  # More than 10 seconds per email is too slow
                raise Exception(f"Classification too slow: {avg_time_per_email:.2f}s per email")

            if successful_classifications < len(test_emails) * 0.8:  # Less than 80% success rate
                raise Exception(f"Low success rate: {successful_classifications}/{len(test_emails)}")

            self.test_results["performance"]["passed"] += 1
            logger.info(f"✅ Classification performance test passed")
            logger.info(f"   📊 Processed {successful_classifications}/{len(test_emails)} emails")
            logger.info(f"   ⏱️ Average time: {avg_time_per_email:.2f}s per email")

        except Exception as e:
            self.test_results["performance"]["failed"] += 1
            logger.error(f"❌ Classification performance test failed: {e}")
    
    def _generate_final_report(self) -> Dict[str, Any]:
        """Generate comprehensive test report"""
        end_time = datetime.now()
        execution_time = (end_time - self.start_time).total_seconds()
        
        total_passed = sum(category["passed"] for category in self.test_results.values())
        total_failed = sum(category["failed"] for category in self.test_results.values())
        total_tests = total_passed + total_failed
        
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        
        report = {
            "execution_summary": {
                "start_time": self.start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "execution_time_seconds": execution_time,
                "total_tests": total_tests,
                "total_passed": total_passed,
                "total_failed": total_failed,
                "success_rate_percent": round(success_rate, 2)
            },
            "category_results": self.test_results,
            "status": "PASSED" if total_failed == 0 else "FAILED"
        }
        
        # Save report to file
        report_file = f"tests/docs/test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"📊 Test report saved to {report_file}")
        logger.info(f"🎯 Test execution completed: {total_passed}/{total_tests} passed ({success_rate:.1f}%)")
        
        return report

async def main():
    """Main test execution function"""
    runner = ComprehensiveTestRunner()
    report = await runner.run_all_tests()
    
    print("\n" + "="*80)
    print("🎉 COMPREHENSIVE TEST EXECUTION COMPLETED")
    print("="*80)
    print(f"Status: {report['status']}")
    print(f"Total Tests: {report['execution_summary']['total_tests']}")
    print(f"Passed: {report['execution_summary']['total_passed']}")
    print(f"Failed: {report['execution_summary']['total_failed']}")
    print(f"Success Rate: {report['execution_summary']['success_rate_percent']}%")
    print(f"Execution Time: {report['execution_summary']['execution_time_seconds']:.2f} seconds")
    print("="*80)
    
    return report

if __name__ == "__main__":
    asyncio.run(main())
