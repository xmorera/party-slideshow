# Dropbox Integration Setup

## Setting up Dropbox Access Token

To sync images from your Dropbox app folder, you need to get an access token:

1. **Run the token generation script:**
   ```bash
   python get_dropbox_token.py
   ```

2. **Follow the OAuth flow:**
   - The script will display a URL
   - Open the URL in your browser
   - Log in to Dropbox if needed
   - Click "Allow" to grant access to your app
   - Copy the authorization code that appears

3. **Enter the code:**
   - Paste the authorization code into the terminal when prompted
   - The script will save your access token to `dropbox-token.txt`

4. **Test the sync:**
   - Start your Flask app: `python app.py`
   - Visit the main page - it will automatically try to sync on load
   - Or click the "☁️ Sync" button to manually trigger sync

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

- If sync fails, check that your `dropbox-token.txt` file exists and contains a valid token
- Make sure your Dropbox app has the correct permissions
- Check the console output for detailed error messages
