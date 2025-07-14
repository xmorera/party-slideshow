from flask import Flask, jsonify, render_template, send_from_directory, request, redirect, url_for, flash
import os
import random
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime
import dropbox
import time

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, that's okay
    pass

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a random secret key
IMAGE_FOLDER = os.path.join(os.path.dirname(__file__), 'images')
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
UPLOAD_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

# Dropbox configuration
DROPBOX_APP_KEY = os.environ.get('APPKEY', 'your_new_app_key_here')
DROPBOX_APP_SECRET = os.environ.get('APPSECRET', 'your_new_app_secret_here')
DROPBOX_FOLDER = ''

def get_dropbox_client():
    """Get authenticated Dropbox client"""
    try:
        print("=== Creating Dropbox client ===")
        
        # Read access token from environment or file
        access_token = os.environ.get('DROPBOX_ACCESS_TOKEN')
        print(f"Access token from environment: {'YES' if access_token else 'NO'}")
        
        if not access_token:
            # Try to read from a token file
            token_file = os.path.join(os.path.dirname(__file__), 'dropbox-token.txt')
            print(f"Looking for token file: {token_file}")
            print(f"Token file exists: {os.path.exists(token_file)}")
            
            if os.path.exists(token_file):
                with open(token_file, 'r') as f:
                    access_token = f.read().strip()
                print(f"Token loaded from file: {access_token[:10]}... (length: {len(access_token)})")
        
        if not access_token:
            print("ERROR: No Dropbox access token found. Please set DROPBOX_ACCESS_TOKEN environment variable or create dropbox-token.txt file.")
            return None
        
        print("Creating Dropbox client with access token...")
        dbx = dropbox.Dropbox(access_token)
        print("SUCCESS: Dropbox client created")
        
        return dbx
    except Exception as e:
        print(f"ERROR creating Dropbox client: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

def sync_dropbox_images():
    """Sync images from Dropbox to local images folder"""
    try:
        print("=== Starting Dropbox sync ===")
        
        # Check environment variables
        app_key = os.environ.get('APPKEY', 'your_new_app_key_here')
        app_secret = os.environ.get('APPSECRET', 'your_new_app_secret_here')
        access_token = os.environ.get('DROPBOX_ACCESS_TOKEN')
        
        print(f"App Key: {app_key[:10]}... (length: {len(app_key)})")
        print(f"App Secret: {app_secret[:10]}... (length: {len(app_secret)})")
        print(f"Access Token from env: {'YES' if access_token else 'NO'}")
        
        # Get Dropbox client
        dbx = get_dropbox_client()
        if not dbx:
            print("ERROR: Failed to connect to Dropbox - no client returned")
            return False
        
        print("SUCCESS: Dropbox client created")
        
        # Test connection by getting account info
        try:
            account = dbx.users_get_current_account()
            print(f"SUCCESS: Connected as {account.name.display_name} ({account.email})")
        except Exception as e:
            print(f"ERROR: Failed to get account info: {e}")
            return False
        
        # Create local images directory if it doesn't exist
        os.makedirs(IMAGE_FOLDER, exist_ok=True)
        print(f"Local images folder: {IMAGE_FOLDER}")
        
        # Get list of existing local images
        existing_images = set()
        if os.path.exists(IMAGE_FOLDER):
            for f in os.listdir(IMAGE_FOLDER):
                if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS:
                    existing_images.add(f)
        
        print(f"Found {len(existing_images)} existing local images: {list(existing_images)}")
        print(f"Checking Dropbox folder: '{DROPBOX_FOLDER}' (empty = root folder)")
        
        # First, let's list the root directory to see what's there
        try:
            print("=== Listing root directory structure ===")
            result = dbx.files_list_folder('')
            root_files = result.entries
            
            for entry in root_files:
                if hasattr(entry, 'name'):
                    entry_type = "folder" if hasattr(entry, '.tag') and entry.tag == 'folder' else "file"
                    print(f"Root entry: {entry.name} ({entry_type})")
            
            # Check different possible folder locations
            folders_to_check = [
                ('sfc30', '/sfc30'),
                ('Apps', '/Apps'),
                ('Apps/sfc30', '/Apps/sfc30')
            ]
            
            dropbox_files = []
            actual_folder_path = ''
            
            # Check if there's a sfc30 subfolder
            party_folder_exists = any(
                hasattr(entry, 'name') and entry.name == 'sfc30' 
                and hasattr(entry, '.tag') and entry.tag == 'folder'
                for entry in root_files
            )
            
            # Check if there's an Apps folder
            apps_folder_exists = any(
                hasattr(entry, 'name') and entry.name == 'Apps' 
                and hasattr(entry, '.tag') and entry.tag == 'folder'
                for entry in root_files
            )
            
            if party_folder_exists:
                print("Found 'sfc30' subfolder in root, checking inside...")
                result = dbx.files_list_folder('/sfc30')
                dropbox_files = result.entries
                actual_folder_path = '/sfc30'
                
                # Handle pagination
                while result.has_more:
                    result = dbx.files_list_folder_continue(result.cursor)
                    dropbox_files.extend(result.entries)
                    
            elif apps_folder_exists:
                print("Found 'Apps' folder, checking for sfc30 inside...")
                try:
                    result = dbx.files_list_folder('/Apps')
                    apps_contents = result.entries
                    
                    for entry in apps_contents:
                        if hasattr(entry, 'name'):
                            print(f"Apps folder contains: {entry.name}")
                    
                    # Check if sfc30 exists in Apps
                    party_in_apps = any(
                        hasattr(entry, 'name') and entry.name == 'sfc30'
                        for entry in apps_contents
                    )
                    
                    if party_in_apps:
                        print("Found 'sfc30' in Apps folder!")
                        result = dbx.files_list_folder('/Apps/sfc30')
                        dropbox_files = result.entries
                        actual_folder_path = '/Apps/sfc30'
                        
                        # Handle pagination
                        while result.has_more:
                            result = dbx.files_list_folder_continue(result.cursor)
                            dropbox_files.extend(result.entries)
                    else:
                        print("No 'sfc30' found in Apps folder")
                        dropbox_files = root_files
                        actual_folder_path = ''
                        
                except Exception as e:
                    print(f"Error checking Apps folder: {e}")
                    dropbox_files = root_files
                    actual_folder_path = ''
                    
            else:
                print("No 'sfc30' or 'Apps' subfolder found, using root folder...")
                dropbox_files = root_files
                actual_folder_path = ''
                
            print(f"Using folder path: '{actual_folder_path}' (empty = root)")
                
        except dropbox.exceptions.ApiError as e:
            print(f"ERROR: Failed to list Dropbox folder '{DROPBOX_FOLDER}': {e}")
            print(f"Error details: {e.error if hasattr(e, 'error') else 'No error details'}")
            return False
        
        print(f"Found {len(dropbox_files)} files in Dropbox folder")
        
        # List all files in Dropbox folder
        for file_entry in dropbox_files:
            if hasattr(file_entry, 'name'):
                print(f"Dropbox file: {file_entry.name}")
        
        # Filter for image files and check for new ones
        new_images_count = 0
        image_files_count = 0
        
        for file_entry in dropbox_files:
            if hasattr(file_entry, 'name'):
                filename = file_entry.name
                file_ext = os.path.splitext(filename)[1].lower()
                
                if file_ext in ALLOWED_EXTENSIONS:
                    image_files_count += 1
                    print(f"Found image file: {filename}")
                    
                    # Check if it's not already local
                    if filename not in existing_images:
                        print(f"New image to download: {filename}")
                        try:
                            # Download the file using the correct folder path
                            if actual_folder_path:
                                dropbox_path = f"{actual_folder_path}/{filename}"
                            else:
                                dropbox_path = f"/{filename}"
                            
                            local_path = os.path.join(IMAGE_FOLDER, filename)
                            
                            print(f"Downloading: {dropbox_path} -> {local_path}")
                            
                            # Download file from Dropbox
                            metadata, response = dbx.files_download(dropbox_path)
                            
                            # Save to local file
                            with open(local_path, 'wb') as f:
                                f.write(response.content)
                            
                            # Set modified time to current time for proper sorting
                            current_time = time.time()
                            os.utime(local_path, (current_time, current_time))
                            
                            new_images_count += 1
                            print(f"SUCCESS: Downloaded {filename} ({len(response.content)} bytes)")
                            
                        except Exception as e:
                            print(f"ERROR: Failed to download {filename}: {e}")
                            continue
                    else:
                        print(f"Image already exists locally: {filename}")
                else:
                    print(f"Skipping non-image file: {filename} (extension: {file_ext})")
        
        print(f"=== Sync Summary ===")
        print(f"Total files in Dropbox: {len(dropbox_files)}")
        print(f"Image files in Dropbox: {image_files_count}")
        print(f"Existing local images: {len(existing_images)}")
        print(f"New images downloaded: {new_images_count}")
        print(f"=== Dropbox sync completed ===")
        
        return True
        
    except Exception as e:
        print(f"FATAL ERROR in Dropbox sync: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def upload_to_dropbox(file_path, filename):
    """Upload a file to Dropbox"""
    try:
        print(f"=== Uploading {filename} to Dropbox ===")
        
        # Get Dropbox client
        dbx = get_dropbox_client()
        if not dbx:
            print("ERROR: Failed to connect to Dropbox - no client returned")
            return False
        
        # Determine the correct folder path based on existing structure
        # Check if sfc30 folder exists in root or Apps
        try:
            result = dbx.files_list_folder('')
            root_files = result.entries
            
            # Check if sfc30 folder exists in root
            party_folder_exists = any(
                hasattr(entry, 'name') and entry.name == 'sfc30' 
                and hasattr(entry, '.tag') and entry.tag == 'folder'
                for entry in root_files
            )
            
            # Check if Apps folder exists
            apps_folder_exists = any(
                hasattr(entry, 'name') and entry.name == 'Apps' 
                and hasattr(entry, '.tag') and entry.tag == 'folder'
                for entry in root_files
            )
            
            # Determine upload path
            if party_folder_exists:
                dropbox_path = f'/sfc30/{filename}'
                print(f"Uploading to sfc30 folder: {dropbox_path}")
            elif apps_folder_exists:
                # Check if sfc30 exists in Apps
                try:
                    result = dbx.files_list_folder('/Apps')
                    apps_contents = result.entries
                    party_in_apps = any(
                        hasattr(entry, 'name') and entry.name == 'sfc30'
                        for entry in apps_contents
                    )
                    
                    if party_in_apps:
                        dropbox_path = f'/Apps/sfc30/{filename}'
                        print(f"Uploading to Apps/sfc30 folder: {dropbox_path}")
                    else:
                        # Create sfc30 folder in Apps
                        try:
                            dbx.files_create_folder_v2('/Apps/sfc30')
                            print("Created sfc30 folder in Apps")
                        except dropbox.exceptions.ApiError as e:
                            if "conflict" not in str(e).lower():
                                print(f"Error creating folder: {e}")
                        dropbox_path = f'/Apps/sfc30/{filename}'
                        print(f"Uploading to newly created Apps/sfc30 folder: {dropbox_path}")
                        
                except Exception as e:
                    print(f"Error checking Apps folder: {e}")
                    dropbox_path = f'/{filename}'
                    print(f"Uploading to root folder: {dropbox_path}")
            else:
                # Create sfc30 folder in root
                try:
                    dbx.files_create_folder_v2('/sfc30')
                    print("Created sfc30 folder in root")
                except dropbox.exceptions.ApiError as e:
                    if "conflict" not in str(e).lower():
                        print(f"Error creating folder: {e}")
                dropbox_path = f'/sfc30/{filename}'
                print(f"Uploading to newly created sfc30 folder: {dropbox_path}")
            
        except Exception as e:
            print(f"Error determining folder structure: {e}")
            dropbox_path = f'/{filename}'
            print(f"Uploading to root folder: {dropbox_path}")
        
        # Read file content and upload
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        print(f"Uploading file {filename} ({len(file_content)} bytes) to {dropbox_path}")
        
        # Upload file to Dropbox
        dbx.files_upload(
            file_content,
            dropbox_path,
            mode=dropbox.files.WriteMode.overwrite
        )
        
        print(f"SUCCESS: Uploaded {filename} to Dropbox")
        return True
        
    except Exception as e:
        print(f"ERROR uploading {filename} to Dropbox: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def get_images():
    if not os.path.exists(IMAGE_FOLDER):
        return []

    files = [
        f for f in os.listdir(IMAGE_FOLDER)
        if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS
    ]

    full_paths = [os.path.join(IMAGE_FOLDER, f) for f in files]
    if not full_paths:
        return []

    # Sort by modification time, newest first
    sorted_files = sorted(full_paths, key=os.path.getmtime, reverse=True)
    
    if len(sorted_files) == 1:
        return [os.path.basename(sorted_files[0])]

    latest = sorted_files[0]
    rest = sorted_files[1:]
    random.shuffle(rest)

    return [os.path.basename(latest)] + [os.path.basename(r) for r in rest]

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in UPLOAD_EXTENSIONS

@app.route('/')
def main():
    # Try to sync with Dropbox on page load
    try:
        sync_dropbox_images()
    except Exception as e:
        print(f"Dropbox sync failed: {e}")
    
    images = get_images()
    if not images:
        return render_template('index.html', main_image=None, carousel_images=[])
    
    main_image = images[0]
    carousel_images = images[1:] if len(images) > 1 else []
    
    return render_template('index.html', main_image=main_image, carousel_images=carousel_images)

@app.route('/sync-dropbox')
def sync_dropbox():
    """Manual Dropbox sync endpoint"""
    try:
        success = sync_dropbox_images()
        if success:
            return jsonify({'status': 'success', 'message': 'Dropbox sync completed successfully'})
        else:
            return jsonify({'status': 'error', 'message': 'Dropbox sync failed'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Dropbox sync error: {str(e)}'}), 500

@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory(IMAGE_FOLDER, filename)

@app.route('/api/images')
def api_images():
    images = get_images()
    return jsonify({
        'images': images,
        'count': len(images)
    })

@app.route('/media/<filename>')
def serve_media(filename):
    media_folder = os.path.join(os.path.dirname(__file__), 'media')
    return send_from_directory(media_folder, filename)

@app.route('/list-images')
def list_images():
    images = get_images()
    return '<br>'.join(images)

@app.route('/upload')
def upload_page():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file selected')
        return redirect(request.url)
    
    file = request.files['file']
    
    if file.filename == '':
        flash('No file selected')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):
        # Create images directory if it doesn't exist
        os.makedirs(IMAGE_FOLDER, exist_ok=True)
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        filename = f"photo_{timestamp}_{unique_id}.{file_extension}"
        
        filepath = os.path.join(IMAGE_FOLDER, filename)
        
        try:
            # Save file locally
            file.save(filepath)
            print(f"Photo saved locally: {filepath}")
            
            # Upload to Dropbox
            dropbox_success = upload_to_dropbox(filepath, filename)
            
            if dropbox_success:
                flash('Photo uploaded successfully to gallery and Dropbox!')
                print(f"SUCCESS: Photo uploaded to both local and Dropbox: {filename}")
            else:
                flash('Photo uploaded to gallery, but failed to upload to Dropbox.')
                print(f"WARNING: Photo uploaded locally but failed to upload to Dropbox: {filename}")
            
            return redirect(url_for('main'))
        except Exception as e:
            flash(f'Error uploading photo: {str(e)}')
            print(f"ERROR: Failed to upload photo: {e}")
            return redirect(request.url)
    else:
        flash('Invalid file type. Please upload JPG, PNG, GIF, or WebP images.')
        return redirect(request.url)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
