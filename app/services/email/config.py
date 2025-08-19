import os
import sys
from pydantic import BaseModel
from typing import List, Optional
from dotenv import load_dotenv

# Load variables from .env if present
load_dotenv()


class Settings(BaseModel):
    google_credentials_path: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "app/env/confidential.json")
    gmail_impersonate_email: Optional[str] = os.getenv("GMAIL_IMPERSONATE_EMAIL")
    state_file_path: str = os.getenv("STATE_FILE_PATH", "app/env/state.json")
    oauth_token_file: str = os.getenv("OAUTH_TOKEN_FILE", "app/env/token.json")

    # Optional: verify Google-signed JWT from Pub/Sub push (recommended if you configure OIDC push auth)
    pubsub_verify_audience: bool = os.getenv("PUBSUB_VERIFY_AUDIENCE", "false").lower() in {"1", "true", "yes"}
    pubsub_audience: Optional[str] = os.getenv("PUBSUB_AUDIENCE")

    # Gmail Watch setup
    gmail_topic_name: Optional[str] = os.getenv("GMAIL_TOPIC_NAME", "projects/misogi-461317/topics/emai-analysis")
    gmail_label_ids: List[str] = [s.strip() for s in os.getenv("GMAIL_LABEL_IDS", "INBOX,SENT").split(",") if s.strip()]
    gmail_label_filter_action: Optional[str] = os.getenv("GMAIL_LABEL_FILTER_ACTION")  # include or exclude


def load_settings() -> Settings:
    return Settings()


