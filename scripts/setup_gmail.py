#!/usr/bin/env python3
"""
Setup script to create Google OAuth provider using langchain auth-client.
This only needs to be run once to configure the OAuth provider.
"""
import asyncio
import os
import json
from pathlib import Path
from langchain_auth import Client


async def setup_google_oauth_provider():
    """Create Google OAuth provider configuration."""
    
    # Get LangSmith API key
    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        raise ValueError("LANGSMITH_API_KEY environment variable must be set")
    
    # Look for Google OAuth client secrets
    secrets_dir = Path(__file__).parent.parent / "eaia" / ".secrets"
    secrets_path = secrets_dir / "secrets.json"
    
    if not secrets_path.exists():
        print(f"Error: Google OAuth client secrets file not found at {secrets_path}")
        print("Please:")
        print("1. Follow the Google OAuth setup instructions in the README")
        print("2. Download your client secrets JSON file")
        print("3. Save it as eaia/.secrets/secrets.json")
        return False
    
    # Load client secrets
    with open(secrets_path) as f:
        secrets = json.load(f)
    
    # Extract OAuth configuration from Google client secrets
    if "web" in secrets:
        oauth_config = secrets["web"]
    elif "installed" in secrets:
        oauth_config = secrets["installed"]
    else:
        raise ValueError("Invalid Google client secrets format")
    
    client_id = oauth_config["client_id"]
    client_secret = oauth_config["client_secret"]
    
    # Create langchain auth client
    client = Client(api_key=api_key)
    
    try:
        # Check if Google provider already exists
        try:
            providers = await client.list_oauth_providers()
            existing_google = next((p for p in providers if p.provider_id == "google"), None)
            
            if existing_google:
                print(f"Google OAuth provider already exists: {existing_google}")
                print("Setup complete! You can now use the executive assistant.")
                return True
        except Exception as e:
            print(f"Warning: Could not check existing providers: {e}")
        
        # Create Google OAuth provider
        print("Creating Google OAuth provider...")
        provider = await client.create_oauth_provider(
            provider_id="google",
            name="Google",
            client_id=client_id,
            client_secret=client_secret,
            auth_url="https://accounts.google.com/o/oauth2/auth",
            token_url="https://oauth2.googleapis.com/token",
        )
        
        print(f"Successfully created Google OAuth provider: {provider}")
        print("Setup complete! You can now use the executive assistant.")
        return True
        
    except Exception as e:
        print(f"Error creating Google OAuth provider: {e}")
        return False
        
    finally:
        await client.close()


if __name__ == "__main__":
    success = asyncio.run(setup_google_oauth_provider())
    if not success:
        exit(1)