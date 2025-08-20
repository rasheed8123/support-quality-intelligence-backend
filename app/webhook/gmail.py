import os
import json
import logging
from fastapi import APIRouter, Request, HTTPException
from app.services.gmail.gmail_watch import (
    register_gmail_watch,
    stop_gmail_watch,
    process_gmail_notification,
    get_message_details
)

log = logging.getLogger(__name__)
router = APIRouter()

@router.post("/gmail")
async def gmail_webhook(request: Request):
    """
    Gmail webhook endpoint that receives Pub/Sub push notifications.
    This is called by Google Cloud Pub/Sub when Gmail events occur.
    """
    try:
        # Get request headers and body
        headers = dict(request.headers)

        # Pub/Sub sends JSON data
        body = await request.json()

        log.info("📬 Gmail webhook received")
        log.info(f"Headers: {headers}")
        log.info(f"Body: {body}")

        # Process the Gmail notification
        process_gmail_notification(body)

        # Pub/Sub expects a 200 response
        return {"status": "ok", "message": "Gmail notification processed"}

    except Exception as e:
        log.error(f"Error processing Gmail webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/gmail/register")
async def register_gmail_webhook():
    """
    Register Gmail push notifications.
    Note: This requires Google Cloud Pub/Sub setup.
    """
    try:
        result = register_gmail_watch()

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "status": "success",
            "message": "Gmail watch registered successfully",
            "details": result
        }

    except Exception as e:
        log.error(f"Failed to register Gmail watch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/gmail/stop")
async def stop_gmail_webhook():
    """Stop Gmail push notifications"""
    try:
        result = stop_gmail_watch()

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return {
            "status": "success",
            "message": "Gmail watch stopped successfully"
        }

    except Exception as e:
        log.error(f"Failed to stop Gmail watch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gmail/message/{message_id}")
async def get_gmail_message(message_id: str):
    """Get details of a specific Gmail message"""
    try:
        message_details = get_message_details(message_id)

        if not message_details:
            raise HTTPException(status_code=404, detail="Message not found")

        return message_details

    except Exception as e:
        log.error(f"Failed to get message {message_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/gmail/test")
async def test_gmail_connection():
    """Test Gmail API connection"""
    try:
        from app.services.gmail.gmail_watch import build_gmail_client

        gmail = build_gmail_client()
        if not gmail:
            raise HTTPException(status_code=500, detail="Failed to build Gmail client")

        # Test by getting user profile
        profile = gmail.users().getProfile(userId='me').execute()

        return {
            "status": "success",
            "message": "Gmail connection successful",
            "email": profile.get('emailAddress'),
            "total_messages": profile.get('messagesTotal'),
            "total_threads": profile.get('threadsTotal')
        }

    except Exception as e:
        log.error(f"Gmail connection test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))