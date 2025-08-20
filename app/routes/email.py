

import base64
import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.email.config import load_settings
from app.services.email.gmail_client import GmailClient
from app.services.email.state_store import StateStore
from app.services.agent_orchestration.classify import classify_email

router = APIRouter(prefix="/email", tags=["email"])

logger = logging.getLogger("gmail-push")


class PubSubPushMessage(BaseModel):
    message: Dict[str, Any]
    subscription: Optional[str] = None


settings = load_settings()
state_store = StateStore(settings.state_file_path)
_gmail_client: Optional[GmailClient] = None


def _get_gmail_client() -> GmailClient:
    global _gmail_client
    if _gmail_client is None:
        try:
            _gmail_client = GmailClient(
                credentials_path=settings.google_credentials_path,
                delegated_subject=settings.gmail_impersonate_email,
                oauth_token_file=settings.oauth_token_file,
            )
        except FileNotFoundError as e:
            # More explicit message for missing credentials
            raise HTTPException(
                status_code=500,
                detail="Credentials file not found. Ensure GOOGLE_APPLICATION_CREDENTIALS points to your service account key JSON (e.g., confidential.json).",
            )
        except Exception as exc:  # noqa: BLE001
            # Surface configuration errors clearly (e.g., malformed JSON or wrong file type)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize Gmail client: {exc}",
            )
    return _gmail_client



def _decode_pubsub_message(envelope: PubSubPushMessage) -> Dict[str, Any]:
    data_b64 = envelope.message.get("data")
    if not data_b64:
        raise HTTPException(status_code=400, detail="Missing data in Pub/Sub message")
    try:
        payload_json = base64.b64decode(data_b64).decode("utf-8")
        return json.loads(payload_json)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"Failed to decode Pub/Sub data: {exc}")


@router.get("/auth/init")
async def auth_init():
    """Trigger OAuth flow (for OAuth client credentials). Creates/refreshes token.json.

    - If using a Service Account, this will just initialize successfully.
    - If using OAuth client JSON and no token exists, a browser should open; if not, check server logs for a URL.
    """
    client = _get_gmail_client()
    # Optional quick call to ensure token works
    try:
        labels = client.service.users().labels().list(userId="me").execute()
        label_names = [l.get("name") for l in labels.get("labels", [])]
    except Exception:
        label_names = []
    return {"status": "ok", "labels_found": len(label_names)}


@router.post("/pubsub/push")
async def pubsub_push(envelope: PubSubPushMessage, request: Request):
    payload = _decode_pubsub_message(envelope)
    
    logger.info(f"PubSub push received for email: {payload.get('emailAddress')}, historyId: {payload.get('historyId')}")
    
    # Gmail push payload has emailAddress and historyId
    email_address = payload.get("emailAddress")
    history_id = payload.get("historyId")
    if not email_address or not history_id:
        raise HTTPException(status_code=400, detail="Invalid Gmail payload: missing emailAddress or historyId")

    # Optional: verify Google-signed JWT audience for Pub/Sub Push
    if settings.pubsub_verify_audience and settings.pubsub_audience:
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests as grequests

            auth_header = request.headers.get("Authorization", "")
            token = auth_header.replace("Bearer ", "").strip()
            if not token:
                raise HTTPException(status_code=401, detail="Missing Authorization header for Pub/Sub verification")
            id_token.verify_oauth2_token(token, grequests.Request(), audience=settings.pubsub_audience)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=401, detail=f"Pub/Sub JWT verification failed: {exc}")

    # High-watermark
    last_id = state_store.get_last_history_id(email_address)

    try:
        client = _get_gmail_client()
        new_messages = client.fetch_new_messages_since(start_history_id=last_id)
    except Exception as exc:  # noqa: BLE001
        # Return 200 so Pub/Sub does not endlessly retry. The error will be logged by server.
        return {"status": "error", "detail": str(exc)}

    # Persist new high-watermark
    state_store.set_last_history_id(email_address, str(history_id))

    logger.info(f"Processing {len(new_messages)} new messages")
    
    # Process each message and call classify_email
    processed_count = 0
    for message in new_messages:
        try:
            # Extract required fields
            email_id = message.get("id")
            thread_id = message.get("threadId")
            headers = message.get("headers", {})
            from_email = headers.get("From", "")
            subject = headers.get("Subject", "")
            
            # Get body from thread's latest message
            thread = message.get("thread", {})
            latest_message = thread.get("latest", {})
            body = latest_message.get("bodyText", "") or latest_message.get("snippet", "")
            
            # Determine if it's sent or received based on labels
            label_ids = message.get("labelIds", [])
            # If SENT label is present, it's an outbound email, otherwise it's inbound
            is_inbound = "SENT" not in label_ids
            
            # Call classify_email function
            classify_email(
                email_id=email_id,
                from_email=from_email,
                thread_id=thread_id,
                subject=subject,
                body=body,
                is_inbound=is_inbound
            )
            
            processed_count += 1
            logger.info(f"Successfully processed email {email_id} (inbound: {is_inbound}, subject: {subject[:50]}...)")
            
        except Exception as e:
            logger.error(f"Error processing email {message.get('id', 'unknown')}: {str(e)}")
            continue

    logger.info(f"Processed {processed_count} out of {len(new_messages)} messages")
    
    return {
        "received_for": email_address,
        "historyId": history_id,
        "count": len(new_messages),
        "processed": processed_count,
    }


