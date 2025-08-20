import os
import json
import logging
import base64
from typing import Dict, Any, Optional
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from app.utils.state import load_state, save_state
from app.config import settings

log = logging.getLogger(__name__)
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", 
                "https://www.googleapis.com/auth/gmail.modify"]
WEBHOOK_URL = os.getenv("WEBHOOK_PUBLIC_URL", "").replace("/webhook/drive", "/webhook/gmail")

# In-memory cache for deduplication
_processed_messages: Dict[str, float] = {}
DEDUP_WINDOW_SECONDS = 60  # Ignore duplicate events within 60 seconds

def build_gmail_client():
    """Build authenticated Gmail API client using settings"""
    try:
        # Load credentials from secure location
        gmail_creds_path = settings.get_gmail_credentials_path()
        creds = Credentials.from_authorized_user_file(gmail_creds_path, GMAIL_SCOPES)
            
        # Refresh credentials if needed
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                log.error("Gmail credentials are invalid and cannot be refreshed")
                return None
                
        return build("gmail", "v1", credentials=creds, cache_discovery=False)
    except Exception as e:
        log.error(f"Failed to build Gmail client: {e}")
        return None

def register_gmail_watch() -> Dict[str, Any]:
    """
    Register Gmail push notifications using Pub/Sub.
    Note: This requires Google Cloud Pub/Sub setup.
    """
    gmail = build_gmail_client()
    if not gmail:
        return {"error": "Failed to build Gmail client"}
    
    try:
        # For Gmail push notifications, you need a Pub/Sub topic
        # This is a simplified version - actual implementation needs Pub/Sub setup
        request_body = {
            'labelIds': ['INBOX'],  # Monitor inbox
            'topicName': f'projects/{os.getenv("GOOGLE_CLOUD_PROJECT")}/topics/gmail-notifications'
        }
        
        result = gmail.users().watch(userId='me', body=request_body).execute()
        log.info(f"Gmail watch registered: {result}")
        
        # Save watch details to state
        state = load_state()
        state['gmail_watch'] = {
            'historyId': result.get('historyId'),
            'expiration': result.get('expiration')
        }
        save_state(state)
        
        return result
    except Exception as e:
        log.error(f"Failed to register Gmail watch: {e}")
        return {"error": str(e)}

def stop_gmail_watch() -> Dict[str, Any]:
    """Stop Gmail push notifications"""
    gmail = build_gmail_client()
    if not gmail:
        return {"error": "Failed to build Gmail client"}
    
    try:
        result = gmail.users().stop(userId='me').execute()
        log.info("Gmail watch stopped")
        
        # Clear watch details from state
        state = load_state()
        if 'gmail_watch' in state:
            del state['gmail_watch']
        save_state(state)
        
        return {"status": "stopped"}
    except Exception as e:
        log.error(f"Failed to stop Gmail watch: {e}")
        return {"error": str(e)}

def _is_duplicate_message(message_id: str) -> bool:
    """Check if we've recently processed this message"""
    import time
    current_time = time.time()
    
    # Clean old entries
    expired_keys = [k for k, timestamp in _processed_messages.items() 
                   if current_time - timestamp > DEDUP_WINDOW_SECONDS]
    for key in expired_keys:
        del _processed_messages[key]
    
    # Check if recently processed
    if message_id in _processed_messages:
        time_since_last = current_time - _processed_messages[message_id]
        log.info(f"🔄 Duplicate message {message_id} (last processed {time_since_last:.1f}s ago) - SKIPPING")
        return True
    
    # Mark as processed
    _processed_messages[message_id] = current_time
    return False

def get_message_details(message_id: str) -> Optional[Dict[str, Any]]:
    """Get detailed information about a Gmail message"""
    gmail = build_gmail_client()
    if not gmail:
        return None
    
    try:
        message = gmail.users().messages().get(
            userId='me', 
            id=message_id, 
            format='full'
        ).execute()
        
        return parse_gmail_message(message)
    except Exception as e:
        log.error(f"Failed to get message details for {message_id}: {e}")
        return None

