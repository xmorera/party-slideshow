#!/usr/bin/env python3
"""
Script to help update Render environment variables
This script will show you the exact values to copy to Render
"""

import os

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded .env file successfully")
except ImportError:
    print("❌ python-dotenv not installed")

def show_render_env_vars():
    """Show environment variables formatted for Render"""
    
    print("\n" + "="*60)
    print("RENDER ENVIRONMENT VARIABLES")
    print("Copy these to your Render service environment variables:")
    print("="*60)
    
    variables = [
        'APPKEY',
        'APPSECRET',
        'DROPBOX_ACCESS_TOKEN',
        'DROPBOX_REFRESH_TOKEN'
    ]
    
    for var in variables:
        value = os.environ.get(var)
        if value:
            print(f"\n{var}")
            print(f"{value}")
            print("-" * 40)
        else:
            print(f"\n❌ {var}: NOT SET")
    
    print("\n" + "="*60)
    print("INSTRUCTIONS:")
    print("1. Go to your Render dashboard")
    print("2. Navigate to your service settings")
    print("3. Go to 'Environment Variables'")
    print("4. Add/update each variable above")
    print("5. Restart your service")
    print("="*60)

if __name__ == "__main__":
    show_render_env_vars()