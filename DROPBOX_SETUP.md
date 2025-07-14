# Dropbox Integration Setup

## Environment Variables Setup

The app uses these environment variables for Dropbox integration:
- `APPKEY` - Your Dropbox app key
- `APPSECRET` - Your Dropbox app secret  
- `DROPBOX_ACCESS_TOKEN` - Your Dropbox access token

## Local Development Setup

### Option 1: Using .env file (Recommended)

1. **Copy the example environment file:**
   ```bash
   copy .env.example .env
   ```

2. **Edit the .env file with your credentials:**
   ```
   APPKEY=<key>
   APPSECRET=<secret>
   DROPBOX_ACCESS_TOKEN=your_access_token_here
   ```

3. **Get your access token:**
   ```bash
   python get_dropbox_token.py
   ```
   Follow the OAuth flow and copy the token to your .env file.

### Option 2: Using Windows environment variables

Set environment variables in PowerShell:
```powershell
$env:APPKEY="hf4h0oogfmfd9xb"
$env:APPSECRET="aiin4334ivtyz77"
$env:DROPBOX_ACCESS_TOKEN="your_access_token_here"
```

## Render.com Deployment Setup

1. **Go to your Render.com dashboard**
2. **Navigate to your web service**
3. **Go to Environment tab**
4. **Add these environment variables:**

   | Name | Value |
   |------|-------|
   | `APPKEY` | `key` |
   | `APPSECRET` | `secret` |
   | `DROPBOX_ACCESS_TOKEN` | `your_access_token_here` |

5. **Save and redeploy your service**

### Getting the Access Token for Production

1. **Run locally first to get token:**
   ```bash
   python get_dropbox_token.py
   ```

2. **Copy the generated token from `dropbox-token.txt`**

3. **Add it to Render.com environment variables**

## How it works

- The app connects to your Dropbox folder `/Apps/party-slideshow/`
- It compares files in that folder with your local `images/` folder
- New images are downloaded and their modification date is set to "now"
- This ensures new images appear at the top of the slideshow
- The sync happens automatically when the page loads, or manually via the sync button

## Folder Structure

```
Dropbox App Folder: /Apps/party-slideshow/
Local Images Folder: ./images/
```

Upload images to your Dropbox app folder, and they'll automatically sync to your party slideshow!

## Troubleshooting

- If sync fails, check that your environment variables are set correctly
- Make sure your Dropbox app has the correct permissions
- Check the console output for detailed error messages
- On Render.com, check the logs for any authentication errors

## Security Notes

- Never commit your `.env` file to git (it's already in .gitignore)
- Keep your access token secure
- On Render.com, environment variables are encrypted and secure
