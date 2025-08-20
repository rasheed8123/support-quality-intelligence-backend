from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import os

from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as UserCredentials
from google_auth_oauthlib.flow import InstalledAppFlow


GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


class GmailClient:
    def __init__(
        self,
        credentials_path: str,
        delegated_subject: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        oauth_token_file: Optional[str] = None,
    ) -> None:
        scopes = scopes or GMAIL_SCOPES
        creds = self._load_credentials(
            credentials_path=credentials_path,
            delegated_subject=delegated_subject,
            scopes=scopes,
            oauth_token_file=oauth_token_file,
        )
        self.service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    @staticmethod
    def _load_credentials(
        credentials_path: str,
        delegated_subject: Optional[str],
        scopes: List[str],
        oauth_token_file: Optional[str],
    ):
        """Load credentials from either a Service Account JSON or OAuth client secret JSON.

        - If the JSON has a "type": "service_account", use domain-wide delegation (if provided).
        - Else treat it as OAuth Client (installed app) and use/refresh token.json.
        """
        import json

        with open(credentials_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if data.get("type") == "service_account":
            creds = service_account.Credentials.from_service_account_file(credentials_path, scopes=scopes)
            if delegated_subject:
                creds = creds.with_subject(delegated_subject)
            return creds

        # OAuth installed app
        if oauth_token_file and os.path.exists(oauth_token_file):
            creds = UserCredentials.from_authorized_user_file(oauth_token_file, scopes)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, scopes=scopes)
            use_console = os.getenv("OAUTH_USE_CONSOLE", "false").lower() in {"1", "true", "yes"}
            if use_console:
                # Manual console flow compatible with older google-auth-oauthlib
                auth_url, _ = flow.authorization_url(
                    access_type="offline",
                    include_granted_scopes="true",
                    prompt="consent",
                )
                print("Please visit this URL to authorize this application:")
                print(auth_url)
                try:
                    code = input("\nEnter the authorization code here: ").strip()
                except Exception:
                    code = ""
                flow.fetch_token(code=code)
                creds = flow.credentials
            else:
                # Starts a local server and tries to open the browser
                port_env = os.getenv("OAUTH_LOCAL_SERVER_PORT")
                port = int(port_env) if port_env else 0
                creds = flow.run_local_server(port=port)
            if oauth_token_file:
                with open(oauth_token_file, "w", encoding="utf-8") as token:
                    token.write(creds.to_json())
        return creds

    def start_watch(
        self,
        topic_name: str,
        label_ids: Optional[List[str]] = None,
        label_filter_action: Optional[str] = None,
    ) -> Dict[str, Any]:
        body: Dict[str, Any] = {"topicName": topic_name}
        if label_ids:
            body["labelIds"] = label_ids
        if label_filter_action in {"include", "exclude"}:
            body["labelFilterBehavior"] = label_filter_action

        return (
            self.service.users()
            .watch(userId="me", body=body)
            .execute()
        )

    def fetch_new_messages_since(self, start_history_id: Optional[str]) -> List[Dict[str, Any]]:
        if not start_history_id:
            # No baseline, skip initial fetch. We'll start from the first push's historyId.
            return []

        message_ids: List[str] = []
        page_token: Optional[str] = None
        while True:
            req = self.service.users().history().list(
                userId="me",
                startHistoryId=start_history_id,
                historyTypes=["messageAdded"],
                pageToken=page_token,
            )
            resp = req.execute()
            for h in resp.get("history", []):
                for m in h.get("messagesAdded", []):
                    msg = m.get("message") or {}
                    msg_id = msg.get("id")
                    if msg_id:
                        message_ids.append(msg_id)
            page_token = resp.get("nextPageToken")
            if not page_token:
                break

        # Deduplicate while preserving order
        seen = set()
        deduped_ids = []
        for mid in message_ids:
            if mid not in seen:
                seen.add(mid)
                deduped_ids.append(mid)

        messages: List[Dict[str, Any]] = []
        fetched_threads: Dict[str, Dict[str, Any]] = {}
        for msg_id in deduped_ids:
            try:
                msg = (
                    self.service.users()
                    .messages()
                    .get(userId="me", id=msg_id, format="metadata", metadataHeaders=["From", "To", "Subject", "Date", "Message-Id"])  # type: ignore[arg-type]
                    .execute()
                )
            except Exception as e:
                # Handle 404 errors gracefully - message may have been deleted
                if "404" in str(e) or "notFound" in str(e):
                    print(f"Message {msg_id} not found (likely deleted), skipping...")
                    continue
                else:
                    # Re-raise other errors
                    print(f"Unexpected error fetching message {msg_id}: {e}")
                    raise e
            
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            thread_id = msg.get("threadId")

            # Fetch thread summary once per thread
            thread_summary: Optional[Dict[str, Any]] = None
            if thread_id:
                if thread_id in fetched_threads:
                    thread_summary = fetched_threads[thread_id]
                else:
                    try:
                        thread_summary = self.get_thread_summary(thread_id)
                        fetched_threads[thread_id] = thread_summary
                    except Exception as e:
                        # Handle 404 errors for threads as well
                        if "404" in str(e) or "notFound" in str(e):
                            print(f"Thread {thread_id} not found (likely deleted), skipping...")
                            thread_summary = None
                        else:
                            # Re-raise other errors
                            print(f"Unexpected error fetching thread {thread_id}: {e}")
                            raise e

            messages.append(
                {
                    "id": msg.get("id"),
                    "threadId": thread_id,
                    "snippet": msg.get("snippet"),
                    "labelIds": msg.get("labelIds", []),
                    "headers": {
                        "From": headers.get("From"),
                        "To": headers.get("To"),
                        "Subject": headers.get("Subject"),
                        "Date": headers.get("Date"),
                        "Message-Id": headers.get("Message-Id"),
                    },
                    "thread": thread_summary,
                }
            )
        return messages

    def get_thread_summary(self, thread_id: str) -> Dict[str, Any]:
        """Fetch a thread and return a compact summary including latest message and simple history.

        Returns:
            {
              "threadId": str,
              "totalMessages": int,
              "latest": { id, internalDate, headers{From,To,Subject,Date,Message-Id}, snippet, bodyText },
              "messages": [ { id, internalDate, headers{...}, snippet } ]
            }
        """
        thread = (
            self.service.users()
            .threads()
            .get(userId="me", id=thread_id, format="full")
            .execute()
        )
        msgs = thread.get("messages", [])

        simplified_messages: List[Dict[str, Any]] = []
        latest_tuple: Tuple[int, Dict[str, Any]] = (0, {})

        for m in msgs:
            payload = m.get("payload", {})
            headers_list = payload.get("headers", [])
            headers = {h["name"]: h["value"] for h in headers_list}
            internal_date_str = m.get("internalDate") or "0"
            try:
                internal_ms = int(internal_date_str)
            except Exception:
                internal_ms = 0
            body_text = self._extract_plain_text(payload)
            simplified = {
                "id": m.get("id"),
                "internalDate": internal_date_str,
                "snippet": m.get("snippet"),
                "headers": {
                    "From": headers.get("From"),
                    "To": headers.get("To"),
                    "Subject": headers.get("Subject"),
                    "Date": headers.get("Date"),
                    "Message-Id": headers.get("Message-Id"),
                },
                "bodyText": body_text,
            }
            simplified_messages.append(simplified)
            if internal_ms >= latest_tuple[0]:
                latest_tuple = (internal_ms, simplified)

        latest_message = latest_tuple[1] if latest_tuple[1] else None
        return {
            "threadId": thread_id,
            "totalMessages": len(simplified_messages),
            "latest": latest_message,
            "messages": simplified_messages,
        }

    def _extract_plain_text(self, payload: Dict[str, Any]) -> Optional[str]:
        """Extract a plain text body from a Gmail message payload.

        Tries 'text/plain' part first; falls back to decoding the first body if needed.
        """
        import base64 as b64

        def walk(parts: List[Dict[str, Any]]) -> Optional[str]:
            for part in parts:
                mime_type = part.get("mimeType", "")
                body = part.get("body", {})
                data = body.get("data")
                if mime_type == "text/plain" and data:
                    try:
                        return b64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="ignore")
                    except Exception:
                        continue
                # Recurse into multipart
                subparts = part.get("parts", [])
                if subparts:
                    text = walk(subparts)
                    if text:
                        return text
            return None

        # Direct body
        if payload.get("body", {}).get("data"):
            try:
                return b64.urlsafe_b64decode(payload["body"]["data"].encode("utf-8")).decode("utf-8", errors="ignore")
            except Exception:
                pass

        parts = payload.get("parts", [])
        return walk(parts) if parts else None


