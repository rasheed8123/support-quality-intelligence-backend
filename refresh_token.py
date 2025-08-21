#!/usr/bin/env python3
"""
Token Refresh Script
Refreshes the existing Gmail token if it's expired.
"""

import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from datetime import datetime

def refresh_gmail_token():
    """Refresh the existing Gmail token"""
    
    token_file = 'app/env/token.json'
    
    if not os.path.exists(token_file):
        print(f"❌ Token file not found: {token_file}")
        return False
    
    print(f"🔍 Found existing token file: {token_file}")
    
    # Load existing credentials
    with open(token_file, 'r') as f:
        token_data = json.load(f)
    
    print(f"📅 Token expiry: {token_data.get('expiry', 'Unknown')}")
    
    # Create credentials object
    creds = Credentials(
        token=token_data.get('token'),
        refresh_token=token_data.get('refresh_token'),
        token_uri=token_data.get('token_uri'),
        client_id=token_data.get('client_id'),
        client_secret=token_data.get('client_secret'),
        scopes=token_data.get('scopes')
    )
    
    # Check if credentials are valid or can be refreshed
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Token expired, attempting to refresh...")
            try:
                creds.refresh(Request())
                print("✅ Token refreshed successfully!")
                
                # Save the refreshed token
                token_data.update({
                    'token': creds.token,
                    'expiry': creds.expiry.isoformat() if creds.expiry else None
                })
                
                with open(token_file, 'w') as f:
                    json.dump(token_data, f, indent=2)
                
                print(f"💾 Updated token saved to: {token_file}")
                print(f"🆕 New expiry: {creds.expiry}")
                return True
                
            except Exception as e:
                print(f"❌ Failed to refresh token: {e}")
                print("🔄 You may need to re-authenticate")
                return False
        else:
            print("❌ Token cannot be refreshed - re-authentication required")
            return False
    else:
        print("✅ Token is still valid!")
        return True

if __name__ == '__main__':
    print("🔑 Gmail Token Refresh")
    print("=" * 50)
    
    if refresh_gmail_token():
        print("\n🎉 Token is ready for use!")
    else:
        print("\n❌ Token refresh failed - you may need to re-authenticate")
