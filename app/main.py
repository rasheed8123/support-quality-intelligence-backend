from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Support Quality Intelligence API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include routers here
# from app.api import rag_routes, agent_routes, classification_routes, alert_routes, report_routes

@app.get("/")
async def root():
    return {"message": "Support Quality Intelligence API"}
