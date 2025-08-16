from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from app.config import settings
import base64
import email

class GmailIngestion:
    def __init__(self):
        creds = Credentials.from_authorized_user_file(
            settings.GMAIL_CREDENTIALS_FILE,
            ["https://www.googleapis.com/auth/gmail.readonly"]
        )
        self.service = build("gmail", "v1", credentials=creds)
        
    async def fetch_emails(self, query: str = None):
        """Fetch emails from Gmail"""
        results = (
            self.service.users()
            .messages()
            .list(userId="me", q=query)
            .execute()
        )
        
        messages = results.get("messages", [])
        emails = []
        
        for message in messages:
            msg = (
                self.service.users()
                .messages()
                .get(userId="me", id=message["id"], format="full")
                .execute()
            )
            emails.append(self._parse_message(msg))
            
        return emails
        
    def _parse_message(self, message):
        """Parse Gmail message into structured format"""
        headers = message["payload"]["headers"]
        subject = next(
            (h["value"] for h in headers if h["name"].lower() == "subject"),
            ""
        )
        sender = next(
            (h["value"] for h in headers if h["name"].lower() == "from"),
            ""
        )
        
        parts = message["payload"].get("parts", [])
        body = ""
        
        for part in parts:
            if part["mimeType"] == "text/plain":
                body = base64.urlsafe_b64decode(
                    part["body"]["data"]
                ).decode("utf-8")
                break
                
        return {
            "message_id": message["id"],
            "thread_id": message["threadId"],
            "subject": subject,
            "sender": sender,
            "body": body
        }
