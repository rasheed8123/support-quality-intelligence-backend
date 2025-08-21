"""
Claim extraction engine for the Support Quality Intelligence system.
Extracts verifiable claims from support responses using OpenAI GPT-4o.
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)


class Claim(BaseModel):
    """Individual claim extracted from support response"""
    text: str
    claim_type: str  # factual_data, policy_statement, procedure_step, timeline_info, contact_info
    verification_priority: str  # high, medium, low
    expected_evidence_type: str  # numerical_data, policy_document, procedure_guide, contact_directory
    specificity_level: str  # specific, general, vague
    context_start: int
    context_end: int
    entities: List[str] = []
    confidence: float = 0.0


class ClaimExtractor:
    """
    Advanced claim extraction engine using OpenAI GPT-4o.
    
    Extracts discrete, verifiable claims from support responses
    that can be fact-checked against authoritative documentation.
    """
    
    def __init__(self):
        """Initialize the claim extractor with OpenAI client"""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.CLAIM_EXTRACTION_MODEL
        
        # Educational domain-specific claim patterns
        self.claim_patterns = {
            "course_fees": ["cost", "fee", "price", "₹", "rupees", "payment"],
            "duration": ["months", "weeks", "days", "duration", "length", "time"],
            "placement": ["placement", "job", "hiring", "companies", "partners"],
            "requirements": ["prerequisite", "requirement", "eligibility", "qualification"],
            "certification": ["certificate", "certification", "accredited", "recognized"],
            "support": ["support", "help", "assistance", "guidance", "mentor"]
        }
        
        logger.info(f"Claim extractor initialized with model: {self.model}")
    
    async def extract_claims(
        self, 
        response_text: str, 
        customer_query: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[Claim]:
        """
        Extract verifiable claims from support response.
        
        Args:
            response_text: The support agent's response
            customer_query: Original customer question for context
            context: Additional context information
            
        Returns:
            List of extracted claims with metadata
        """
        logger.info(f"Extracting claims from response of {len(response_text)} characters")
        
        try:
            # Build extraction prompt
            extraction_prompt = self._build_extraction_prompt(
                response_text, customer_query, context
            )
            
            # Call OpenAI for claim extraction
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user", 
                        "content": extraction_prompt
                    }
                ],
                temperature=0.1,  # Low temperature for consistent extraction
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            result = json.loads(response.choices[0].message.content)
            claims = self._parse_claims_response(result, response_text)
            
            logger.info(f"Successfully extracted {len(claims)} claims")
            return claims
            
        except Exception as e:
            logger.error(f"Claim extraction failed: {str(e)}", exc_info=True)
            # Return fallback claims for robustness
            return self._extract_fallback_claims(response_text)
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for claim extraction"""
        return """You are an expert claim extraction system for educational support responses.

Your task is to extract discrete, verifiable claims from support agent responses that can be fact-checked against authoritative documentation.

Focus on extracting claims about:
- Course fees, costs, and pricing
- Program duration and schedules  
- Admission requirements and procedures
- Placement statistics and company partnerships
- Assessment policies and grading systems
- Support response times and procedures
- Instructor qualifications and experience
- Certification details and validity

For each claim, determine:
1. Claim type: factual_data, policy_statement, procedure_step, timeline_info, contact_info
2. Verification priority: high (critical facts), medium (important details), low (general info)
3. Expected evidence type: numerical_data, policy_document, procedure_guide, contact_directory
4. Specificity level: specific (exact numbers/dates), general (approximate), vague (unclear)

Extract entities like numbers, dates, names, percentages, and amounts.

Return valid JSON with a "claims" array containing claim objects."""
    
    def _build_extraction_prompt(
        self, 
        response_text: str, 
        customer_query: Optional[str],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Build the extraction prompt with context"""
        
        prompt_parts = [
            "Extract all verifiable claims from this support response:\n",
            f"SUPPORT RESPONSE: \"{response_text}\"\n"
        ]
        
        if customer_query:
            prompt_parts.append(f"CUSTOMER QUERY: \"{customer_query}\"\n")
        
        if context:
            prompt_parts.append(f"CONTEXT: {json.dumps(context)}\n")
        
        prompt_parts.extend([
            "\nFor each claim, provide:",
            "- text: exact claim text from the response",
            "- claim_type: factual_data, policy_statement, procedure_step, timeline_info, or contact_info", 
            "- verification_priority: high, medium, or low",
            "- expected_evidence_type: numerical_data, policy_document, procedure_guide, or contact_directory",
            "- specificity_level: specific, general, or vague",
            "- context_start: character position where claim starts",
            "- context_end: character position where claim ends", 
            "- entities: list of specific entities (numbers, dates, names, amounts)",
            "- confidence: confidence score 0.0 to 1.0",
            "\nReturn JSON format with 'claims' array."
        ])
        
        return "\n".join(prompt_parts)
    
    def _parse_claims_response(self, result: Dict[str, Any], original_text: str) -> List[Claim]:
        """Parse OpenAI response into Claim objects"""
        claims = []
        
        if "claims" not in result:
            logger.warning("No 'claims' key in OpenAI response")
            return claims
        
        for claim_data in result["claims"]:
            try:
                # Validate and clean claim data
                claim_text = claim_data.get("text", "").strip()
                if not claim_text or len(claim_text) < 5:
                    continue
                
                # Ensure context positions are valid
                context_start = max(0, claim_data.get("context_start", 0))
                context_end = min(len(original_text), claim_data.get("context_end", len(claim_text)))
                
                # Validate claim type
                valid_types = ["factual_data", "policy_statement", "procedure_step", "timeline_info", "contact_info"]
                claim_type = claim_data.get("claim_type", "factual_data")
                if claim_type not in valid_types:
                    claim_type = "factual_data"
                
                # Ensure entities are strings
                entities = claim_data.get("entities", [])
                if entities:
                    entities = [str(entity) for entity in entities]

                # Create claim object
                claim = Claim(
                    text=claim_text,
                    claim_type=claim_type,
                    verification_priority=claim_data.get("verification_priority", "medium"),
                    expected_evidence_type=claim_data.get("expected_evidence_type", "numerical_data"),
                    specificity_level=claim_data.get("specificity_level", "general"),
                    context_start=context_start,
                    context_end=context_end,
                    entities=entities,
                    confidence=float(claim_data.get("confidence", 0.8))
                )
                
                claims.append(claim)
                
            except Exception as e:
                logger.warning(f"Failed to parse claim: {str(e)}")
                continue
        
        return claims
    
    def _extract_fallback_claims(self, response_text: str) -> List[Claim]:
        """Extract basic claims using pattern matching as fallback"""
        logger.info("Using fallback claim extraction")
        
        claims = []
        words = response_text.split()
        
        # Look for monetary amounts
        for i, word in enumerate(words):
            if "₹" in word or "rupees" in word.lower():
                context_start = response_text.find(word)
                context_end = context_start + len(word)
                
                # Expand context to include surrounding words
                start_idx = max(0, i - 3)
                end_idx = min(len(words), i + 4)
                claim_text = " ".join(words[start_idx:end_idx])
                
                claims.append(Claim(
                    text=claim_text,
                    claim_type="factual_data",
                    verification_priority="high",
                    expected_evidence_type="numerical_data",
                    specificity_level="specific",
                    context_start=context_start,
                    context_end=context_end,
                    entities=[word],
                    confidence=0.7
                ))
        
        # Look for duration mentions
        duration_keywords = ["months", "weeks", "days", "duration"]
        for keyword in duration_keywords:
            if keyword in response_text.lower():
                # Find the sentence containing the keyword
                sentences = response_text.split(".")
                for sentence in sentences:
                    if keyword in sentence.lower():
                        claims.append(Claim(
                            text=sentence.strip(),
                            claim_type="factual_data",
                            verification_priority="medium",
                            expected_evidence_type="numerical_data",
                            specificity_level="general",
                            context_start=response_text.find(sentence),
                            context_end=response_text.find(sentence) + len(sentence),
                            entities=[keyword],
                            confidence=0.6
                        ))
                        break
        
        return claims[:5]  # Limit fallback claims
    
    async def validate_claims(self, claims: List[Claim]) -> List[Claim]:
        """
        Validate and filter extracted claims for quality.
        
        Args:
            claims: List of extracted claims
            
        Returns:
            Filtered list of high-quality claims
        """
        validated_claims = []
        
        for claim in claims:
            # Skip very short or vague claims
            if len(claim.text) < 10:
                continue
            
            # Skip claims with very low confidence
            if claim.confidence < 0.3:
                continue
            
            # Skip duplicate claims
            if any(self._are_claims_similar(claim, existing) for existing in validated_claims):
                continue
            
            validated_claims.append(claim)
        
        logger.info(f"Validated {len(validated_claims)} out of {len(claims)} claims")
        return validated_claims
    
    def _are_claims_similar(self, claim1: Claim, claim2: Claim) -> bool:
        """Check if two claims are similar enough to be considered duplicates"""
        # Simple similarity check based on text overlap
        words1 = set(claim1.text.lower().split())
        words2 = set(claim2.text.lower().split())
        
        if len(words1) == 0 or len(words2) == 0:
            return False
        
        overlap = len(words1.intersection(words2))
        similarity = overlap / min(len(words1), len(words2))
        
        return similarity > 0.7
