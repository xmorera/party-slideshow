#!/usr/bin/env python3
"""
Script to get Dropbox access token for the party slideshow app.
Run this once to get your access token, then save it to dropbox-token.txt
"""

import dropbox
import os

# Read app key and secret from dropbox-key.txt
def read_dropbox_credentials():
    try:
        with open('dropbox-key.txt', 'r') as f:
            lines = f.read().strip().split('\n')
            app_key = lines[1].strip()
            app_secret = lines[3].strip()
            return app_key, app_secret
    except Exception as e:
        print(f"Error reading dropbox-key.txt: {e}")
        return None, None

def get_access_token():
    app_key, app_secret = read_dropbox_credentials()
    
    if not app_key or not app_secret:
        print("Could not read Dropbox app key and secret from dropbox-key.txt")
        return None
    
    print("Dropbox App Key:", app_key)
    print("Dropbox App Secret:", app_secret)
    
    # Create OAuth flow
    auth_flow = dropbox.DropboxOAuth2FlowNoRedirect(app_key, app_secret)
    
    # Get authorization URL
    authorize_url = auth_flow.start()
    print("\n1. Go to this URL in your browser:")
    print(authorize_url)
    print("\n2. Click 'Allow' (you might have to log in first)")
    print("3. Copy the authorization code that appears")
    
    # Get authorization code from user
    auth_code = input("\nEnter the authorization code here: ").strip()
    
    try:
        # Complete the authorization and get access token
        oauth_result = auth_flow.finish(auth_code)
        access_token = oauth_result.access_token
        
        print(f"\nSuccess! Your access token is: {access_token}")
        
        # Save to file
        with open('dropbox-token.txt', 'w') as f:
            f.write(access_token)
        
        print("Access token saved to dropbox-token.txt")
        
        # Test the token
        print("\nTesting token...")
        dbx = dropbox.Dropbox(access_token)
        account = dbx.users_get_current_account()
        print(f"Connected as: {account.name.display_name} ({account.email})")
        
        return access_token
        
    except Exception as e:
        print(f"Error getting access token: {e}")
        return None

if __name__ == "__main__":
    get_access_token()