# OLD PUBSUB LOGIC INCASE IF ANYTHING GOES WRONG

'''
@router.post("/pubsub/push")
async def pubsub_push(envelope: PubSubPushMessage, request: Request):
    payload = _decode_pubsub_message(envelope)
    # Print what we received from Pub/Sub/Gmail
    try:
        logger.info("PubSub push received: %s", json.dumps(payload))
    except Exception:
        logger.info("PubSub push received (non-serializable payload)")
    # Also print to stdout for immediate visibility in your terminal
    try:
        print("PubSub push payload:", json.dumps(payload))
    except Exception:
        print("PubSub push payload (raw):", payload)

    # Gmail push payload has emailAddress and historyId
    email_address = payload.get("emailAddress")
    history_id = payload.get("historyId")
    if not email_address or not history_id:
        raise HTTPException(status_code=400, detail="Invalid Gmail payload: missing emailAddress or historyId")

    # Optional: verify Google-signed JWT audience for Pub/Sub Push
    if settings.pubsub_verify_audience and settings.pubsub_audience:
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests as grequests

            auth_header = request.headers.get("Authorization", "")
            token = auth_header.replace("Bearer ", "").strip()
            if not token:
                raise HTTPException(status_code=401, detail="Missing Authorization header for Pub/Sub verification")
            id_token.verify_oauth2_token(token, grequests.Request(), audience=settings.pubsub_audience)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=401, detail=f"Pub/Sub JWT verification failed: {exc}")

    # High-watermark
    last_id = state_store.get_last_history_id(email_address)

    try:
        client = _get_gmail_client()
        new_messages = client.fetch_new_messages_since(start_history_id=last_id)
    except Exception as exc:  # noqa: BLE001
        # Return 200 so Pub/Sub does not endlessly retry. The error will be logged by server.
        return {"status": "error", "detail": str(exc)}

    # Persist new high-watermark
    state_store.set_last_history_id(email_address, str(history_id))

    # Print a concise summary of fetched messages
    try:
        subjects = [m.get("headers", {}).get("Subject") for m in new_messages]
        logger.info(
            "Fetched %d messages. Subjects: %s",
            len(new_messages),
            subjects,
        )
        print(f"Fetched {len(new_messages)} messages. Subjects: {subjects}")

        # Detailed per-message console output including thread and latest message info
        for m in new_messages:
            thread_id = m.get("threadId")
            thread = m.get("thread") or {}
            latest = thread.get("latest") or {}
            latest_headers = (latest.get("headers") or {})
            latest_subject = latest_headers.get("Subject")
            latest_from = latest_headers.get("From")
            latest_date = latest_headers.get("Date")
            preview = (latest.get("bodyText") or latest.get("snippet") or "").strip()
            if preview and len(preview) > 160:
                preview = preview[:160] + "…"
            print(
                "Message:",
                {
                    "id": m.get("id"),
                    "threadId": thread_id,
                    "subject": m.get("headers", {}).get("Subject"),
                    "snippet": m.get("snippet"),
                    "threadTotal": thread.get("totalMessages"),
                    "latest": {
                        "subject": latest_subject,
                        "from": latest_from,
                        "date": latest_date,
                        "preview": preview,
                    },
                },
            )
            # Print concise chat history (up to last 10 entries)
            history_msgs = (thread.get("messages") or [])[-10:]
            if history_msgs:
                print("Thread history (latest 10):")
                for hm in history_msgs:
                    hmh = (hm.get("headers") or {})
                    hsub = hmh.get("Subject")
                    hfrom = hmh.get("From")
                    hdate = hmh.get("Date")
                    hprev = (hm.get("bodyText") or hm.get("snippet") or "").strip()
                    if hprev and len(hprev) > 120:
                        hprev = hprev[:120] + "…"
                    print(f"- [{hdate}] {hfrom} | {hsub} :: {hprev}")
    except Exception:
        logger.info("Fetched %d messages.", len(new_messages))
        print(f"Fetched {len(new_messages)} messages.")

    # Return summaries for visibility
    return {
        "received_for": email_address,
        "historyId": history_id,
        "count": len(new_messages),
        "messages": new_messages,
    }


'''