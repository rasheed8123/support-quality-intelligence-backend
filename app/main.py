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
from routes import classification
from routes import email
app.include_router(classification.router)
app.include_router(email.router)

@app.get("/")
async def root():
    return {"message": "Support Quality Intelligence API"}
