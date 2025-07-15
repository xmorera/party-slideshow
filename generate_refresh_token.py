#!/usr/bin/env python3
"""
Script to generate a Dropbox refresh token for long-term authentication.
Run this script once to get a refresh token that doesn't expire.
"""

import dropbox
import os
import webbrowser
import urllib.parse

def generate_refresh_token():
    """Generate a refresh token for Dropbox authentication"""
    
    # Get your app credentials from environment variables
    app_key = os.environ.get('APPKEY')
    app_secret = os.environ.get('APPSECRET')
    
    if not app_key or not app_secret:
        print("ERROR: Please set APPKEY and APPSECRET environment variables")
        print("You can get these from your Dropbox App Console at:")
        print("https://www.dropbox.com/developers/apps")
        return None
    
    print(f"App Key: {app_key}")
    print(f"App Secret: {app_secret[:10]}...")
    
    # Create OAuth2 flow
    auth_flow = dropbox.DropboxOAuth2FlowNoRedirect(
        app_key, 
        app_secret,
        token_access_type='offline'  # This is key for getting refresh tokens
    )
    
    # Get authorization URL
    authorize_url = auth_flow.start()
    print("\n" + "="*60)
    print("STEP 1: Go to this URL and authorize the app:")
    print(authorize_url)
    print("="*60)
    
    # Try to open the URL automatically
    try:
        webbrowser.open(authorize_url)
        print("Opening browser automatically...")
    except:
        print("Please copy and paste the URL above into your browser.")
    
    # Get the authorization code from user
    auth_code = input("\nSTEP 2: Enter the authorization code here: ").strip()
    
    try:
        # Complete the OAuth flow
        oauth_result = auth_flow.finish(auth_code)
        
        print("\n" + "="*60)
        print("SUCCESS! Here are your tokens:")
        print("="*60)
        print(f"Access Token: {oauth_result.access_token}")
        print(f"Refresh Token: {oauth_result.refresh_token}")
        print(f"Account ID: {oauth_result.account_id}")
        
        # Save to environment file
        env_content = f"""# Dropbox Configuration
APPKEY={app_key}
APPSECRET={app_secret}
DROPBOX_ACCESS_TOKEN={oauth_result.access_token}
DROPBOX_REFRESH_TOKEN={oauth_result.refresh_token}
"""
        
        with open('.env', 'w') as f:
            f.write(env_content)
        
        print("\n" + "="*60)
        print("Environment file (.env) created with your tokens!")
        print("="*60)
        print("For production, set these environment variables:")
        print(f"APPKEY={app_key}")
        print(f"APPSECRET={app_secret}")
        print(f"DROPBOX_REFRESH_TOKEN={oauth_result.refresh_token}")
        print("\nThe refresh token will NOT expire and is the recommended approach.")
        print("="*60)
        
        return oauth_result.refresh_token
        
    except Exception as e:
        print(f"\nERROR: Failed to complete OAuth flow: {e}")
        return None

if __name__ == "__main__":
    print("Dropbox Refresh Token Generator")
    print("=" * 40)
    
    refresh_token = generate_refresh_token()
    if refresh_token:
        print("\nSUCCESS: Your refresh token has been generated!")
        print("You can now use it in your application.")
    else:
        print("\nFAILED: Could not generate refresh token.")
