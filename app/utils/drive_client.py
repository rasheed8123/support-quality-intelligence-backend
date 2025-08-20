from googleapiclient.discovery import build, Resource
from google.oauth2 import service_account
from app.config import settings

def build_drive_client() -> Resource:
    """Build authenticated Google Drive API client using environment variables"""
    try:
        sa_info = settings.get_service_account_info()
        scopes = settings.GOOGLE_SCOPES.split(",")
        creds = service_account.Credentials.from_service_account_info(sa_info, scopes=scopes)
        return build("drive", "v3", credentials=creds, cache_discovery=False)
    except (ValueError, Exception) as e:
        raise Exception(f"Failed to build Drive client: {e}")
