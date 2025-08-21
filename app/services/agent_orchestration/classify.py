from app.services.classification_models import classify_category, classify_priority, classify_tone, classify_issue
from app.db.models.emails import Email
from app.db.models.email_analysis import InboundEmailAnalysis, OutboundEmailAnalysis
from app.db.session import SessionLocal
from datetime import datetime
import logging
import asyncio
import re
from typing import Tuple, Optional

# Import RAG components
from app.services.core.pipeline_orchestrator import PipelineOrchestrator
from app.api.models.request_models import SupportVerificationRequest, VerificationLevel

# Import Alert components
from app.services.alerts.alert_service import AlertService, AlertConfiguration

logger = logging.getLogger(__name__)

async def classify_email(email_id: str, from_email: str, thread_id: str, subject: str, body: str, is_inbound: bool = True, thread_context: str = None):
    """
    Classify email according to the flow.md logic and write to database.

    Args:
        email_id: Unique identifier for the email
        from_email: Sender email address
        thread_id: Thread identifier
        subject: Email subject
        body: Email body content
        is_inbound: True if inbound (inbox), False if outbound (sent)
        thread_context: Full email thread context for outbound processing
    """
    # 🔍 DETAILED LOGGING: Function entry
    logger.info(f"🎯 CLASSIFY_EMAIL STARTED")
    logger.info(f"   Email ID: {email_id}")
    logger.info(f"   From: {from_email}")
    logger.info(f"   Thread ID: {thread_id}")
    logger.info(f"   Subject: {subject}")
    logger.info(f"   Is Inbound: {is_inbound}")
    logger.info(f"   Body Length: {len(body)} characters")
    logger.info(f"   Thread Context Length: {len(thread_context) if thread_context else 0} characters")
    logger.info(f"   Direction: {'INBOUND (Customer → Support)' if is_inbound else 'OUTBOUND (Support → Customer)'}")

    db = SessionLocal()
    try:
        # 🔍 DETAILED LOGGING: Database operations
        logger.info(f"   📊 Creating email record in database...")

        # Create email record
        email = Email(
            email_identifier=email_id,
            is_inbound=is_inbound,
            thread_id=thread_id,
            created_at=datetime.utcnow()
        )
        db.add(email)
        db.flush()  # Get the email ID

        logger.info(f"   ✅ Email record created with ID: {email.id}")
        logger.info(f"   📋 Email record details:")
        logger.info(f"      - email_identifier: {email.email_identifier}")
        logger.info(f"      - is_inbound: {email.is_inbound}")
        logger.info(f"      - thread_id: {email.thread_id}")
        logger.info(f"      - created_at: {email.created_at}")
        
        if is_inbound:
            # 🔍 DETAILED LOGGING: Inbound processing
            logger.info(f"   📥 PROCESSING INBOUND EMAIL (Customer → Support)")
            logger.info(f"      This will trigger spam/priority/issue classification")
            await _process_inbound_email(db, email, from_email, subject, body)
            logger.info(f"   ✅ INBOUND EMAIL PROCESSING COMPLETED")
        else:
            # 🔍 DETAILED LOGGING: Outbound processing
            logger.info(f"   📤 PROCESSING OUTBOUND EMAIL (Support → Customer)")
            logger.info(f"      This will trigger RAG verification pipeline")
            # Outbound email processing (sent) with RAG verification
            # Use await since we're now in an async function
            await _process_outbound_email(db, email, from_email, subject, body, thread_context)
            logger.info(f"   ✅ OUTBOUND EMAIL PROCESSING COMPLETED")
        
        db.commit()
        logger.info(f"Successfully classified and stored email {email_id}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error classifying email {email_id}: {str(e)}")
        raise
    finally:
        db.close()

