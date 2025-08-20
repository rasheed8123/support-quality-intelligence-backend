"""
Intelligent feedback generation engine for the Support Quality Intelligence system.
Generates actionable improvement suggestions and alternative response recommendations.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from app.services.rag_pipeline.compliance_checker import ComplianceViolation, ComplianceResult
from app.services.rag_pipeline.fact_verification import ClaimVerification
from app.services.rag_pipeline.claim_extraction import Claim
from app.config import settings
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


@dataclass
class ImprovementSuggestion:
    """Represents a specific improvement suggestion"""
    category: str
    priority: str  # "high", "medium", "low"
    description: str
    specific_action: str
    expected_impact: str
    implementation_effort: str  # "low", "medium", "high"


@dataclass
class ResponseSuggestion:
    """Represents an improved response suggestion"""
    improved_response: str
    key_improvements: List[str]
    tone_adjustments: List[str]
    added_information: List[str]
    confidence: float


@dataclass
class FeedbackResult:
    """Complete feedback generation result"""
    overall_feedback: str
    improvement_suggestions: List[ImprovementSuggestion]
    response_suggestion: Optional[ResponseSuggestion]
    strengths: List[str]
    areas_for_improvement: List[str]
    training_recommendations: List[str]
    processing_time_ms: float


class FeedbackGenerator:
    """
    Advanced feedback generation engine that provides intelligent,
    actionable improvement suggestions for support responses.
    """
    
    def __init__(self):
        """Initialize the feedback generator"""
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Feedback categories
        self.feedback_categories = {
            "accuracy": "Factual correctness and policy compliance",
            "communication": "Tone, clarity, and professionalism",
            "completeness": "Information thoroughness and detail",
            "empathy": "Customer understanding and emotional intelligence",
            "efficiency": "Response speed and problem resolution",
            "personalization": "Customer-specific customization"
        }
        
        logger.info(f"Feedback generator initialized with model: {settings.FEEDBACK_GENERATION_MODEL}")
    
    async def generate_feedback(
        self,
        support_response: str,
        customer_query: str,
        claims: List[Claim],
        claim_verifications: List[ClaimVerification],
        compliance_result: ComplianceResult,
        context: Optional[Dict[str, Any]] = None
    ) -> FeedbackResult:
        """
        Generate comprehensive feedback for a support response.
        
        Args:
            support_response: The support response to analyze
            customer_query: Original customer query
            claims: Extracted claims from the response
            claim_verifications: Fact verification results
            compliance_result: Compliance checking results
            context: Additional context information
            
        Returns:
            Comprehensive feedback with suggestions and improvements
        """
        start_time = datetime.now()
        logger.info(f"Generating feedback for response of {len(support_response)} characters")
        
        try:
            # Step 1: Analyze response strengths and weaknesses
            strengths, weaknesses = await self._analyze_response_quality(
                support_response, customer_query, claim_verifications, compliance_result
            )
            
            # Step 2: Generate specific improvement suggestions
            improvement_suggestions = await self._generate_improvement_suggestions(
                support_response, customer_query, weaknesses, compliance_result.violations
            )
            
            # Step 3: Generate improved response suggestion
            response_suggestion = await self._generate_response_suggestion(
                support_response, customer_query, improvement_suggestions
            )
            
            # Step 4: Generate training recommendations
            training_recommendations = await self._generate_training_recommendations(
                weaknesses, compliance_result.violations
            )
            
            # Step 5: Create overall feedback summary
            overall_feedback = await self._generate_overall_feedback(
                strengths, weaknesses, improvement_suggestions
            )
            
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            result = FeedbackResult(
                overall_feedback=overall_feedback,
                improvement_suggestions=improvement_suggestions,
                response_suggestion=response_suggestion,
                strengths=strengths,
                areas_for_improvement=weaknesses,
                training_recommendations=training_recommendations,
                processing_time_ms=processing_time
            )
            
            logger.info(f"Feedback generation completed in {processing_time:.0f}ms")
            return result
            
        except Exception as e:
            logger.error(f"Feedback generation failed: {str(e)}")
            # Return minimal feedback on error
            return FeedbackResult(
                overall_feedback="Unable to generate detailed feedback due to processing error.",
                improvement_suggestions=[],
                response_suggestion=None,
                strengths=[],
                areas_for_improvement=[],
                training_recommendations=[],
                processing_time_ms=(datetime.now() - start_time).total_seconds() * 1000
            )
    
    async def _analyze_response_quality(
        self,
        support_response: str,
        customer_query: str,
        claim_verifications: List[ClaimVerification],
        compliance_result: ComplianceResult
    ) -> tuple[List[str], List[str]]:
        """Analyze response to identify strengths and weaknesses"""
        
        # Prepare verification context
        verification_context = ""
        if claim_verifications:
            verification_context = "\n".join([
                f"Claim: {cv.claim_text} - Status: {cv.status} - Confidence: {cv.confidence}"
                for cv in claim_verifications[:3]
            ])
        
        # Prepare compliance context
        compliance_context = ""
        if compliance_result.violations:
            compliance_context = "\n".join([
                f"Violation: {v.description} - Severity: {v.severity}"
                for v in compliance_result.violations[:3]
            ])
        
        prompt = f"""
        Analyze this customer support interaction for strengths and weaknesses:
        
        CUSTOMER QUERY: {customer_query}
        SUPPORT RESPONSE: {support_response}
        
        FACT VERIFICATION RESULTS:
        {verification_context}
        
        COMPLIANCE ISSUES:
        {compliance_context}
        
        Return a JSON object with strengths and weaknesses:
        {{
            "strengths": [
                "Specific strength 1",
                "Specific strength 2"
            ],
            "weaknesses": [
                "Specific weakness 1", 
                "Specific weakness 2"
            ]
        }}
        
        Analyze these aspects:
        1. Factual accuracy and policy compliance
        2. Communication tone and professionalism
        3. Information completeness and clarity
        4. Customer empathy and understanding
        5. Problem resolution effectiveness
        6. Response structure and organization
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.FEEDBACK_GENERATION_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000
            )
            
            import json
            analysis = json.loads(response.choices[0].message.content)
            
            strengths = analysis.get("strengths", [])
            weaknesses = analysis.get("weaknesses", [])
            
            logger.info(f"Identified {len(strengths)} strengths and {len(weaknesses)} weaknesses")
            return strengths, weaknesses
            
        except Exception as e:
            logger.error(f"Response quality analysis failed: {str(e)}")
            return [], ["Unable to analyze response quality"]
    
    async def _generate_improvement_suggestions(
        self,
        support_response: str,
        customer_query: str,
        weaknesses: List[str],
        violations: List[ComplianceViolation]
    ) -> List[ImprovementSuggestion]:
        """Generate specific, actionable improvement suggestions"""
        
        suggestions = []
        
        # Generate suggestions based on weaknesses
        if weaknesses:
            weakness_context = "\n".join(weaknesses)
            
            prompt = f"""
            Generate specific improvement suggestions for this support response:
            
            CUSTOMER QUERY: {customer_query}
            SUPPORT RESPONSE: {support_response}
            
            IDENTIFIED WEAKNESSES:
            {weakness_context}
            
            Return JSON array of improvement suggestions:
            [
                {{
                    "category": "accuracy|communication|completeness|empathy|efficiency|personalization",
                    "priority": "high|medium|low",
                    "description": "Clear description of what to improve",
                    "specific_action": "Specific action to take",
                    "expected_impact": "What improvement this will bring",
                    "implementation_effort": "low|medium|high"
                }}
            ]
            
            Focus on actionable, specific suggestions that can be immediately implemented.
            """
            
            try:
                response = await self.openai_client.chat.completions.create(
                    model=settings.FEEDBACK_GENERATION_MODEL,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3,
                    max_tokens=1500
                )
                
                import json
                suggestions_data = json.loads(response.choices[0].message.content)
                
                for suggestion_data in suggestions_data:
                    suggestions.append(ImprovementSuggestion(
                        category=suggestion_data.get("category", "general"),
                        priority=suggestion_data.get("priority", "medium"),
                        description=suggestion_data.get("description", ""),
                        specific_action=suggestion_data.get("specific_action", ""),
                        expected_impact=suggestion_data.get("expected_impact", ""),
                        implementation_effort=suggestion_data.get("implementation_effort", "medium")
                    ))
                
            except Exception as e:
                logger.error(f"Improvement suggestions generation failed: {str(e)}")
        
        # Add suggestions based on compliance violations
        for violation in violations:
            if violation.severity in ["critical", "major"]:
                suggestions.append(ImprovementSuggestion(
                    category="compliance",
                    priority="high" if violation.severity == "critical" else "medium",
                    description=f"Address {violation.rule_type} violation",
                    specific_action=violation.suggested_correction,
                    expected_impact="Improved policy compliance and accuracy",
                    implementation_effort="low"
                ))
        
        return suggestions
    
    async def _generate_response_suggestion(
        self,
        support_response: str,
        customer_query: str,
        improvement_suggestions: List[ImprovementSuggestion]
    ) -> Optional[ResponseSuggestion]:
        """Generate an improved version of the response"""
        
        if not improvement_suggestions:
            return None
        
        # Create improvement context
        improvements_context = "\n".join([
            f"- {suggestion.description}: {suggestion.specific_action}"
            for suggestion in improvement_suggestions[:5]
        ])
        
        prompt = f"""
        Rewrite this support response incorporating the suggested improvements:
        
        ORIGINAL CUSTOMER QUERY: {customer_query}
        ORIGINAL RESPONSE: {support_response}
        
        IMPROVEMENTS TO INCORPORATE:
        {improvements_context}
        
        Return a JSON object with the improved response:
        {{
            "improved_response": "The rewritten response text",
            "key_improvements": ["Improvement 1", "Improvement 2"],
            "tone_adjustments": ["Tone change 1", "Tone change 2"],
            "added_information": ["Added info 1", "Added info 2"],
            "confidence": 0.0-1.0
        }}
        
        Guidelines for the improved response:
        1. Maintain the core message and intent
        2. Improve tone, clarity, and professionalism
        3. Add missing information identified in suggestions
        4. Ensure policy accuracy and compliance
        5. Make it more empathetic and customer-focused
        6. Keep it concise but complete
        """
        
        try:
            response = await self.openai_client.chat.completions.create(
                model=settings.FEEDBACK_GENERATION_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=2000
            )
            
            import json
            suggestion_data = json.loads(response.choices[0].message.content)
            
            return ResponseSuggestion(
                improved_response=suggestion_data.get("improved_response", ""),
                key_improvements=suggestion_data.get("key_improvements", []),
                tone_adjustments=suggestion_data.get("tone_adjustments", []),
                added_information=suggestion_data.get("added_information", []),
                confidence=suggestion_data.get("confidence", 0.7)
            )
            
        except Exception as e:
            logger.error(f"Response suggestion generation failed: {str(e)}")
            return None
    
    async def _generate_training_recommendations(
        self,
        weaknesses: List[str],
        violations: List[ComplianceViolation]
    ) -> List[str]:
        """Generate training recommendations based on identified issues"""
        
        recommendations = []
        
        # Analyze weakness patterns
        weakness_patterns = {
            "communication": ["tone", "professional", "empathy", "clarity"],
            "policy": ["policy", "guideline", "compliance", "accuracy"],
            "completeness": ["information", "detail", "complete", "missing"],
            "efficiency": ["time", "speed", "quick", "efficient"]
        }
        
        weakness_text = " ".join(weaknesses).lower()
        
        for category, keywords in weakness_patterns.items():
            if any(keyword in weakness_text for keyword in keywords):
                if category == "communication":
                    recommendations.append("Customer communication and empathy training")
                elif category == "policy":
                    recommendations.append("Policy and compliance refresher training")
                elif category == "completeness":
                    recommendations.append("Information gathering and response completeness training")
                elif category == "efficiency":
                    recommendations.append("Efficiency and time management training")
        
        # Add recommendations based on violation types
        violation_types = set(v.rule_type for v in violations)
        
        if "policy_accuracy" in violation_types:
            recommendations.append("Product knowledge and policy accuracy training")
        if "communication_tone" in violation_types:
            recommendations.append("Professional communication standards training")
        if "information_completeness" in violation_types:
            recommendations.append("Response checklist and completeness training")
        
        # Remove duplicates and return
        return list(set(recommendations))
    
    async def _generate_overall_feedback(
        self,
        strengths: List[str],
        weaknesses: List[str],
        improvement_suggestions: List[ImprovementSuggestion]
    ) -> str:
        """Generate overall feedback summary"""
        
        if not strengths and not weaknesses:
            return "Response meets basic standards. Continue following current practices."
        
        feedback_parts = []
        
        if strengths:
            feedback_parts.append(f"Strengths: {', '.join(strengths[:3])}")
        
        if weaknesses:
            feedback_parts.append(f"Areas for improvement: {', '.join(weaknesses[:3])}")
        
        if improvement_suggestions:
            high_priority = [s for s in improvement_suggestions if s.priority == "high"]
            if high_priority:
                feedback_parts.append(f"Priority actions: {', '.join([s.description for s in high_priority[:2]])}")
        
        return ". ".join(feedback_parts) + "."
