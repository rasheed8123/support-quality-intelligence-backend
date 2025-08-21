#!/usr/bin/env python3
"""
Test Gmail Access
Tests if the existing token can access Gmail API.
"""

import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from datetime import datetime

def test_gmail_access():
    """Test Gmail API access with existing token"""
    
    token_file = 'app/env/token.json'
    
    if not os.path.exists(token_file):
        print(f"❌ Token file not found: {token_file}")
        return False
    
    print(f"🔍 Loading token from: {token_file}")
    
    # Load existing credentials
    with open(token_file, 'r') as f:
        token_data = json.load(f)
    
    print(f"📅 Token expiry: {token_data.get('expiry', 'Unknown')}")
    print(f"🕐 Current time: {datetime.now().isoformat()}")
    
    # Create credentials object
    creds = Credentials(
        token=token_data.get('token'),
        refresh_token=token_data.get('refresh_token'),
        token_uri=token_data.get('token_uri'),
        client_id=token_data.get('client_id'),
        client_secret=token_data.get('client_secret'),
        scopes=token_data.get('scopes')
    )
    
    try:
        # Test Gmail API access
        print("🔄 Testing Gmail API access...")
        service = build('gmail', 'v1', credentials=creds)
        
        # Get user profile (simple test)
        profile = service.users().getProfile(userId='me').execute()
        print(f"✅ Gmail API access successful!")
        print(f"📧 Email: {profile.get('emailAddress')}")
        print(f"📊 Total messages: {profile.get('messagesTotal', 0)}")
        
        # If we got here, the token works
        return True
        
    except Exception as e:
        print(f"❌ Gmail API access failed: {e}")
        
        # Try to refresh the token
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Attempting to refresh token...")
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
                
                print(f"💾 Updated token saved")
                print(f"🆕 New expiry: {creds.expiry}")
                
                # Test again with refreshed token
                service = build('gmail', 'v1', credentials=creds)
                profile = service.users().getProfile(userId='me').execute()
                print(f"✅ Gmail API access successful with refreshed token!")
                print(f"📧 Email: {profile.get('emailAddress')}")
                
                return True
                
            except Exception as refresh_error:
                print(f"❌ Token refresh failed: {refresh_error}")
                return False
        else:
            print("❌ Cannot refresh token - re-authentication required")
            return False

if __name__ == '__main__':
    print("🧪 Gmail API Access Test")
    print("=" * 50)
    
    if test_gmail_access():
        print("\n🎉 Gmail access is working!")
    else:
        print("\n❌ Gmail access failed - re-authentication may be needed")