async def _process_inbound_email(db, email, from_email: str, subject: str, body: str):
    """Process inbound email according to flow.md logic."""
    # 🔍 DETAILED LOGGING: Inbound processing start
    logger.info(f"   📥 _PROCESS_INBOUND_EMAIL STARTED")
    logger.info(f"      Email ID: {email.email_identifier}")
    logger.info(f"      From: {from_email}")
    logger.info(f"      Subject: {subject}")
    logger.info(f"      Body: {body[:200]}{'...' if len(body) > 200 else ''}")

    email_text = f"{subject} {body}"
    logger.info(f"      Combined text length: {len(email_text)} characters")

    # Step 1: Spam classification
    logger.info(f"      🔍 STEP 1: Spam classification")
    spam_result = classify_category(email_text)
    email_type = spam_result.get("category", "query")  # Default to query if classification fails
    logger.info(f"         Spam result: {spam_result}")
    logger.info(f"         Email type: {email_type}")

    if email_type == "spam":
        logger.info(f"         ❌ EMAIL CLASSIFIED AS SPAM - Creating spam record")
        # Create analysis record for spam emails too
        inbound_analysis = InboundEmailAnalysis(
            email_id=email.email_identifier,
            from_email=from_email,
            type=email_type,  # "spam"
            priority="low",   # Default priority for spam
            category="spam",  # Default category for spam
            responded=False,
            created_at=datetime.utcnow()
        )
        db.add(inbound_analysis)
        db.commit()
        logger.info(f"         ✅ Spam email {email.email_identifier} stored in inbound_email_analysis")
        logger.info(f"   📥 _PROCESS_INBOUND_EMAIL COMPLETED (SPAM)")
        return

    # Step 2: Priority classification (only for non-spam)
    logger.info(f"      🔍 STEP 2: Priority classification")
    priority_result = classify_priority(email_text)
    priority = priority_result.get("priority", "medium")  # Default to medium
    logger.info(f"         Priority result: {priority_result}")
    logger.info(f"         Priority: {priority}")

    # Step 3: Issue classification for category
    logger.info(f"      🔍 STEP 3: Issue classification")
    issue_result = await classify_issue(email_text)
    category = issue_result if issue_result else "others"  # Use issue classification directly
    logger.info(f"         Issue result: {issue_result}")
    logger.info(f"         Category: {category}")

    # Create inbound analysis record
    logger.info(f"      💾 CREATING INBOUND ANALYSIS RECORD")
    inbound_analysis = InboundEmailAnalysis(
        email_id=email.email_identifier,
        from_email=from_email,
        type=email_type,
        priority=priority,
        category=category,
        responded=False,
        created_at=datetime.utcnow()
    )

    db.add(inbound_analysis)
    db.commit()

    logger.info(f"         ✅ INBOUND ANALYSIS STORED:")
    logger.info(f"            - email_id: {inbound_analysis.email_id}")
    logger.info(f"            - from_email: {inbound_analysis.from_email}")
    logger.info(f"            - type: {inbound_analysis.type}")
    logger.info(f"            - priority: {inbound_analysis.priority}")
    logger.info(f"            - category: {inbound_analysis.category}")
    logger.info(f"            - responded: {inbound_analysis.responded}")
    logger.info(f"            - created_at: {inbound_analysis.created_at}")

    logger.info(f"   📥 _PROCESS_INBOUND_EMAIL COMPLETED (NON-SPAM)")
    logger.info(f"      Final classification: {email_type}, priority: {priority}, category: {category}")

    # ALERT TRIGGER: Schedule SLA monitoring for non-spam emails
    if email_type != "spam":
        try:
            # Determine SLA threshold based on priority
            if "high" in priority.lower():
                threshold_hours = AlertConfiguration.SLA_THRESHOLDS["high_priority"]
                priority_level = "high"
            elif "medium" in priority.lower():
                threshold_hours = AlertConfiguration.SLA_THRESHOLDS["medium_priority"]
                priority_level = "medium"
            else:
                threshold_hours = AlertConfiguration.SLA_THRESHOLDS["low_priority"]
                priority_level = "low"

            # Note: In a production system, you'd schedule this with a job queue
            # For now, we'll rely on the background scheduler to check SLA breaches
            logger.info(f"SLA monitoring scheduled for {priority_level} priority email {email.email_identifier} (threshold: {threshold_hours}h)")

        except Exception as e:
            logger.error(f"Failed to schedule SLA monitoring for email {email.email_identifier}: {e}")




# SHUBHAM CHECK THIS
# SHUBHAM CHECK THIS
# SHUBHAM CHECK THIS
# SHUBHAM CHECK THIS
# SHUBHAM CHECK THIS
# SHUBHAM CHECK THIS
# SHUBHAM CHECK THIS

