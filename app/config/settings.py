from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str = "sqlite:///./sql_app.db"
    
    # API Keys
    OPENAI_API_KEY: str
    GOOGLE_CLOUD_PROJECT: Optional[str] = None
    
    # Gmail API settings
    GMAIL_CREDENTIALS_FILE: Optional[str] = None
    
    # LangGraph settings
    VECTOR_STORE_PATH: str = "./vector_store"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    class Config:
        env_file = ".env"
