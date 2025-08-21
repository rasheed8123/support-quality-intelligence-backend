#!/usr/bin/env python3
"""
Setup Validation Script
Validates the secure credential setup and provides recommendations.
"""

import os
import json
from pathlib import Path

# Simple validation without importing app modules to avoid conflicts

def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_status(item: str, status: bool, details: str = ""):
    """Print status with colored indicators"""
    indicator = "✅" if status else "❌"
    print(f"{indicator} {item}")
    if details:
        print(f"   {details}")

def validate_directory_structure():
    """Validate the directory structure"""
    print_header("Directory Structure Validation")
    
    directories = {
        "credentials/": "Sensitive credential files",
        "config/": "Application configuration files", 
        "secrets/": "Alternative location for secrets",
        "app/config/": "Configuration modules"
    }
    
    for dir_path, description in directories.items():
        exists = Path(dir_path).exists()
        print_status(f"{dir_path:<15} - {description}", exists)

def validate_credentials():
    """Validate credential files"""
    print_header("Credential Files Validation")

    # Service Account - check multiple locations
    service_account_locations = [
        "credentials/service-account.json",
        "secrets/service-account.json",
        "service-account.json"
    ]

    sa_found = False
    for location in service_account_locations:
        if Path(location).exists():
            print_status("Google Service Account", True, f"Found at: {location}")
            sa_found = True

            # Validate JSON structure
            try:
                with open(location, 'r') as f:
                    sa_data = json.load(f)
                    required_fields = ["type", "project_id", "private_key", "client_email"]
                    missing_fields = [field for field in required_fields if field not in sa_data]

                    if missing_fields:
                        print_status("Service Account Structure", False, f"Missing fields: {missing_fields}")
                    else:
                        print_status("Service Account Structure", True, f"Project: {sa_data['project_id']}")
            except Exception as e:
                print_status("Service Account JSON", False, f"Invalid JSON: {e}")
            break

    if not sa_found:
        print_status("Google Service Account", False, "Not found in any expected location")

    # Gmail Credentials
    gmail_locations = [
        "credentials/gmail_credentials.json",
        "gmail_credentials.json"
    ]

    gmail_found = False
    for location in gmail_locations:
        if Path(location).exists():
            print_status("Gmail Credentials", True, f"Found at: {location}")
            gmail_found = True
            break

    if not gmail_found:
        print_status("Gmail Credentials", False, "Run 'python setup_gmail_auth.py' to create")

    # State File
    state_locations = [
        "config/state.json",
        "state.json"
    ]

    for location in state_locations:
        if Path(location).exists():
            print_status("State File", True, f"Found at: {location}")
            break
    else:
        print_status("State File", False, "Will be created when webhook is registered")

def validate_environment():
    """Validate environment configuration"""
    print_header("Environment Configuration")
    
    env_vars = {
        "GOOGLE_CLOUD_PROJECT": "Google Cloud Project ID",
        "DRIVE_FOLDER_ID": "Google Drive folder to monitor",
        "WEBHOOK_PUBLIC_URL": "Public webhook URL",
        "GOOGLE_SCOPES": "Google API scopes"
    }
    
    for var, description in env_vars.items():
        value = os.getenv(var)
        has_value = bool(value and value.strip())
        print_status(f"{var:<20} - {description}", has_value, 
                    f"Value: {value[:50]}..." if has_value and len(value) > 50 else f"Value: {value}")

def validate_security():
    """Validate security setup"""
    print_header("Security Validation")
    
    # Check .gitignore
    gitignore_path = Path(".gitignore")
    if gitignore_path.exists():
        gitignore_content = gitignore_path.read_text()
        security_patterns = [
            "credentials/",
            "secrets/", 
            "*.json",
            "service-account.json",
            "gmail_credentials.json"
        ]
        
        missing_patterns = []
        for pattern in security_patterns:
            if pattern not in gitignore_content:
                missing_patterns.append(pattern)
        
        if missing_patterns:
            print_status("Git Ignore Security", False, f"Missing patterns: {missing_patterns}")
        else:
            print_status("Git Ignore Security", True, "All sensitive patterns ignored")
    else:
        print_status("Git Ignore File", False, ".gitignore file not found")
    
    # Check file permissions (Unix-like systems)
    if os.name != 'nt':  # Not Windows
        creds_dir = Path("credentials")
        if creds_dir.exists():
            for json_file in creds_dir.glob("*.json"):
                stat = json_file.stat()
                mode = oct(stat.st_mode)[-3:]
                secure = mode in ['600', '400']  # Read-only or read-write for owner only
                print_status(f"File Permissions: {json_file.name}", secure, f"Mode: {mode}")

def provide_recommendations():
    """Provide setup recommendations"""
    print_header("Recommendations")
    
    recommendations = [
        "✅ Move all credential files to credentials/ directory",
        "✅ Use environment variables for non-sensitive configuration",
        "✅ Regularly rotate service account keys",
        "✅ Monitor credential usage in Google Cloud Console",
        "✅ Set up proper file permissions (600) on Unix systems",
        "✅ Use separate credentials for different environments",
        "❌ Never commit credential files to version control",
        "❌ Never share credential files via email or chat",
        "❌ Never store credentials in public cloud storage"
    ]
    
    for rec in recommendations:
        print(f"  {rec}")

def main():
    """Main validation function"""
    print("🔍 Support Quality Intelligence Backend - Setup Validation")
    
    try:
        validate_directory_structure()
        validate_credentials()
        validate_environment()
        validate_security()
        provide_recommendations()
        
        print_header("Validation Complete")
        print("🎉 Run this script after making changes to verify your setup!")
        
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
