# Dropbox Folder Structure Fix

## Problem
The app was creating nested folders like `sfc30/sfc30` instead of uploading directly to the app folder root.

## Root Cause
When using a Dropbox app, you already operate within your app's designated folder space. The complex folder detection logic was creating unnecessary nested structures.

## Solution
Simplified the upload and sync functions to work directly with the app folder root:

### Upload Function (`upload_to_dropbox`)
- **Before**: Complex logic to detect and create `sfc30` folders
- **After**: Direct upload to app folder root (`/{filename}`)

### Sync Function (`sync_dropbox_images`)
- **Before**: Complex logic to check multiple folder locations (`/sfc30`, `/Apps/sfc30`, etc.)
- **After**: Direct listing and download from app folder root

## Changes Made

1. **Simplified upload path**: All images now upload to `/{filename}` (root of app folder)
2. **Simplified sync path**: All images are read from app folder root
3. **Removed complex folder detection**: No more nested folder creation logic
4. **Direct operation**: App now works directly within the Dropbox app folder space

## Result
- Images upload directly to: `https://www.dropbox.com/home/Apps/sfc30/` (no nested sfc30 folder)
- Cleaner folder structure
- Simpler code that's easier to maintain
- Works correctly with Dropbox app permissions

## Testing
1. Upload a new image via the web interface
2. Check Dropbox at `https://www.dropbox.com/home/Apps/sfc30/`
3. Verify the image appears directly in the app folder (not in a nested sfc30 subfolder)
4. Verify the slideshow displays the image correctly

## Environment Variables
The token management system will automatically update:
- `DROPBOX_ACCESS_TOKEN` - automatically refreshed
- `DROPBOX_REFRESH_TOKEN` - long-lived token for automatic refresh
- Local `.env` file updated automatically in development
- Production (Render) requires manual environment variable updates
