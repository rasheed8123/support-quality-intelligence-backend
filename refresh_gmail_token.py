#!/usr/bin/env python3
"""
Quick script to refresh the expired Gmail token
"""

import json
import requests
from datetime import datetime, timedelta

def refresh_gmail_token():
    """Refresh the expired Gmail token using the refresh token"""
    
    # Read current token file
    token_path = "app/env/token.json"
    
    try:
        with open(token_path, 'r') as f:
            token_data = json.load(f)
        
        print(f"📧 Current token expiry: {token_data.get('expiry', 'Unknown')}")
        
        # Check if token is expired
        expiry_str = token_data.get('expiry')
        if expiry_str:
            expiry_time = datetime.fromisoformat(expiry_str.replace('Z', '+00:00'))
            current_time = datetime.now(expiry_time.tzinfo)
            
            if current_time < expiry_time:
                print("✅ Token is still valid!")
                return True
            else:
                print("❌ Token is expired, refreshing...")
        
        # Refresh the token
        refresh_token = token_data.get('refresh_token')
        client_id = token_data.get('client_id')
        client_secret = token_data.get('client_secret')
        
        if not all([refresh_token, client_id, client_secret]):
            print("❌ Missing required token data for refresh")
            return False
        
        # Make refresh request
        refresh_url = "https://oauth2.googleapis.com/token"
        refresh_data = {
            'client_id': client_id,
            'client_secret': client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }
        
        print("🔄 Refreshing token...")
        response = requests.post(refresh_url, data=refresh_data)
        
        if response.status_code == 200:
            new_token_data = response.json()
            
            # Update token data
            token_data['token'] = new_token_data['access_token']
            
            # Calculate new expiry (usually 1 hour from now)
            expires_in = new_token_data.get('expires_in', 3600)  # Default 1 hour
            new_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
            token_data['expiry'] = new_expiry.isoformat() + 'Z'
            
            # Update refresh token if provided
            if 'refresh_token' in new_token_data:
                token_data['refresh_token'] = new_token_data['refresh_token']
            
            # Save updated token
            with open(token_path, 'w') as f:
                json.dump(token_data, f, indent=2)
            
            print(f"✅ Token refreshed successfully!")
            print(f"   New expiry: {token_data['expiry']}")
            print(f"   New token: {new_token_data['access_token'][:50]}...")
            
            return True
            
        else:
            print(f"❌ Failed to refresh token: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error refreshing token: {str(e)}")
        return False

def setup_gmail_watch():
    """Set up Gmail watch after token refresh"""
    try:
        from app.services.email.gmail_client import GmailClient

        print("🔄 Setting up Gmail watch...")

        # Initialize Gmail client with proper credentials
        client = GmailClient(
            credentials_path="app/env/confidential.json",
            delegated_subject="alhassan069@gmail.com",
            oauth_token_file="app/env/token.json"
        )

        # Set up watch
        result = client.setup_watch()
        
        if result:
            print("✅ Gmail watch setup successful!")
            print(f"   Watch details: {result}")
            return True
        else:
            print("❌ Gmail watch setup failed")
            return False
            
    except Exception as e:
        print(f"❌ Error setting up Gmail watch: {str(e)}")
        return False

if __name__ == "__main__":
    print("🔧 GMAIL TOKEN REFRESH & WATCH SETUP")
    print("=" * 50)
    
    # Step 1: Refresh token
    if refresh_gmail_token():
        print("\n🎯 Token refresh completed!")
        
        # Step 2: Setup Gmail watch
        if setup_gmail_watch():
            print("\n🎉 Gmail Pub/Sub setup completed successfully!")
            print("   Your server should now receive Gmail notifications")
        else:
            print("\n⚠️ Gmail watch setup failed, but token is refreshed")
            print("   You may need to manually set up the watch")
    else:
        print("\n❌ Token refresh failed!")
        print("   You may need to re-authenticate completely")
