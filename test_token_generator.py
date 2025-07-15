#!/usr/bin/env python3
"""
Test script for the web-based token generator
"""

import requests
import json
import os

def test_token_generator():
    """Test the token generator endpoints"""
    
    # Base URL for your app
    base_url = "http://localhost:5000"  # Change this to your actual URL
    
    print("Testing Token Generator Endpoints")
    print("=" * 50)
    
    # Test 1: Check if the token generator page loads
    print("\n1. Testing token generator page...")
    try:
        response = requests.get(f"{base_url}/generate-dropbox-token")
        if response.status_code == 200:
            print("✅ Token generator page loads successfully")
        else:
            print(f"❌ Token generator page failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error accessing token generator page: {e}")
    
    # Test 2: Test token generation endpoint (with dummy data)
    print("\n2. Testing token generation endpoint...")
    try:
        test_data = {
            "app_key": "test_key",
            "app_secret": "test_secret",
            "auth_code": "test_code"
        }
        
        response = requests.post(
            f"{base_url}/generate-tokens",
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            if not data.get('success'):
                print("✅ Token generation endpoint responds correctly (expected failure with test data)")
            else:
                print("⚠️  Token generation endpoint returned success with test data (unexpected)")
        else:
            print(f"❌ Token generation endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing token generation endpoint: {e}")
    
    # Test 3: Test token testing endpoint
    print("\n3. Testing token test endpoint...")
    try:
        test_data = {
            "refresh_token": "test_refresh_token",
            "app_key": "test_key",
            "app_secret": "test_secret"
        }
        
        response = requests.post(
            f"{base_url}/test-dropbox-token",
            json=test_data,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            if not data.get('success'):
                print("✅ Token test endpoint responds correctly (expected failure with test data)")
            else:
                print("⚠️  Token test endpoint returned success with test data (unexpected)")
        else:
            print(f"❌ Token test endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing token test endpoint: {e}")
    
    # Test 4: Test access token refresh endpoint
    print("\n4. Testing access token refresh endpoint...")
    try:
        response = requests.post(
            f"{base_url}/update-access-token",
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            if not data.get('success'):
                print("✅ Access token refresh endpoint responds correctly (expected failure without proper setup)")
            else:
                print("⚠️  Access token refresh endpoint returned success (unexpected without proper setup)")
        else:
            print(f"❌ Access token refresh endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing access token refresh endpoint: {e}")
    
    print("\n" + "=" * 50)
    print("Test completed!")
    print("\nTo use the token generator:")
    print(f"1. Go to: {base_url}/generate-dropbox-token")
    print("2. Enter your Dropbox app credentials")
    print("3. Follow the steps to generate tokens")
    print("4. Tokens will be automatically saved to .env file locally")
    print("5. For production deployment, manually update environment variables in Render")
    print("\nNew features:")
    print("- Automatic environment variable updates (development only)")
    print("- Access token refresh capability")
    print("- Enhanced production deployment guidance")

if __name__ == "__main__":
    test_token_generator()
