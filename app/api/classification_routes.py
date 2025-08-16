from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.classification_models.priority_detector import PriorityDetector
from app.services.classification_models.tone_classifier import ToneClassifier
from typing import List, Dict

router = APIRouter()
priority_detector = PriorityDetector()
tone_classifier = ToneClassifier()

@router.post("/classify/priority")
async def classify_priority(
    text: str,
    db: Session = Depends(get_db)
):
    """Classify email priority"""
    try:
        priority = await priority_detector.predict_priority(text)
        return {"status": "success", "priority": priority}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/classify/tone")
async def classify_tone(
    text: str,
    db: Session = Depends(get_db)
):
    """Classify email tone"""
    try:
        tone = await tone_classifier.classify_tone(text)
        return {"status": "success", "tone": tone}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
