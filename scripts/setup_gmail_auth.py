#!/usr/bin/env python3
"""
Gmail OAuth Setup Script
Run this script to authenticate with Gmail and generate the credentials file.
"""

import os
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Gmail API scopes - read-only access
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def setup_gmail_credentials():
    """Set up Gmail OAuth credentials"""

    # Check if client secrets file exists (look in multiple locations)
    client_secrets_locations = [
        'credentials/client_secret.json',  # Recommended location
        'secrets/client_secret.json',      # Alternative location
        'client_secret.json'               # Legacy location
    ]

    client_secrets_file = None
    for location in client_secrets_locations:
        if os.path.exists(location):
            client_secrets_file = location
            break

    credentials_file = 'credentials/gmail_credentials.json'  # Will be created in secure location

    # Ensure credentials directory exists
    os.makedirs('credentials', exist_ok=True)
    
    if not client_secrets_file:
        print("❌ Error: client_secret.json not found!")
        print("📋 Please:")
        print("1. Go to Google Cloud Console")
        print("2. APIs & Services → Credentials")
        print("3. Create OAuth 2.0 Client ID (Desktop application)")
        print("4. Download the JSON file")
        print("5. Rename it to 'client_secret.json'")
        print("6. Place it in 'credentials/' directory (recommended)")
        print("   Alternative locations: 'secrets/' or project root")
        return False

    print(f"✅ Using client secrets from: {client_secrets_file}")
    
    creds = None
    
    # Load existing credentials if available
    if os.path.exists(credentials_file):
        creds = Credentials.from_authorized_user_file(credentials_file, SCOPES)
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("🔄 Refreshing expired credentials...")
            creds.refresh(Request())
        else:
            print("🔐 Starting OAuth flow...")
            print("📱 Your browser will open for Gmail authentication")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secrets_file, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(credentials_file, 'w') as token:
            token.write(creds.to_json())
        print(f"✅ Credentials saved to {credentials_file}")
    
    # Test the credentials
    try:
        service = build('gmail', 'v1', credentials=creds)
        profile = service.users().getProfile(userId='me').execute()
        
        print("🎉 Gmail authentication successful!")
        print(f"📧 Email: {profile.get('emailAddress')}")
        print(f"📊 Total messages: {profile.get('messagesTotal')}")
        print(f"🧵 Total threads: {profile.get('threadsTotal')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing Gmail connection: {e}")
        return False

def main():
    print("🚀 Gmail OAuth Setup")
    print("=" * 50)
    
    if setup_gmail_credentials():
        print("\n✅ Setup complete!")
        print("📋 Next steps:")
        print("1. Update GOOGLE_CLOUD_PROJECT in .env file")
        print("2. Set up Pub/Sub topic and subscription")
        print("3. Test the webhook endpoints")
    else:
        print("\n❌ Setup failed. Please check the instructions above.")

if __name__ == "__main__":
    main()
