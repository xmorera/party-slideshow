#!/usr/bin/env python3
"""
Test script to verify environment variables are loaded correctly
"""

import os

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded .env file successfully")
except ImportError:
    print("❌ python-dotenv not installed")

def test_environment_variables():
    """Test all required environment variables"""
    
    print("\n=== Environment Variables Test ===")
    
    # Test each variable
    variables = [
        'DROPBOX_ACCESS_TOKEN',
        'DROPBOX_REFRESH_TOKEN', 
        'APPKEY',
        'APPSECRET'
    ]
    
    all_present = True
    
    for var in variables:
        value = os.environ.get(var)
        if value:
            if len(value) > 20:
                preview = value[:20] + '...'
            else:
                preview = value
            print(f"✅ {var}: {preview} (length: {len(value)})")
        else:
            print(f"❌ {var}: NOT SET")
            all_present = False
    
    print(f"\n=== Summary ===")
    if all_present:
        print("✅ All environment variables are set!")
        
        # Test refresh token functionality
        print("\n=== Testing Refresh Token ===")
        try:
            import requests
            
            refresh_token = os.environ.get('DROPBOX_REFRESH_TOKEN')
            app_key = os.environ.get('APPKEY')
            app_secret = os.environ.get('APPSECRET')
            
            response = requests.post('https://api.dropboxapi.com/oauth2/token', data={
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': app_key,
                'client_secret': app_secret
            })
            
            if response.status_code == 200:
                token_data = response.json()
                new_access_token = token_data.get('access_token')
                print(f"✅ Refresh token works! New access token: {new_access_token[:20]}...")
                
                # Test the new access token
                import dropbox
                test_dbx = dropbox.Dropbox(new_access_token)
                account = test_dbx.users_get_current_account()
                print(f"✅ New access token works! Connected as: {account.name.display_name}")
                
                return True
            else:
                print(f"❌ Refresh token failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error testing refresh token: {e}")
            return False
    else:
        print("❌ Some environment variables are missing!")
        return False

if __name__ == "__main__":
    test_environment_variables()