async def _process_outbound_email(db, email, from_email: str, subject: str, body: str, thread_context: str = None):
    """
    Process outbound email with RAG verification according to flow.md logic.

    Args:
        db: Database session
        email: Email model instance
        from_email: Sender email address
        subject: Email subject
        body: Email body content (support response)
        thread_context: Previous email thread context (customer query + history)
    """
    logger.info(f"Starting RAG verification for outbound email {email.email_identifier}")

    try:
        # Step 1: Extract customer query and context from thread
        customer_query, conversation_context = await _extract_thread_context(
            thread_context, subject, body
        )

        # Step 2: Run RAG verification pipeline
        rag_results = await _run_rag_verification(
            support_response=body,
            customer_query=customer_query,
            conversation_context=conversation_context,
            email_id=email.email_identifier
        )

        # Step 3: Store RAG results in database
        await _store_outbound_analysis(
            db, email, rag_results, from_email
        )

        logger.info(f"RAG verification completed for email {email.email_identifier}")

    except Exception as e:
        logger.error(f"Error in RAG verification for email {email.email_identifier}: {str(e)}")
        # Store minimal analysis on error
        await _store_fallback_analysis(db, email, from_email, str(e))
        raise


async def _extract_thread_context(thread_context: str, subject: str, body: str) -> Tuple[str, str]:
    """
    Extract customer query and conversation context from email thread.

    IMPORTANT: For outbound email verification:
    - Customer Query: The second-to-last message (customer's question we're responding to)
    - Support Response: The last message (our response being verified - passed as 'body')
    - Context: All messages before the customer query

    Args:
        thread_context: Full email thread context
        subject: Email subject
        body: Current email body (support response - chronologically last)

    Returns:
        Tuple of (customer_query, conversation_context)
    """
    try:
        if not thread_context:
            # If no thread context, use subject as customer query
            customer_query = subject or "General inquiry"
            conversation_context = ""
            logger.info("No thread context provided, using subject as customer query")
            return customer_query, conversation_context

        # Parse thread and sort chronologically
        emails_in_thread = _parse_email_thread_chronologically(thread_context)

        if len(emails_in_thread) >= 2:
            # CORRECTED LOGIC:
            # Second-to-last email is the customer query (what we're responding to)
            customer_query = emails_in_thread[-2].get('body', subject)

            # All messages before the customer query as context
            context_messages = emails_in_thread[:-2]  # Exclude last 2 (our response + customer query)
            conversation_context = _format_conversation_context(context_messages)

            logger.info(f"Thread has {len(emails_in_thread)} messages")
            logger.info(f"Customer query (2nd-to-last): {customer_query[:100]}...")
            logger.info(f"Context messages: {len(context_messages)}")

        elif len(emails_in_thread) == 1:
            # Single email in thread - use subject as query
            customer_query = subject or "General inquiry"
            conversation_context = ""
            logger.info("Single email in thread, using subject as customer query")
        else:
            # No emails parsed, fallback to subject
            customer_query = subject or "General inquiry"
            conversation_context = ""
            logger.warning("No emails parsed from thread context")

        return customer_query, conversation_context

    except Exception as e:
        logger.error(f"Error extracting thread context: {str(e)}")
        # Fallback to subject
        return subject or "General inquiry", ""


def _parse_email_thread_chronologically(thread_context) -> list:
    """
    Parse email thread text into individual email messages sorted chronologically.

    Args:
        thread_context: Raw thread text with chronological message data (string or list)

    Returns:
        List of email dictionaries sorted chronologically (oldest first)
    """
    emails = []

    try:
        # Handle different input types
        if thread_context is None:
            return emails

        if isinstance(thread_context, list):
            # If it's already a list, convert to expected format
            if not thread_context:
                return emails

            # Convert list of dicts to string format
            if isinstance(thread_context[0], dict):
                # List of email dicts
                for i, email_dict in enumerate(thread_context):
                    emails.append({
                        'body': email_dict.get('body', ''),
                        'sender': email_dict.get('from', ''),
                        'subject': email_dict.get('subject', ''),
                        'date': email_dict.get('date', ''),
                        'order': i
                    })
                return emails
            else:
                # List of strings, join them
                thread_context = "\n---\n".join(str(item) for item in thread_context)

        if not isinstance(thread_context, str):
            # Convert to string if it's not already
            thread_context = str(thread_context)

        # Split thread context by message separators
        message_blocks = thread_context.split("---\n")

        for i, block in enumerate(message_blocks):
            if not block.strip():
                continue

            # Extract message components
            lines = block.strip().split('\n')
            msg_data = {
                'body': '',
                'sender': 'unknown',
                'date': '',
                'subject': '',
                'order': i
            }

            # Parse header lines and body
            body_lines = []
            in_body = False

            for line in lines:
                line = line.strip()
                if line.startswith('From: '):
                    msg_data['sender'] = line[6:].strip()
                elif line.startswith('Date: '):
                    msg_data['date'] = line[6:].strip()
                elif line.startswith('Subject: '):
                    msg_data['subject'] = line[9:].strip()
                elif line == '' and not in_body:
                    in_body = True  # Empty line indicates start of body
                elif in_body or (not line.startswith(('From:', 'Date:', 'Subject:'))):
                    body_lines.append(line)

            msg_data['body'] = '\n'.join(body_lines).strip()

            # Only add if we have meaningful content
            if len(msg_data['body']) > 10:
                emails.append(msg_data)

        # Sort by date if available, otherwise by order
        emails.sort(key=lambda x: (x.get('date', ''), x.get('order', 0)))

        logger.info(f"Parsed {len(emails)} messages from thread context")

    except Exception as e:
        logger.error(f"Error parsing email thread chronologically: {str(e)}")
        # Fallback to simple parsing
        emails = _parse_email_thread_fallback(thread_context)

    return emails


