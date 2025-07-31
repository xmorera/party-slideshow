#!/usr/bin/env python3
"""
Test script to verify environment variables are loaded correctly
"""

import os
import sys

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Loaded .env file successfully")
except ImportError:
    print("⚠️ python-dotenv not installed, using system environment variables")
except Exception as e:
    print(f"⚠️ Could not load .env file: {e}")

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
            
            print(f"Testing with:")
            print(f"  Refresh token: {refresh_token[:20]}...")
            print(f"  App key: {app_key}")
            print(f"  App secret: {app_secret[:10]}...")
            
            response = requests.post('https://api.dropboxapi.com/oauth2/token', data={
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
                'client_id': app_key,
                'client_secret': app_secret
            })
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                token_data = response.json()
                new_access_token = token_data.get('access_token')
                print(f"✅ Refresh token works! New access token: {new_access_token[:20]}...")
                
                # Test the new access token
                try:
                    import dropbox
                    test_dbx = dropbox.Dropbox(new_access_token)
                    account = test_dbx.users_get_current_account()
                    print(f"✅ New access token works! Connected as: {account.name.display_name}")
                    print(f"✅ Email: {account.email}")
                    
                    # Update the .env file with the new token
                    update_env_file_token(new_access_token)
                    
                    return True
                except Exception as dropbox_error:
                    print(f"❌ Error testing new access token with Dropbox: {dropbox_error}")
                    return False
                    
            else:
                print(f"❌ Refresh token failed: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error details: {error_data}")
                except:
                    print(f"Response text: {response.text}")
                return False
                
        except ImportError as ie:
            print(f"❌ Import error: {ie}")
            print("Make sure you have installed: pip install requests dropbox")
            return False
        except Exception as e:
            print(f"❌ Error testing refresh token: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return False
    else:
        print("❌ Some environment variables are missing!")
        print("\nTo fix this, add the missing variables to your .env file:")
        print("DROPBOX_ACCESS_TOKEN=your_access_token_here")
        print("DROPBOX_REFRESH_TOKEN=your_refresh_token_here")
        print("APPKEY=your_app_key_here")
        print("APPSECRET=your_app_secret_here")
        return False

def update_env_file_token(new_token):
    """Update the .env file with a new access token"""
    try:
        env_file = '.env'
        if not os.path.exists(env_file):
            print("⚠️ .env file not found, cannot update token")
            return False
            
        # Read current content
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        # Update the access token line
        updated = False
        for i, line in enumerate(lines):
            if line.startswith('DROPBOX_ACCESS_TOKEN='):
                lines[i] = f'DROPBOX_ACCESS_TOKEN={new_token}\n'
                updated = True
                break
        
        # If not found, add it
        if not updated:
            lines.append(f'DROPBOX_ACCESS_TOKEN={new_token}\n')
        
        # Write back to file
        with open(env_file, 'w') as f:
            f.writelines(lines)
        
        print("✅ Updated .env file with new access token")
        return True
        
    except Exception as e:
        print(f"❌ Error updating .env file: {e}")
        return False

if __name__ == "__main__":
    success = test_environment_variables()
    
    if success:
        print("\n🎉 All tests passed! Your Dropbox integration should work.")
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")
        sys.exit(1)