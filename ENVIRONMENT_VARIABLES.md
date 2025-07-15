# Environment Variable Management for Dropbox Integration

## Overview

This system automatically manages Dropbox access tokens to prevent expiration issues. It works differently in development vs production environments.

## How It Works

### Development Environment
- **Local .env file**: Environment variables are automatically updated in a local `.env` file
- **Immediate effect**: Changes take effect immediately in the running application
- **Persistence**: Settings persist across app restarts

### Production Environment (Render)
- **Manual update required**: You must manually update environment variables in Render's dashboard
- **No automatic updates**: The `.env` file approach doesn't work in production environments
- **Restart required**: After updating environment variables, restart the service

## Environment Variables

### Required Variables
```
APPKEY=your_dropbox_app_key
APPSECRET=your_dropbox_app_secret
DROPBOX_ACCESS_TOKEN=your_access_token
DROPBOX_REFRESH_TOKEN=your_refresh_token
```

### Token Types
- **Access Token**: Short-lived (4 hours), used for API calls
- **Refresh Token**: Long-lived (doesn't expire), used to get new access tokens

## Usage

### 1. Generate Initial Tokens
1. Go to `/generate-dropbox-token` in your web browser
2. Enter your Dropbox app credentials
3. Complete the OAuth flow
4. Tokens will be generated and automatically saved locally

### 2. Refresh Access Token
- **Automatic**: The app automatically refreshes tokens when they expire
- **Manual**: Use the "Refresh Access Token" button in the token generator

### 3. Deploy to Render

#### For New Deployments:
1. Generate tokens using the web interface
2. Copy all environment variables from the results
3. Set them in your Render dashboard under "Environment Variables"
4. Deploy your app

#### For Existing Deployments:
1. Go to your Render dashboard
2. Navigate to your service
3. Go to "Environment Variables" section
4. Update the following variables:
   - `DROPBOX_ACCESS_TOKEN`
   - `DROPBOX_REFRESH_TOKEN`
   - `APPKEY`
   - `APPSECRET`
5. Restart your service

## Important Notes

### Development vs Production

| Feature | Development | Production (Render) |
|---------|-------------|-------------------|
| Auto-update .env | ✅ Yes | ❌ No |
| Manual env update | ✅ Yes | ✅ Yes |
| Requires restart | ❌ No | ✅ Yes |
| Persistence | ✅ Yes | ✅ Yes |

### Render Limitations
- Render doesn't allow runtime modification of environment variables
- Changes must be made through the Render dashboard
- Service restart is required after env var changes
- The app cannot automatically update production environment variables

### Best Practices
1. **Use refresh tokens**: They don't expire and automatically renew access tokens
2. **Monitor token status**: Check logs for token refresh activities
3. **Keep tokens secure**: Never commit tokens to version control
4. **Update production regularly**: Manually update production tokens when needed

## API Endpoints

### `/generate-dropbox-token`
- **Method**: GET
- **Purpose**: Serve the token generation web interface

### `/generate-tokens`
- **Method**: POST
- **Purpose**: Generate new tokens from OAuth code
- **Auto-updates**: Local environment variables

### `/update-access-token`
- **Method**: POST
- **Purpose**: Refresh access token from refresh token
- **Auto-updates**: Local DROPBOX_ACCESS_TOKEN

### `/test-dropbox-token`
- **Method**: POST
- **Purpose**: Test if tokens are working correctly

## Troubleshooting

### Common Issues

1. **Token expired error**
   - Run the token refresh process
   - Check if refresh token is valid
   - Regenerate tokens if needed

2. **Environment variables not updating**
   - Check if .env file exists and is writable
   - Verify permissions on the file
   - For production, manually update in Render dashboard

3. **Dropbox API errors**
   - Verify app key and secret are correct
   - Check if the Dropbox app is configured properly
   - Ensure proper OAuth scopes are set

### Debug Steps
1. Check the app logs for token refresh activities
2. Verify environment variables are set correctly
3. Test tokens using the web interface
4. Check Dropbox app configuration

## Security Considerations

- Never expose tokens in client-side code
- Use HTTPS in production
- Regularly rotate app secrets
- Monitor token usage logs
- Keep dependencies updated

## Future Enhancements

Potential improvements:
1. Automatic token rotation scheduling
2. Token status dashboard
3. Integration with other cloud storage providers
4. Automated deployment scripts for Render
5. Token backup and recovery system