def _parse_email_thread_fallback(thread_context: str) -> list:
    """
    Fallback parser for email thread text when structured parsing fails.

    Args:
        thread_context: Raw thread text

    Returns:
        List of email dictionaries with sender, body, timestamp
    """
    emails = []

    try:
        # Split by common email separators
        # Look for patterns like "From:", "On [date]", "-----Original Message-----"
        email_separators = [
            r'From:.*?<.*?>',
            r'On.*?wrote:',
            r'-----Original Message-----',
            r'________________________________',
            r'> On.*?wrote:',
        ]

        # Split the thread into individual emails
        parts = [thread_context]
        for separator in email_separators:
            new_parts = []
            for part in parts:
                new_parts.extend(re.split(separator, part, flags=re.IGNORECASE | re.MULTILINE))
            parts = [p.strip() for p in new_parts if p.strip()]

        # Extract meaningful content from each part
        for i, part in enumerate(parts):
            if len(part) > 20:  # Filter out very short fragments
                emails.append({
                    'body': part.strip(),
                    'order': i,
                    'sender': _extract_sender_from_text(part),
                    'date': ''
                })

        # Sort by order (oldest first)
        emails.sort(key=lambda x: x['order'])

        logger.info(f"Fallback parser extracted {len(emails)} messages")

    except Exception as e:
        logger.error(f"Error in fallback email thread parsing: {str(e)}")
        # Final fallback: treat entire context as single email
        emails = [{'body': thread_context, 'order': 0, 'sender': 'unknown', 'date': ''}]

    return emails


def _extract_sender_from_text(email_text: str) -> str:
    """Extract sender information from email text."""
    # Look for email patterns
    email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
    emails = re.findall(email_pattern, email_text)

    if emails:
        return emails[0]

    # Look for "From:" patterns
    from_pattern = r'From:\s*([^\n\r]+)'
    from_match = re.search(from_pattern, email_text, re.IGNORECASE)

    if from_match:
        return from_match.group(1).strip()

    return 'unknown'


def _format_conversation_context(context_messages: list) -> str:
    """Format previous messages into conversation context."""
    if not context_messages:
        return ""

    formatted_context = "Previous conversation:\n\n"

    for i, msg in enumerate(context_messages):
        sender = msg.get('sender', 'unknown')
        body = msg.get('body', '')

        # Truncate very long messages
        if len(body) > 500:
            body = body[:500] + "..."

        formatted_context += f"Message {i+1} from {sender}:\n{body}\n\n"

    return formatted_context


