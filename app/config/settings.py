from pydantic_settings import BaseSettings
from typing import Optional, List
from pathlib import Path
import os
import json

class Settings(BaseSettings):
    """Production-grade settings for Support Quality Intelligence RAG Pipeline"""

    # Database settings
    DATABASE_URL: str = "sqlite:///./sql_app.db"

    # API Configuration
    API_VERSION: str = "v1"
    API_TITLE: str = "Support Quality Intelligence API"
    API_DESCRIPTION: str = "Advanced RAG pipeline for support response verification"

    # API Keys
    OPENAI_API_KEY: Optional[str] = None
    GOOGLE_CLOUD_PROJECT: Optional[str] = None

    # Google Service Account - Google Drive Credentials (configured in .env)
    GOOGLE_SERVICE_ACCOUNT_TYPE: str = "service_account"
    GOOGLE_SERVICE_ACCOUNT_PROJECT_ID: Optional[str] = None
    GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY_ID: Optional[str] = None
    GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY: Optional[str] = None
    GOOGLE_SERVICE_ACCOUNT_CLIENT_EMAIL: Optional[str] = None
    GOOGLE_SERVICE_ACCOUNT_CLIENT_ID: Optional[str] = None
    GOOGLE_SERVICE_ACCOUNT_AUTH_URI: str = "https://accounts.google.com/o/oauth2/auth"
    GOOGLE_SERVICE_ACCOUNT_TOKEN_URI: str = "https://oauth2.googleapis.com/token"
    GOOGLE_SERVICE_ACCOUNT_AUTH_PROVIDER_X509_CERT_URL: str = "https://www.googleapis.com/oauth2/v1/certs"
    GOOGLE_SERVICE_ACCOUNT_CLIENT_X509_CERT_URL: Optional[str] = None
    GOOGLE_SERVICE_ACCOUNT_UNIVERSE_DOMAIN: str = "googleapis.com"
    GOOGLE_SCOPES: str = "https://www.googleapis.com/auth/drive.readonly"
    DRIVE_FOLDER_ID: Optional[str] = None
    WEBHOOK_PUBLIC_URL: Optional[str] = None

    # Gmail API settings
    GMAIL_CREDENTIALS_FILE: Optional[str] = None
    GMAIL_PUBSUB_TOPIC: str = "gmail-notifications"
    GMAIL_PUBSUB_SUBSCRIPTION: str = "gmail-webhook-subscription"

    # OpenAI Models Configuration
    CLAIM_EXTRACTION_MODEL: str = "gpt-4o"
    FACT_VERIFICATION_MODEL: str = "gpt-4o"
    COMPLIANCE_CHECK_MODEL: str = "gpt-4o"
    FEEDBACK_GENERATION_MODEL: str = "gpt-4o"
    QUERY_EXPANSION_MODEL: str = "gpt-4o-mini"
    RERANKING_MODEL: str = "gpt-4o-mini"
    EMBEDDING_MODEL: str = "text-embedding-3-large"

    # Vector Store Configuration
    VECTOR_STORE_TYPE: str = "qdrant"
    VECTOR_STORE_HOST: str = "localhost"
    VECTOR_STORE_PORT: int = 6333
    VECTOR_STORE_API_KEY: Optional[str] = None
    EMBEDDING_DIMENSIONS: int = 3072
    MAX_CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 100

    # Verification Thresholds
    DEFAULT_ACCURACY_THRESHOLD: float = 0.8
    STRICT_ACCURACY_THRESHOLD: float = 0.9
    COMPREHENSIVE_ACCURACY_THRESHOLD: float = 0.95

    # Performance Settings
    MAX_CONCURRENT_REQUESTS: int = 100
    REQUEST_TIMEOUT_SECONDS: int = 30
    MAX_CLAIMS_PER_REQUEST: int = 20
    MAX_EVIDENCE_ITEMS_PER_CLAIM: int = 10
    RETRIEVAL_TIMEOUT_SECONDS: int = 10

    # Caching Configuration
    ENABLE_RESPONSE_CACHING: bool = True
    CACHE_TTL_SECONDS: int = 3600

    # Monitoring and Logging
    LOG_LEVEL: str = "INFO"
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 8001

    class Config:
        env_file = ".env"
        extra = "allow"  # Allow extra fields from .env

    def get_service_account_info(self) -> dict:
        """Build Google service account info from environment variables"""
        if not self.GOOGLE_SERVICE_ACCOUNT_PROJECT_ID:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_PROJECT_ID is required in .env file")

        if not self.GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY is required in .env file")

        if not self.GOOGLE_SERVICE_ACCOUNT_CLIENT_EMAIL:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT_CLIENT_EMAIL is required in .env file")

        return {
            "type": self.GOOGLE_SERVICE_ACCOUNT_TYPE,
            "project_id": self.GOOGLE_SERVICE_ACCOUNT_PROJECT_ID,
            "private_key_id": self.GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY_ID,
            "private_key": self.GOOGLE_SERVICE_ACCOUNT_PRIVATE_KEY.replace('\\n', '\n'),  # Fix newlines
            "client_email": self.GOOGLE_SERVICE_ACCOUNT_CLIENT_EMAIL,
            "client_id": self.GOOGLE_SERVICE_ACCOUNT_CLIENT_ID,
            "auth_uri": self.GOOGLE_SERVICE_ACCOUNT_AUTH_URI,
            "token_uri": self.GOOGLE_SERVICE_ACCOUNT_TOKEN_URI,
            "auth_provider_x509_cert_url": self.GOOGLE_SERVICE_ACCOUNT_AUTH_PROVIDER_X509_CERT_URL,
            "client_x509_cert_url": self.GOOGLE_SERVICE_ACCOUNT_CLIENT_X509_CERT_URL,
            "universe_domain": self.GOOGLE_SERVICE_ACCOUNT_UNIVERSE_DOMAIN
        }

    def get_gmail_credentials_path(self) -> str:
        """Get Gmail credentials file path with secure fallback locations"""
        if self.GMAIL_CREDENTIALS_FILE and Path(self.GMAIL_CREDENTIALS_FILE).exists():
            return self.GMAIL_CREDENTIALS_FILE

        # Fallback locations in priority order
        locations = [
            "credentials/gmail_credentials.json",
            "secrets/gmail_credentials.json",
            "gmail_credentials.json"
        ]

        for location in locations:
            if Path(location).exists():
                return location

        raise FileNotFoundError(
            "Gmail credentials not found. Expected at: credentials/gmail_credentials.json\n"
            "Run 'python setup_gmail_auth.py' to create it."
        )
