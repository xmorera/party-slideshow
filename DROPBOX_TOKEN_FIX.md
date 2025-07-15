# Dropbox Token Expiration Fix

## The Problem
Your Dropbox access token is expiring because modern Dropbox apps use **short-lived tokens** (4 hours) by default. This is a security improvement, but requires using **refresh tokens** for long-term access.

## Enhanced Solution with Guard Clauses

### Guard Clause Protection
The application now includes multiple guard clauses to handle token expiration:

1. **Startup Check**: Tests token validity when the app starts
2. **Upload Guard**: Tests connection before attempting file upload
3. **Retry Logic**: Automatically refreshes tokens and retries failed operations
4. **Error Handling**: Provides clear error messages and fallback behavior

### Token Expiration Flow
```
1. User uploads file → 2. Guard clause tests token → 3. Token expired? → 4. Auto-refresh → 5. Retry upload
                                    ↓                                                    ↓
                           6. Success: Upload continues                    7. Fail: Show error message
```

## Solution Options

### Option 1: Use Refresh Tokens (Recommended)
Refresh tokens don't expire and are the modern, secure approach.

#### Step 1: Generate a Refresh Token
```bash
# Make sure your environment variables are set
set APPKEY=your_app_key_here
set APPSECRET=your_app_secret_here

# Run the token generator
python generate_refresh_token.py
```

#### Step 2: Set Environment Variables
After running the script, set these environment variables:
```bash
set APPKEY=your_app_key
set APPSECRET=your_app_secret
set DROPBOX_REFRESH_TOKEN=your_refresh_token
```

### Option 2: Request Long-lived Tokens (Legacy)
If you want to keep using access tokens, you can request long-lived tokens from Dropbox:

1. Go to your [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. Select your app
3. Go to the "Settings" tab
4. Under "OAuth 2", find "Access token expiration"
5. Select "No expiration" (if available)
6. Generate a new access token

**Note**: This option may not be available for new apps and is being phased out.

### Option 3: Automatic Token Refresh (Advanced)
For production applications, you can implement automatic token refresh:

```python
def refresh_access_token(refresh_token, app_key, app_secret):
    """Refresh an expired access token"""
    try:
        # Use the refresh token to get a new access token
        import requests
        
        response = requests.post('https://api.dropboxapi.com/oauth2/token', data={
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': app_key,
            'client_secret': app_secret
        })
        
        if response.status_code == 200:
            token_data = response.json()
            return token_data['access_token']
        else:
            print(f"Failed to refresh token: {response.text}")
            return None
    except Exception as e:
        print(f"Error refreshing token: {e}")
        return None
```

## Current Code Changes
I've enhanced your `app.py` with comprehensive guard clauses and error handling:

### Guard Clauses Added:
1. **`test_dropbox_token()`** - Utility function to test token validity
2. **Startup guard** in `main()` - Tests token when app starts
3. **Upload guard** in `upload_file()` - Tests connection before upload
4. **Retry guard** in `upload_to_dropbox()` - Handles token expiration during upload

### Error Handling Flow:
- **Token expires** → **Auto-detection** → **Refresh attempt** → **Retry operation** → **Success/Fail with clear message**

### Features:
- ✅ **Automatic token refresh** (no manual intervention)
- ✅ **Graceful error handling** (users get clear feedback)
- ✅ **Fallback behavior** (local save continues even if Dropbox fails)
- ✅ **Comprehensive logging** (easy debugging)
- ✅ **Production ready** (handles all edge cases)

## Environment Variables Needed

### For Refresh Token Approach (Recommended):
```
APPKEY=your_app_key
APPSECRET=your_app_secret
DROPBOX_REFRESH_TOKEN=your_refresh_token
```

### For Access Token Approach (Legacy):
```
DROPBOX_ACCESS_TOKEN=your_access_token
```

## Quick Fix for Right Now
If you need an immediate fix:

1. Go to your [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. Select your app
3. Go to "Settings" → "OAuth 2"
4. Click "Generate access token"
5. Copy the new token and update your `DROPBOX_ACCESS_TOKEN` environment variable

This will give you another 4 hours, but you should implement refresh tokens for a permanent solution.

## Testing
After setting up refresh tokens, restart your application and check the console output. You should see:
```
=== Creating Dropbox client ===
Using refresh token for authentication...
SUCCESS: Dropbox client created with refresh token
```

## Troubleshooting

### "expired_access_token" Error
- Your access token has expired (4 hours)
- Generate a new access token OR switch to refresh tokens

### "Invalid refresh token" Error
- Your refresh token is invalid
- Run `generate_refresh_token.py` again to get a new one

### "App key/secret not found" Error
- Make sure APPKEY and APPSECRET environment variables are set
- Check your Dropbox App Console for the correct values

## Production Deployment
For production (like on Render), set these environment variables in your hosting platform:

```
APPKEY=your_app_key
APPSECRET=your_app_secret
DROPBOX_REFRESH_TOKEN=your_refresh_token
```

Remove or don't set `DROPBOX_ACCESS_TOKEN` to force the use of refresh tokens.
