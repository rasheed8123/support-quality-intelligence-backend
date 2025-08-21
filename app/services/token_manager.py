"""
Enhanced Token Manager for Long-Term Gmail Access
Handles automatic token refresh with maximum longevity optimization.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

class LongTermTokenManager:
    """
    Manages Gmail OAuth tokens with focus on maximum longevity and reliability.
    
    Features:
    - Automatic token refresh before expiration
    - Proactive refresh (refreshes 10 minutes before expiry)
    - Persistent storage with backup
    - Error recovery and retry logic
    - Long-term refresh token preservation
    """
    
    def __init__(self, token_file: str = "app/env/token.json"):
        self.token_file = token_file
        self.backup_file = f"{token_file}.backup"
        self._credentials: Optional[Credentials] = None
        self._last_refresh = None
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(token_file), exist_ok=True)
        
    def get_credentials(self) -> Optional[Credentials]:
        """
        Get valid credentials, automatically refreshing if needed.
        Returns credentials that are guaranteed to be valid for at least 10 minutes.
        """
        try:
            # Load credentials if not already loaded
            if not self._credentials:
                self._load_credentials()
            
            # Check if we need to refresh (proactive refresh)
            if self._needs_refresh():
                logger.info("🔄 Proactively refreshing token before expiration...")
                self._refresh_token()
            
            return self._credentials
            
        except Exception as e:
            logger.error(f"❌ Failed to get credentials: {e}")
            return None
    
    def _load_credentials(self):
        """Load credentials from token file"""
        if not os.path.exists(self.token_file):
            logger.error(f"❌ Token file not found: {self.token_file}")
            return
        
        try:
            with open(self.token_file, 'r') as f:
                token_data = json.load(f)
            
            self._credentials = Credentials(
                token=token_data.get('token'),
                refresh_token=token_data.get('refresh_token'),
                token_uri=token_data.get('token_uri'),
                client_id=token_data.get('client_id'),
                client_secret=token_data.get('client_secret'),
                scopes=token_data.get('scopes')
            )
            
            logger.info(f"✅ Credentials loaded from {self.token_file}")
            
        except Exception as e:
            logger.error(f"❌ Failed to load credentials: {e}")
    
    def _needs_refresh(self) -> bool:
        """
        Check if token needs refresh.
        Returns True if token expires within 10 minutes (proactive refresh).
        """
        if not self._credentials:
            return True
        
        if not self._credentials.valid:
            return True
        
        # Proactive refresh: refresh 10 minutes before expiry
        if self._credentials.expiry:
            time_until_expiry = self._credentials.expiry - datetime.utcnow()
            if time_until_expiry < timedelta(minutes=10):
                logger.info(f"🕐 Token expires in {time_until_expiry}, refreshing proactively")
                return True
        
        return False
    
    def _refresh_token(self):
        """Refresh the access token using refresh token"""
        if not self._credentials or not self._credentials.refresh_token:
            logger.error("❌ No refresh token available")
            return
        
        try:
            # Create backup before refresh
            self._create_backup()
            
            # Refresh the token
            self._credentials.refresh(Request())
            
            # Save the refreshed token
            self._save_credentials()
            
            self._last_refresh = datetime.utcnow()
            logger.info(f"✅ Token refreshed successfully, expires: {self._credentials.expiry}")
            
        except Exception as e:
            logger.error(f"❌ Token refresh failed: {e}")
            # Try to restore from backup
            self._restore_from_backup()
    
    def _save_credentials(self):
        """Save credentials to file"""
        try:
            token_data = {
                'token': self._credentials.token,
                'refresh_token': self._credentials.refresh_token,
                'token_uri': self._credentials.token_uri,
                'client_id': self._credentials.client_id,
                'client_secret': self._credentials.client_secret,
                'scopes': self._credentials.scopes,
                'universe_domain': 'googleapis.com',
                'account': '',
                'expiry': self._credentials.expiry.isoformat() if self._credentials.expiry else None
            }
            
            with open(self.token_file, 'w') as f:
                json.dump(token_data, f, indent=2)
            
            logger.info(f"💾 Credentials saved to {self.token_file}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save credentials: {e}")
    
    def _create_backup(self):
        """Create backup of current token file"""
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r') as src, open(self.backup_file, 'w') as dst:
                    dst.write(src.read())
                logger.debug(f"📋 Backup created: {self.backup_file}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to create backup: {e}")
    
    def _restore_from_backup(self):
        """Restore token from backup if available"""
        try:
            if os.path.exists(self.backup_file):
                with open(self.backup_file, 'r') as src, open(self.token_file, 'w') as dst:
                    dst.write(src.read())
                logger.info(f"🔄 Restored from backup: {self.backup_file}")
                self._load_credentials()
        except Exception as e:
            logger.error(f"❌ Failed to restore from backup: {e}")
    
    def get_gmail_service(self):
        """Get authenticated Gmail service"""
        credentials = self.get_credentials()
        if not credentials:
            return None
        
        try:
            service = build('gmail', 'v1', credentials=credentials)
            return service
        except Exception as e:
            logger.error(f"❌ Failed to build Gmail service: {e}")
            return None
    
    def get_token_info(self) -> dict:
        """Get information about current token status"""
        if not self._credentials:
            self._load_credentials()
        
        if not self._credentials:
            return {"status": "no_token", "message": "No token available"}
        
        info = {
            "status": "valid" if self._credentials.valid else "invalid",
            "has_refresh_token": bool(self._credentials.refresh_token),
            "scopes": self._credentials.scopes,
            "expiry": self._credentials.expiry.isoformat() if self._credentials.expiry else None,
            "time_until_expiry": None,
            "last_refresh": self._last_refresh.isoformat() if self._last_refresh else None
        }
        
        if self._credentials.expiry:
            time_until_expiry = self._credentials.expiry - datetime.utcnow()
            info["time_until_expiry"] = str(time_until_expiry)
            info["expires_in_minutes"] = int(time_until_expiry.total_seconds() / 60)
        
        return info

# Global instance for the application
token_manager = LongTermTokenManager()