def parse_gmail_message(message: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Gmail message into structured format"""
    headers = message.get('payload', {}).get('headers', [])
    
    # Extract headers
    subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
    sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
    recipient = next((h['value'] for h in headers if h['name'].lower() == 'to'), '')
    date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
    message_id_header = next((h['value'] for h in headers if h['name'].lower() == 'message-id'), '')
    
    # Extract body (simplified - handles text/plain)
    body = extract_message_body(message.get('payload', {}))
    
    return {
        'message_id': message['id'],
        'thread_id': message['threadId'],
        'history_id': message.get('historyId'),
        'subject': subject,
        'sender': sender,
        'recipient': recipient,
        'date': date,
        'message_id_header': message_id_header,
        'body_preview': body[:200] + '...' if len(body) > 200 else body,
        'labels': message.get('labelIds', []),
        'snippet': message.get('snippet', '')
    }

def extract_message_body(payload: Dict[str, Any]) -> str:
    """Extract text body from Gmail message payload"""
    body = ""
    
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part.get('body', {}).get('data', '')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                    break
    elif payload.get('mimeType') == 'text/plain':
        data = payload.get('body', {}).get('data', '')
        if data:
            body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    
    return body

def process_gmail_notification(notification_data: Dict[str, Any]) -> None:
    """
    Process Gmail push notification.
    This is called when a webhook is received from Pub/Sub.
    """
    try:
        # Decode the Pub/Sub message
        if 'message' in notification_data:
            message_data = notification_data['message']
            if 'data' in message_data:
                # Decode base64 data
                decoded_data = base64.b64decode(message_data['data']).decode('utf-8')
                gmail_data = json.loads(decoded_data)
                
                email_address = gmail_data.get('emailAddress')
                history_id = gmail_data.get('historyId')
                
                log.info(f"📧 Gmail notification for {email_address}, historyId: {history_id}")
                
                # Get recent changes using history API
                process_gmail_history(history_id)
                
    except Exception as e:
        log.error(f"Failed to process Gmail notification: {e}")

def process_gmail_history(start_history_id: str) -> None:
    """Process Gmail history to get actual message changes"""
    gmail = build_gmail_client()
    if not gmail:
        return
    
    try:
        # Get history of changes
        history = gmail.users().history().list(
            userId='me',
            startHistoryId=start_history_id,
            historyTypes=['messageAdded', 'messageDeleted']
        ).execute()
        
        changes = history.get('history', [])
        
        for change in changes:
            # Process added messages (new emails)
            if 'messagesAdded' in change:
                for msg_added in change['messagesAdded']:
                    message_id = msg_added['message']['id']
                    
                    if _is_duplicate_message(message_id):
                        continue
                    
                    # Get full message details
                    message_details = get_message_details(message_id)
                    if message_details:
                        log.info(f"📨 NEW EMAIL: {message_details['subject']} from {message_details['sender']}")
                        
                        # TODO: Add your email processing logic here
                        process_new_email(message_details)
            
            # Process deleted messages
            if 'messagesDeleted' in change:
                for msg_deleted in change['messagesDeleted']:
                    message_id = msg_deleted['message']['id']
                    log.info(f"🗑️ EMAIL DELETED: {message_id}")
                    
    except Exception as e:
        log.error(f"Failed to process Gmail history: {e}")

def process_new_email(email_data: Dict[str, Any]) -> None:
    """
    Process a new email. Replace with your business logic.
    
    Args:
        email_data: Parsed email data with sender, recipient, subject, etc.
    """
    log.info(f"🚀 Processing new email: {email_data['subject']}")
    
    # TODO: Replace with your actual processing logic
    # Examples:
    # - Classify email type
    # - Extract important information
    # - Send notifications
    # - Update database
    # - Trigger workflows
    
    print(f"✅ Email processed: {email_data['subject']} from {email_data['sender']} to {email_data['recipient']}")