async def _run_rag_verification(
    support_response: str,
    customer_query: str,
    conversation_context: str,
    email_id: str
) -> dict:
    """
    Run the complete RAG verification pipeline for outbound email.

    Args:
        support_response: The email body (agent's response)
        customer_query: Extracted customer question
        conversation_context: Previous conversation history
        email_id: Email identifier for logging

    Returns:
        Dictionary with RAG verification results
    """
    logger.info(f"Running RAG verification for email {email_id}")

    try:
        # Initialize RAG pipeline orchestrator
        orchestrator = PipelineOrchestrator()

        # Create verification request
        verification_request = SupportVerificationRequest(
            support_response=support_response,
            customer_query=customer_query,
            verification_level=VerificationLevel.STANDARD,  # Use STANDARD for email verification
            include_suggestions=True,
            agent_id=f"email_agent_{email_id}",
            ticket_id=email_id,
            subject_areas=_extract_subject_areas(customer_query, support_response),
            min_accuracy_score=0.7,  # Appropriate threshold for STANDARD verification
            require_source_citation=True
        )

        # Add conversation context to the request if available
        if conversation_context:
            # Note: The current SupportVerificationRequest doesn't have a context field
            # The RAG system will use customer_query for context
            logger.info(f"Conversation context available: {len(conversation_context)} characters")

        # Run verification pipeline
        verification_result = await orchestrator.verify_response(
            verification_request,
            email_id
        )

        # Extract key metrics
        rag_results = {
            'overall_score': verification_result.overall_score,
            'verification_status': verification_result.verification_status.value,
            'factual_accuracy_score': verification_result.factual_accuracy.overall_score,
            'compliance_score': verification_result.guideline_compliance.overall_score,
            'total_claims': verification_result.factual_accuracy.total_claims,
            'verified_claims': verification_result.factual_accuracy.verified_claims,
            'unverified_claims': verification_result.factual_accuracy.unverified_claims,
            'insufficient_evidence_claims': verification_result.factual_accuracy.insufficient_evidence_claims,
            'claim_verifications': [
                {
                    'claim_text': cv.claim_text,
                    'status': cv.status.value,
                    'confidence': cv.confidence,
                    'explanation': cv.explanation
                }
                for cv in verification_result.claim_verifications
            ],
            'compliance_violations': len(verification_result.guideline_compliance.violations),
            'compliance_recommendations': len(verification_result.guideline_compliance.recommendations),
            'feedback_summary': verification_result.feedback_summary,
            'improvement_suggestions': verification_result.improvement_suggestions,
            'processing_time_ms': verification_result.processing_time_ms,
            'model_versions': verification_result.model_versions
        }

        logger.info(f"RAG verification completed for {email_id}: "
                   f"Overall score: {rag_results['overall_score']}, "
                   f"Status: {rag_results['verification_status']}")

        return rag_results

    except Exception as e:
        logger.error(f"Error in RAG verification for {email_id}: {str(e)}")
        # Return minimal error result
        return {
            'overall_score': 0.0,
            'verification_status': 'ERROR',
            'factual_accuracy_score': 0.0,
            'compliance_score': 0.0,
            'error': str(e),
            'processing_time_ms': 0
        }


def _extract_subject_areas(customer_query: str, support_response: str) -> list:
    """
    Extract relevant subject areas from customer query and response.
    Only returns valid subject areas as defined in the Pydantic model.

    Args:
        customer_query: Customer's question
        support_response: Agent's response

    Returns:
        List of relevant subject areas (only valid ones)
    """
    # Define subject area keywords - ONLY VALID AREAS
    # Valid areas: data_science, web_development, placement_assistance, fees,
    # assessment, certification, instructors, support_guidelines, course_catalog, general
    subject_keywords = {
        'data_science': ['data science', 'machine learning', 'ml', 'ai', 'analytics', 'python', 'statistics'],
        'web_development': ['web development', 'html', 'css', 'javascript', 'react', 'node', 'frontend', 'backend'],
        'placement_assistance': ['placement', 'job', 'career', 'interview', 'resume', 'hiring', 'employment'],
        'fees': ['fee', 'cost', 'price', 'payment', 'installment', 'scholarship', 'discount', 'refund'],
        'assessment': ['test', 'exam', 'quiz', 'assessment', 'evaluation', 'grade', 'score'],
        'certification': ['certificate', 'certification', 'credential', 'diploma', 'degree'],
        'instructors': ['instructor', 'teacher', 'mentor', 'faculty', 'trainer'],
        'support_guidelines': ['policy', 'guideline', 'rule', 'procedure', 'process', 'support'],
        'course_catalog': ['course', 'curriculum', 'syllabus', 'module', 'chapter', 'content', 'topics', 'catalog']
    }

    # Combine query and response for analysis
    combined_text = f"{customer_query} {support_response}".lower()

    # Find matching subject areas
    relevant_areas = []
    for area, keywords in subject_keywords.items():
        if any(keyword in combined_text for keyword in keywords):
            relevant_areas.append(area)

    # Default to general if no specific areas found
    if not relevant_areas:
        relevant_areas = ['general']

    return relevant_areas


