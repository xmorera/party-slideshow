#!/usr/bin/env python3
"""
Test script to verify automatic token refresh functionality
"""

import os
import sys
import dropbox

# Add the parent directory to the path so we can import from app.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import get_dropbox_client_with_retry

def test_token_refresh():
    """Test the automatic token refresh functionality"""
    print("Testing Dropbox Token Refresh Functionality")
    print("=" * 50)
    
    # Test 1: Try to get a Dropbox client
    print("\nTest 1: Getting Dropbox client with auto-refresh...")
    dbx = get_dropbox_client_with_retry()
    
    if dbx:
        print("✅ SUCCESS: Dropbox client created successfully")
        
        # Test 2: Try to make an API call
        print("\nTest 2: Testing API call...")
        try:
            account = dbx.users_get_current_account()
            print(f"✅ SUCCESS: Connected as {account.name.display_name} ({account.email})")
            
            # Test 3: Try to list files
            print("\nTest 3: Testing file listing...")
            try:
                result = dbx.files_list_folder('')
                print(f"✅ SUCCESS: Found {len(result.entries)} items in root folder")
                
                # Show first few entries
                for i, entry in enumerate(result.entries[:3]):
                    entry_type = "📁" if hasattr(entry, '.tag') and entry.tag == 'folder' else "📄"
                    print(f"  {entry_type} {entry.name}")
                    
            except Exception as e:
                print(f"❌ ERROR: Failed to list files: {e}")
                
        except dropbox.exceptions.AuthError as auth_error:
            print(f"❌ AUTHENTICATION ERROR: {auth_error}")
            print("This suggests that token refresh is not working properly")
            
        except Exception as e:
            print(f"❌ ERROR: API call failed: {e}")
            
    else:
        print("❌ FAILED: Could not create Dropbox client")
        print("\nPossible issues:")
        print("1. Missing environment variables (APPKEY, APPSECRET, DROPBOX_REFRESH_TOKEN)")
        print("2. Invalid refresh token")
        print("3. Network connectivity issues")
        print("\nTo fix:")
        print("1. Run: python generate_refresh_token.py")
        print("2. Set the environment variables as shown")
        print("3. Try this test again")
    
    print("\n" + "=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    test_token_refresh()
