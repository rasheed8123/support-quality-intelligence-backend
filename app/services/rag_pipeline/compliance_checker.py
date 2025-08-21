"""
Compliance checking engine for the Support Quality Intelligence system.
Verifies support responses against company policies and guidelines stored in vector DB.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from app.services.rag_pipeline.advanced_retrieval import AdvancedRetrievalEngine
from app.services.rag_pipeline.claim_extraction import Claim
from app.config import settings
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


@dataclass
class ComplianceViolation:
    """Represents a compliance violation"""
    rule_type: str
    severity: str  # "critical", "major", "minor"
    description: str
    violated_text: str
    guideline_reference: str
    suggested_correction: str
    confidence: float


@dataclass
class ComplianceRecommendation:
    """Represents a compliance recommendation"""
    category: str
    description: str
    priority: str  # "high", "medium", "low"
    implementation: str


@dataclass
class ComplianceResult:
    """Complete compliance checking result"""
    overall_score: float
    violations: List[ComplianceViolation]
    recommendations: List[ComplianceRecommendation]
    compliant_aspects: List[str]
    guidelines_checked: int
    processing_time_ms: float


class ComplianceChecker:
    """
    Advanced compliance checking engine that verifies support responses
    against company policies and guidelines stored in the vector database.
    """
    
    def __init__(self):
        """Initialize the compliance checker"""
        self.retrieval_engine = AdvancedRetrievalEngine()
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Compliance rule categories
        self.rule_categories = {
            "policy_accuracy": "Factual accuracy of policies mentioned",
            "communication_tone": "Professional and empathetic communication",
            "information_completeness": "Required information inclusion",
            "escalation_procedures": "Proper escalation and follow-up",
            "data_privacy": "Customer data handling compliance",
            "service_standards": "Customer service quality standards"
        }
        
        logger.info(f"Compliance checker initialized with model: {settings.COMPLIANCE_CHECK_MODEL}")
    
    async def check_compliance(
        self,
        support_response: str,
        customer_query: str,
        claims: List[Claim],
        context: Optional[Dict[str, Any]] = None
    ) -> ComplianceResult:
        """
        Perform comprehensive compliance checking against guidelines.
        
        Args:
            support_response: The support response to check
            customer_query: Original customer query for context
            claims: Extracted claims from the response
            context: Additional context information
            
        Returns:
            Comprehensive compliance checking result
        """
        start_time = datetime.now()
        logger.info(f"Starting compliance check for response of {len(support_response)} characters")
        
        try:
            # Step 1: Retrieve relevant guidelines
            guidelines = await self._retrieve_relevant_guidelines(
                support_response, customer_query, claims
            )
            
            # Step 2: Check policy compliance
            policy_violations = await self._check_policy_compliance(
                support_response, claims, guidelines
            )
            
            # Step 3: Check communication standards
            communication_issues = await self._check_communication_standards(
                support_response, customer_query
            )
            
            # Step 4: Check information completeness
            completeness_issues = await self._check_information_completeness(
                support_response, customer_query, guidelines
            )
            
            # Step 5: Generate recommendations
            recommendations = await self._generate_recommendations(
                support_response, policy_violations + communication_issues + completeness_issues
            )
            
            # Step 6: Identify compliant aspects
            compliant_aspects = await self._identify_compliant_aspects(
                support_response, guidelines
            )
            
            # Combine all violations
            all_violations = policy_violations + communication_issues + completeness_issues
            
            # Calculate overall compliance score
            overall_score = self._calculate_compliance_score(all_violations, len(guidelines))
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            result = ComplianceResult(
                overall_score=overall_score,
                violations=all_violations,
                recommendations=recommendations,
                compliant_aspects=compliant_aspects,
                guidelines_checked=len(guidelines),
                processing_time_ms=processing_time
            )
            
            logger.info(f"Compliance check completed: score={overall_score:.2f}, violations={len(all_violations)}")
            return result
            
        except Exception as e:
            logger.error(f"Compliance checking failed: {str(e)}")
            # Return minimal result on error
            return ComplianceResult(
                overall_score=0.5,
                violations=[],
                recommendations=[],
                compliant_aspects=[],
                guidelines_checked=0,
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
    
    async def _retrieve_relevant_guidelines(
        self,
        support_response: str,
        customer_query: str,
        claims: List[Claim]
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant guidelines from vector database"""
        
        # Create search queries for different types of guidelines
        search_queries = [
            f"policies and guidelines for: {customer_query}",
            f"compliance rules for: {support_response[:200]}",
            "customer service standards and communication guidelines",
            "escalation procedures and follow-up requirements"
        ]
        
        # Add claim-specific searches
        for claim in claims[:3]:  # Limit to top 3 claims
            search_queries.append(f"policy guidelines for: {claim.text}")
        
        all_guidelines = []
        
        for query in search_queries:
            try:
                # Use advanced retrieval to find relevant guidelines
                results = await self.retrieval_engine.retrieve_evidence_for_claims(
                    claims=[Claim(text=query, confidence=1.0, category="guideline_search")],
                    max_evidence_per_claim=5
                )
                
                if query in results:
                    all_guidelines.extend(results[query])
                    
            except Exception as e:
                logger.warning(f"Failed to retrieve guidelines for query '{query}': {str(e)}")
        
        # Deduplicate and return top guidelines
        unique_guidelines = []
        seen_content = set()
        
        for guideline in all_guidelines:
            content_hash = hash(guideline.get('content', '')[:100])
            if content_hash not in seen_content:
                seen_content.add(content_hash)
                unique_guidelines.append(guideline)
        
        logger.info(f"Retrieved {len(unique_guidelines)} unique guidelines")
        return unique_guidelines[:10]  # Limit to top 10
    
    async def _check_policy_compliance(
        self,
        support_response: str,
        claims: List[Claim],
        guidelines: List[Dict[str, Any]]
    ) -> List[ComplianceViolation]:
        """Check compliance with specific policies"""
        
        violations = []
        
        if not guidelines:
            return violations
        
        # Create guideline context
        guideline_context = "\n".join([
            f"Guideline: {g.get('content', '')[:300]}"
            for g in guidelines[:5]
        ])
        
        prompt = f"""
        You are a compliance officer checking if a support response follows company guidelines.
        
        SUPPORT RESPONSE:
        {support_response}
        
        COMPANY GUIDELINES:
        {guideline_context}
        
        EXTRACTED CLAIMS:
        {[claim.text for claim in claims]}
        
        Check for policy violations and return a JSON array of violations:
        [
            {{
                "rule_type": "policy_accuracy|communication_tone|information_completeness",
                "severity": "critical|major|minor",
                "description": "Clear description of the violation",
                "violated_text": "Specific text that violates the rule",
                "guideline_reference": "Which guideline was violated",
                "suggested_correction": "How to fix this violation",
                "confidence": 0.0-1.0
            }}
        ]
        
        Focus on:
        1. Factual accuracy of policies mentioned
        2. Missing required information
        3. Incorrect procedures or timelines
        4. Contradictions with guidelines
        
        Return empty array [] if no violations found.
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.COMPLIANCE_CHECK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1500
            )
            
            import json
            try:
                content = response.choices[0].message.content.strip()
                if not content:
                    violations_data = []
                else:
                    violations_data = json.loads(content)
            except (json.JSONDecodeError, AttributeError) as e:
                logger.error(f"Failed to parse policy violations JSON: {str(e)}")
                violations_data = []
            
            for violation_data in violations_data:
                violations.append(ComplianceViolation(
                    rule_type=violation_data.get("rule_type", "unknown"),
                    severity=violation_data.get("severity", "minor"),
                    description=violation_data.get("description", ""),
                    violated_text=violation_data.get("violated_text", ""),
                    guideline_reference=violation_data.get("guideline_reference", ""),
                    suggested_correction=violation_data.get("suggested_correction", ""),
                    confidence=violation_data.get("confidence", 0.5)
                ))
            
            logger.info(f"Found {len(violations)} policy violations")
            
        except Exception as e:
            logger.error(f"Policy compliance check failed: {str(e)}")
        
        return violations
    
    async def _check_communication_standards(
        self,
        support_response: str,
        customer_query: str
    ) -> List[ComplianceViolation]:
        """Check communication tone and standards"""
        
        violations = []
        
        prompt = f"""
        Check this support response for communication standard violations:
        
        CUSTOMER QUERY: {customer_query}
        SUPPORT RESPONSE: {support_response}
        
        Check for these communication issues and return JSON array:
        [
            {{
                "rule_type": "communication_tone",
                "severity": "critical|major|minor",
                "description": "Description of communication issue",
                "violated_text": "Problematic text",
                "guideline_reference": "Professional communication standards",
                "suggested_correction": "Better way to communicate",
                "confidence": 0.0-1.0
            }}
        ]
        
        Look for:
        1. Unprofessional tone or language
        2. Lack of empathy or acknowledgment
        3. Too formal or too casual tone
        4. Missing courtesy elements (greetings, thanks)
        5. Unclear or confusing language
        
        Return [] if communication is appropriate.
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.COMPLIANCE_CHECK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1000
            )
            
            import json
            try:
                content = response.choices[0].message.content.strip()
                if not content:
                    violations_data = []
                else:
                    violations_data = json.loads(content)
            except (json.JSONDecodeError, AttributeError) as e:
                logger.error(f"Failed to parse communication violations JSON: {str(e)}")
                violations_data = []
            
            for violation_data in violations_data:
                violations.append(ComplianceViolation(
                    rule_type=violation_data.get("rule_type", "communication_tone"),
                    severity=violation_data.get("severity", "minor"),
                    description=violation_data.get("description", ""),
                    violated_text=violation_data.get("violated_text", ""),
                    guideline_reference=violation_data.get("guideline_reference", ""),
                    suggested_correction=violation_data.get("suggested_correction", ""),
                    confidence=violation_data.get("confidence", 0.5)
                ))
            
        except Exception as e:
            logger.error(f"Communication standards check failed: {str(e)}")
        
        return violations
    
    async def _check_information_completeness(
        self,
        support_response: str,
        customer_query: str,
        guidelines: List[Dict[str, Any]]
    ) -> List[ComplianceViolation]:
        """Check if response includes all required information"""
        
        violations = []
        
        prompt = f"""
        Check if this support response includes all necessary information:
        
        CUSTOMER QUERY: {customer_query}
        SUPPORT RESPONSE: {support_response}
        
        Based on the customer's question, identify missing critical information:
        
        Return JSON array of missing information violations:
        [
            {{
                "rule_type": "information_completeness",
                "severity": "major|minor",
                "description": "What information is missing",
                "violated_text": "N/A",
                "guideline_reference": "Complete information requirement",
                "suggested_correction": "What should be added",
                "confidence": 0.0-1.0
            }}
        ]
        
        Common missing elements:
        1. Specific timelines or deadlines
        2. Contact information for follow-up
        3. Next steps or action items
        4. Alternative solutions
        5. Reference numbers or documentation
        
        Return [] if response is complete.
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.COMPLIANCE_CHECK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                max_tokens=1000
            )
            
            import json
            try:
                content = response.choices[0].message.content.strip()
                if not content:
                    violations_data = []
                else:
                    violations_data = json.loads(content)
            except (json.JSONDecodeError, AttributeError) as e:
                logger.error(f"Failed to parse completeness violations JSON: {str(e)}")
                violations_data = []
            
            for violation_data in violations_data:
                violations.append(ComplianceViolation(
                    rule_type=violation_data.get("rule_type", "information_completeness"),
                    severity=violation_data.get("severity", "minor"),
                    description=violation_data.get("description", ""),
                    violated_text=violation_data.get("violated_text", "N/A"),
                    guideline_reference=violation_data.get("guideline_reference", ""),
                    suggested_correction=violation_data.get("suggested_correction", ""),
                    confidence=violation_data.get("confidence", 0.5)
                ))
            
        except Exception as e:
            logger.error(f"Information completeness check failed: {str(e)}")
        
        return violations
    
    async def _generate_recommendations(
        self,
        support_response: str,
        violations: List[ComplianceViolation]
    ) -> List[ComplianceRecommendation]:
        """Generate improvement recommendations"""
        
        if not violations:
            return [
                ComplianceRecommendation(
                    category="general",
                    description="Response meets compliance standards",
                    priority="low",
                    implementation="Continue following current practices"
                )
            ]
        
        recommendations = []
        
        # Group violations by type
        violation_groups = {}
        for violation in violations:
            if violation.rule_type not in violation_groups:
                violation_groups[violation.rule_type] = []
            violation_groups[violation.rule_type].append(violation)
        
        # Generate recommendations for each group
        for rule_type, group_violations in violation_groups.items():
            if rule_type == "policy_accuracy":
                recommendations.append(ComplianceRecommendation(
                    category="policy_accuracy",
                    description="Review and verify policy information before responding",
                    priority="high",
                    implementation="Cross-reference with latest policy documents"
                ))
            elif rule_type == "communication_tone":
                recommendations.append(ComplianceRecommendation(
                    category="communication",
                    description="Improve communication tone and professionalism",
                    priority="medium",
                    implementation="Use more empathetic language and acknowledge customer concerns"
                ))
            elif rule_type == "information_completeness":
                recommendations.append(ComplianceRecommendation(
                    category="completeness",
                    description="Include all necessary information in responses",
                    priority="medium",
                    implementation="Use response checklists to ensure completeness"
                ))
        
        return recommendations
    
    async def _identify_compliant_aspects(
        self,
        support_response: str,
        guidelines: List[Dict[str, Any]]
    ) -> List[str]:
        """Identify what the response does well"""
        
        compliant_aspects = []
        
        # Basic compliance checks
        if len(support_response.split()) >= 10:
            compliant_aspects.append("Adequate response length")
        
        if any(word in support_response.lower() for word in ["thank", "please", "help"]):
            compliant_aspects.append("Polite and courteous tone")
        
        if any(word in support_response.lower() for word in ["understand", "sorry", "apologize"]):
            compliant_aspects.append("Shows empathy and understanding")
        
        if "?" in support_response:
            compliant_aspects.append("Asks clarifying questions")
        
        return compliant_aspects
    
    def _calculate_compliance_score(
        self,
        violations: List[ComplianceViolation],
        guidelines_checked: int
    ) -> float:
        """Calculate overall compliance score"""
        
        if not violations:
            return 1.0
        
        # Weight violations by severity
        severity_weights = {
            "critical": 0.4,
            "major": 0.2,
            "minor": 0.1
        }
        
        total_penalty = 0.0
        for violation in violations:
            weight = severity_weights.get(violation.severity, 0.1)
            confidence_factor = violation.confidence
            total_penalty += weight * confidence_factor
        
        # Calculate score (1.0 - penalties, minimum 0.0)
        score = max(0.0, 1.0 - total_penalty)
        
        return round(score, 3)
