from services.classification_models import classify_category, classify_priority, classify_tone, classify_issue
from db.models.emails import Email
from db.models.email_analysis import InboundEmailAnalysis, OutboundEmailAnalysis
from db.session import SessionLocal
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def classify_email(email_id: str, from_email: str, thread_id: str, subject: str, body: str, is_inbound: bool = True):
    """
    Classify email according to the flow.md logic and write to database.
    
    Args:
        email_id: Unique identifier for the email
        from_email: Sender email address
        thread_id: Thread identifier
        subject: Email subject
        body: Email body content
        is_inbound: True if inbound (inbox), False if outbound (sent)
    """
    db = SessionLocal()
    try:
        # Create email record
        email = Email(
            email_identifier=email_id,
            is_inbound=is_inbound,
            thread_id=thread_id,
            created_at=datetime.utcnow()
        )
        db.add(email)
        db.flush()  # Get the email ID
        
        if is_inbound:
            # Inbound email processing (inbox)
            _process_inbound_email(db, email, from_email, subject, body)
        else:
            # Outbound email processing (sent)
            _process_outbound_email(db, email, from_email, subject, body)
        
        db.commit()
        logger.info(f"Successfully classified and stored email {email_id}")
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error classifying email {email_id}: {str(e)}")
        raise
    finally:
        db.close()

def _process_inbound_email(db, email, from_email: str, subject: str, body: str):
    """Process inbound email according to flow.md logic."""
    email_text = f"{subject} {body}"
    
    # Step 1: Spam classification
    spam_result = classify_category(email_text)
    email_type = spam_result.get("category", "query")  # Default to query if classification fails
    
    if email_type == "spam":
        # End processing for spam
        logger.info(f"Email {email.email_identifier} classified as spam")
        return
    
    # Step 2: Priority classification (only for non-spam)
    priority_result = classify_priority(email_text)
    priority = priority_result.get("priority", "medium")  # Default to medium
    
    # Step 3: Issue classification for category
    issue_result = classify_issue(email_text)
    category = issue_result if issue_result else "others"  # Use issue classification directly
    
    # Create inbound analysis record
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
    logger.info(f"Inbound email {email.email_identifier} classified as {email_type}, priority: {priority}, category: {category}")




# SHUBHAM CHECK THIS
# SHUBHAM CHECK THIS
# SHUBHAM CHECK THIS
# SHUBHAM CHECK THIS
# SHUBHAM CHECK THIS
# SHUBHAM CHECK THIS
# SHUBHAM CHECK THIS

def _process_outbound_email(db, email, from_email: str, subject: str, body: str):
    """Process outbound email according to flow.md logic."""
    # TODO: Implement outbound email processing logic
    # This will analyze sent emails for quality metrics
    logger.info(f"Outbound email {email.email_identifier} processing - placeholder implementation")
    pass