from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.rag_pipeline.langgraph_flow import RAGFlow
from typing import List, Dict

router = APIRouter()
rag_flow = RAGFlow()

@router.post("/rag/process")
async def process_documents(
    folder_id: str,
    db: Session = Depends(get_db)
):
    """Process documents through the RAG pipeline"""
    try:
        result = await rag_flow.execute(folder_id)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rag/query")
async def query_documents(
    question: str,
    db: Session = Depends(get_db)
):
    """Query the RAG system"""
    try:
        # Implement query logic
        return {"status": "success", "answer": "Not implemented"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
