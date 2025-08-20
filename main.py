#!/usr/bin/env python3
"""
Main entry point for the Support Quality Intelligence Backend.
Run this file to start the FastAPI server on port 5000.
"""

if __name__ == "__main__":
    import uvicorn
    import os
    from dotenv import load_dotenv

    # Load environment variables
    load_dotenv()

    # Get the webhook URL from environment and extract base URL
    webhook_url = os.getenv("WEBHOOK_PUBLIC_URL", "Not configured")
    if webhook_url != "Not configured" and "/webhook/drive" in webhook_url:
        tunnel_base_url = webhook_url.replace("/webhook/drive", "")
    else:
        tunnel_base_url = webhook_url

    print("🚀 Starting Support Quality Intelligence Backend...")
    print("🔒 Server will run on: http://localhost:5000")
    print(f"🌐 Tunnel URL: {tunnel_base_url}")

    # Start the FastAPI server on port 5000
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=5000,
        reload=False,  # Disable reload to avoid multiprocessing issues
        log_level="info"
    )
