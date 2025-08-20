# app/webhook/google_drive.py
import os
from fastapi import APIRouter, Request
from app.services.rag_pipeline.google_drive.drive_watch import create_drive_watch
router = APIRouter()

@router.post("/drive")
async def drive_webhook(request: Request):
    headers = dict(request.headers)
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}

    print("📩 Drive webhook received")
    print("Headers:", headers)
    print("Body:", body)

    # TODO: call service layer (drive_watch.py) to handle this event
    return {"status": "ok"}


@router.post("/drive/register")
async def register_drive_watch():
    # Get webhook URL from environment variable
    webhook_url = os.getenv("WEBHOOK_PUBLIC_URL")
    if not webhook_url:
        return {"error": "WEBHOOK_PUBLIC_URL not configured in environment"}

    response = create_drive_watch(webhook_url)
    return response
