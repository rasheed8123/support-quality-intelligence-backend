from fastapi import APIRouter, Request

router = APIRouter(prefix="/classification", tags=["classification"])

@router.get("/")
async def classification():
    return {"message": "Hello, World!"}

@router.post("/")
async def classify(request: Request):
    return {"message": "Hello, World!"}