async def _store_outbound_analysis(db, email, rag_results: dict, from_email: str):
    """
    Store RAG verification results in the database.

    Args:
        db: Database session
        email: Email model instance
        rag_results: RAG verification results
        from_email: Sender email address
    """
    try:
        # Determine email type based on content analysis
        email_type = _determine_email_type(rag_results)

        # Extract tone from improvement suggestions or default
        tone = _extract_tone_from_results(rag_results)

        # Create outbound analysis record
        outbound_analysis = OutboundEmailAnalysis(
            email_id=email.email_identifier,
            type=email_type,
            factual_accuracy=rag_results.get('factual_accuracy_score', 0.0),
            guideline_compliance=rag_results.get('compliance_score', 0.0),
            completeness=rag_results.get('overall_score', 0.0),  # Use overall score as completeness proxy
            tone=tone,
            created_at=datetime.utcnow()
        )

        db.add(outbound_analysis)

        logger.info(f"Stored outbound analysis for email {email.email_identifier}: "
                   f"Accuracy: {outbound_analysis.factual_accuracy:.2f}, "
                   f"Compliance: {outbound_analysis.guideline_compliance:.2f}, "
                   f"Completeness: {outbound_analysis.completeness:.2f}")

        # ALERT TRIGGERS: Check for quality issues in outbound responses
        try:
            # ALERT TRIGGER 1: Factual Accuracy Check
            if (outbound_analysis.factual_accuracy is not None and
                outbound_analysis.factual_accuracy < AlertConfiguration.QUALITY_THRESHOLDS["factual_accuracy_min"]):

                await AlertService.create_immediate_alert(
                    alert_type="factual_error",
                    email_id=email.email_identifier,
                    description=f"Factual accuracy score {outbound_analysis.factual_accuracy:.2f} below threshold {AlertConfiguration.QUALITY_THRESHOLDS['factual_accuracy_min']}",
                    current_value=outbound_analysis.factual_accuracy,
                    threshold_value=AlertConfiguration.QUALITY_THRESHOLDS["factual_accuracy_min"],
                    send_notification=False  # Disable email notifications
                )
                logger.warning(f"Factual error alert created for email {email.email_identifier}")

            # ALERT TRIGGER 2: Negative Sentiment Check
            if tone in ["poor", "negative", "unprofessional"]:
                # Convert tone to numeric score for threshold comparison
                tone_score = 0.3 if tone == "poor" else 0.4

                await AlertService.create_immediate_alert(
                    alert_type="negative_sentiment",
                    email_id=email.email_identifier,
                    description=f"Negative sentiment detected in response (tone: {tone})",
                    current_value=tone_score,
                    threshold_value=AlertConfiguration.QUALITY_THRESHOLDS["sentiment_score_min"],
                    send_notification=False  # Disable email notifications
                )
                logger.warning(f"Negative sentiment alert created for email {email.email_identifier}")

        except Exception as alert_error:
            logger.error(f"Failed to create quality alerts for email {email.email_identifier}: {alert_error}")

    except Exception as e:
        logger.error(f"Error storing outbound analysis for {email.email_identifier}: {str(e)}")
        raise


async def _store_fallback_analysis(db, email, from_email: str, error_message: str):
    """
    Store minimal analysis when RAG verification fails.

    Args:
        db: Database session
        email: Email model instance
        from_email: Sender email address
        error_message: Error that occurred
    """
    try:
        # Create minimal outbound analysis record
        outbound_analysis = OutboundEmailAnalysis(
            email_id=email.email_identifier,
            type="unknown",
            factual_accuracy=0.0,
            guideline_compliance=0.0,
            completeness=0.0,
            tone="unknown",
            created_at=datetime.utcnow()
        )

        db.add(outbound_analysis)

        logger.warning(f"Stored fallback analysis for email {email.email_identifier} due to error: {error_message}")

    except Exception as e:
        logger.error(f"Error storing fallback analysis for {email.email_identifier}: {str(e)}")


def _determine_email_type(rag_results: dict) -> str:
    """
    Determine email type based on RAG analysis results.

    Args:
        rag_results: RAG verification results

    Returns:
        Email type string
    """
    # Analyze claims and content to determine type
    total_claims = rag_results.get('total_claims', 0)

    if total_claims > 3:
        return "information"  # Information-heavy response
    elif total_claims > 0:
        return "query"  # Response to specific query
    else:
        return "general"  # General communication


def _extract_tone_from_results(rag_results: dict) -> str:
    """
    Extract tone assessment from RAG results.

    Args:
        rag_results: RAG verification results

    Returns:
        Tone string
    """
    # Check compliance score to infer tone
    compliance_score = rag_results.get('compliance_score', 0.0)

    if compliance_score >= 0.9:
        return "professional"
    elif compliance_score >= 0.7:
        return "appropriate"
    elif compliance_score >= 0.5:
        return "needs_improvement"
    else:
        return "poor"