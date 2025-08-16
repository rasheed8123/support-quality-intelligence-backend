from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.agent_orchestration.gmail_ingestion import GmailIngestion
from app.services.agent_orchestration.sla_tracker import SLATracker
from typing import List, Dict

router = APIRouter()
gmail_service = GmailIngestion()

@router.get("/emails")
async def get_emails(
    query: str = None,
    db: Session = Depends(get_db)
):
    """Fetch emails from Gmail"""
    try:
        emails = await gmail_service.fetch_emails(query)
        return {"status": "success", "emails": emails}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sla/check")
async def check_sla(
    db: Session = Depends(get_db)
):
    """Check SLA breaches"""
    try:
        sla_tracker = SLATracker(db)
        breaches = await sla_tracker.check_sla_breaches()
        return {"status": "success", "breaches": breaches}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
