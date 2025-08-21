#!/usr/bin/env python3
"""
Setup script for Qdrant vector database.
Provides options to start Qdrant with Docker and configure the application.
"""

import subprocess
import sys
import time
import requests
from pathlib import Path


def check_docker():
    """Check if Docker is available and running"""
    try:
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            return False, "Docker not installed"
        
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        if result.returncode != 0:
            return False, "Docker daemon not running"
        
        return True, "Docker is available"
    except FileNotFoundError:
        return False, "Docker not found"


def start_qdrant():
    """Start Qdrant using docker-compose"""
    print("🚀 Starting Qdrant vector database...")
    
    try:
        # Start Qdrant using docker-compose
        result = subprocess.run(['docker-compose', 'up', '-d', 'qdrant'], 
                              capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Failed to start Qdrant: {result.stderr}")
            return False
        
        print("⏳ Waiting for Qdrant to be ready...")
        
        # Wait for Qdrant to be ready
        for i in range(30):  # Wait up to 30 seconds
            try:
                response = requests.get('http://localhost:6333/health', timeout=2)
                if response.status_code == 200:
                    print("✅ Qdrant is ready!")
                    return True
            except requests.exceptions.RequestException:
                pass
            
            time.sleep(1)
            print(f"   Waiting... ({i+1}/30)")
        
        print("❌ Qdrant failed to start within 30 seconds")
        return False
        
    except FileNotFoundError:
        print("❌ docker-compose not found. Please install Docker Compose.")
        return False


def stop_qdrant():
    """Stop Qdrant"""
    print("🛑 Stopping Qdrant...")
    try:
        result = subprocess.run(['docker-compose', 'down'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Qdrant stopped successfully")
        else:
            print(f"❌ Failed to stop Qdrant: {result.stderr}")
    except FileNotFoundError:
        print("❌ docker-compose not found")


def update_env_file(vector_store_type):
    """Update .env file with vector store configuration"""
    env_file = Path('.env')
    if not env_file.exists():
        print("❌ .env file not found")
        return False
    
    # Read current content
    content = env_file.read_text()
    
    # Update vector store type
    lines = content.split('\n')
    updated_lines = []
    
    for line in lines:
        if line.startswith('VECTOR_STORE_TYPE='):
            updated_lines.append(f'VECTOR_STORE_TYPE={vector_store_type}')
        else:
            updated_lines.append(line)
    
    # Write back
    env_file.write_text('\n'.join(updated_lines))
    print(f"✅ Updated .env file: VECTOR_STORE_TYPE={vector_store_type}")
    return True


def main():
    """Main setup function"""
    print("🔧 Qdrant Setup for Support Quality Intelligence Backend")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python setup_qdrant.py start    # Start Qdrant and configure app")
        print("  python setup_qdrant.py stop     # Stop Qdrant")
        print("  python setup_qdrant.py memory   # Use memory vector store")
        print("  python setup_qdrant.py status   # Check Qdrant status")
        return
    
    command = sys.argv[1].lower()
    
    if command == 'start':
        # Check Docker
        docker_ok, docker_msg = check_docker()
        print(f"🐳 Docker status: {docker_msg}")
        
        if not docker_ok:
            print("❌ Cannot start Qdrant without Docker")
            print("💡 Using memory vector store instead...")
            update_env_file('memory')
            return
        
        # Start Qdrant
        if start_qdrant():
            update_env_file('qdrant')
            print("\n🎉 Qdrant is ready! You can now restart your application.")
        else:
            print("💡 Falling back to memory vector store...")
            update_env_file('memory')
    
    elif command == 'stop':
        stop_qdrant()
        update_env_file('memory')
    
    elif command == 'memory':
        update_env_file('memory')
        print("✅ Configured to use memory vector store")
    
    elif command == 'status':
        try:
            response = requests.get('http://localhost:6333/health', timeout=2)
            if response.status_code == 200:
                print("✅ Qdrant is running and healthy")
            else:
                print("❌ Qdrant is not responding properly")
        except requests.exceptions.RequestException:
            print("❌ Qdrant is not running")
    
    else:
        print(f"❌ Unknown command: {command}")


if __name__ == "__main__":
    main()
