from flask import Flask, jsonify, render_template, send_from_directory, request, redirect, url_for, flash
import os
import random
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime
import dropbox
import time
import sys  # Add this import

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # python-dotenv not installed, that's okay
    pass

def update_env_variable(key, value):
    """Update environment variable both in current process and .env file"""
    try:
        # Update in current process
        os.environ[key] = value
        
        # Update in .env file for persistence
        env_file_path = os.path.join(os.path.dirname(__file__), '.env')
        
        # Read existing .env file
        env_vars = {}
        if os.path.exists(env_file_path):
            with open(env_file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        env_vars[k] = v
        
        # Update the variable
        env_vars[key] = value
        
        # Write back to .env file
        with open(env_file_path, 'w') as f:
            for k, v in env_vars.items():
                f.write(f"{k}={v}\n")
        
        print(f"SUCCESS: Updated {key} in environment and .env file")
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to update {key}: {e}")
        return False

def get_current_access_token():
    """Get current access token from a refresh token"""
    try:
        refresh_token = os.environ.get('DROPBOX_REFRESH_TOKEN')
        app_key = os.environ.get('APPKEY')
        app_secret = os.environ.get('APPSECRET')
        
        if not all([refresh_token, app_key, app_secret]):
            return None
            
        # Create Dropbox client with refresh token
        dbx = dropbox.Dropbox(
            oauth2_refresh_token=refresh_token,
            app_key=app_key,
            app_secret=app_secret
        )
        
        # Get current access token
        auth_result = dbx._oauth2_access_token_from_refresh_token(refresh_token)
        return auth_result.get('access_token')
        
    except Exception as e:
        print(f"ERROR: Failed to get current access token: {e}")
        return None

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
    """Get authenticated Dropbox client with automatic token refresh"""
    try:
        print("=== Creating Dropbox client ===")
        
        # Always prioritize refresh token approach (recommended)
        refresh_token = os.environ.get('DROPBOX_REFRESH_TOKEN')
        app_key = os.environ.get('APPKEY', 'your_new_app_key_here')
        app_secret = os.environ.get('APPSECRET', 'your_new_app_secret_here')
        
        # If we have refresh token and app credentials, use them directly
        if refresh_token and app_key != 'your_new_app_key_here' and app_secret != 'your_new_app_secret_here':
            print("Using refresh token for authentication (recommended approach)...")
            try:
                # Create client with refresh token - this will auto-refresh if needed
                dbx = dropbox.Dropbox(
                    oauth2_refresh_token=refresh_token,
                    app_key=app_key,
                    app_secret=app_secret
                )
                
                # Test the connection to ensure it works
                try:
                    account = dbx.users_get_current_account()
                    print(f"SUCCESS: Dropbox client created with refresh token - Connected as {account.name.display_name}")
                    
                    # Update the access token in environment for other parts of the app
                    current_token = dbx._oauth2_access_token
                    if current_token:
                        update_env_variable('DROPBOX_ACCESS_TOKEN', current_token)
                        print("Updated DROPBOX_ACCESS_TOKEN with fresh token from refresh")
                    
                    return dbx
                    
                except dropbox.exceptions.AuthError as auth_error:
                    print(f"Auth error with refresh token: {auth_error}")
                    # If refresh token fails, fall through to access token method
                    pass
                except Exception as test_error:
                    print(f"Connection test failed with refresh token: {test_error}")
                    # If connection test fails, fall through to access token method
                    pass
                    
            except Exception as e:
                print(f"Failed to create client with refresh token: {e}")
                # Fall back to access token if refresh token fails
        else:
            print("Missing refresh token or app credentials, falling back to access token...")
        
        # Fall back to access token (legacy approach) - but with auto-refresh capability
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
            print("ERROR: No Dropbox access token or refresh token found.")
            print("Please set either:")
            print("1. DROPBOX_REFRESH_TOKEN (recommended) + APPKEY + APPSECRET")
            print("2. DROPBOX_ACCESS_TOKEN (legacy)")
            return None
        
        print("Creating Dropbox client with access token...")
        dbx = dropbox.Dropbox(access_token)
        
        # Test the access token - if expired, try to refresh
        try:
            account = dbx.users_get_current_account()
            print(f"SUCCESS: Dropbox client created with access token - Connected as {account.name.display_name}")
            return dbx
            
        except dropbox.exceptions.AuthError as auth_error:
            print(f"Authentication error with access token: {auth_error}")
            
            if 'expired_access_token' in str(auth_error):
                print("Access token expired - attempting to refresh using refresh token...")
                
                # Try to refresh the access token
                if refresh_token and app_key != 'your_new_app_key_here' and app_secret != 'your_new_app_secret_here':
                    new_access_token = refresh_access_token(refresh_token, app_key, app_secret)
                    
                    if new_access_token:
                        print("Creating new Dropbox client with refreshed access token...")
                        try:
                            # Create new client with refreshed token
                            new_dbx = dropbox.Dropbox(new_access_token)
                            # Test the new connection
                            account = new_dbx.users_get_current_account()
                            print(f"SUCCESS: Refreshed access token works - Connected as {account.name.display_name}")
                            
                            # Update environment variable with new token
                            update_env_variable('DROPBOX_ACCESS_TOKEN', new_access_token)
                            print("Updated DROPBOX_ACCESS_TOKEN environment variable")
                            
                            return new_dbx
                        except Exception as e:
                            print(f"Failed to create client with refreshed access token: {e}")
                    else:
                        print("Failed to refresh access token")
                else:
                    print("Cannot refresh access token - missing refresh token or app credentials")
                    print("Please run generate_refresh_token.py to get a refresh token")
            
            print("Authentication failed and could not recover")
            return None
            
        except Exception as e:
            print(f"Error testing Dropbox connection: {e}")
            return None
        
    except Exception as e:
        print(f"ERROR creating Dropbox client: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

def refresh_access_token(refresh_token, app_key, app_secret):
    """Refresh an expired access token using the refresh token"""
    try:
        print("=== Refreshing access token ===")
        print(f"Using refresh token: {refresh_token[:20]}...")
        print(f"Using app key: {app_key}")
        
        import requests
        
        # Make the token refresh request
        response = requests.post('https://api.dropboxapi.com/oauth2/token', data={
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': app_key,
            'client_secret': app_secret
        })
        
        print(f"Token refresh response status: {response.status_code}")
        
        if response.status_code == 200:
            token_data = response.json()
            new_access_token = token_data.get('access_token')
            
            if new_access_token:
                print(f"SUCCESS: New access token generated: {new_access_token[:10]}...")
                
                # Update the token file if it exists
                token_file = os.path.join(os.path.dirname(__file__), 'dropbox-token.txt')
                try:
                    with open(token_file, 'w') as f:
                        f.write(new_access_token)
                    print("Updated token file with new access token")
                except Exception as file_error:
                    print(f"Could not update token file: {file_error}")
                
                return new_access_token
            else:
                print("ERROR: No access token in response")
                print(f"Response data: {token_data}")
                return None
        else:
            print(f"Failed to refresh token: Status {response.status_code}")
            print(f"Response: {response.text}")
            
            # Parse error details if available
            try:
                error_data = response.json()
                if 'error_description' in error_data:
                    print(f"Error description: {error_data['error_description']}")
                if 'error' in error_data:
                    print(f"Error type: {error_data['error']}")
            except:
                pass
                
            return None
            
    except Exception as e:
        print(f"Error refreshing token: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return None

def get_dropbox_client_with_retry():
    """Get Dropbox client with automatic token refresh on expiration"""
    try:
        print("=== Getting Dropbox client with retry capability ===")
        
        # The main get_dropbox_client() function now handles all retry logic
        dbx = get_dropbox_client()
        
        if dbx:
            print("SUCCESS: Dropbox client obtained successfully")
            return dbx
        else:
            print("ERROR: Could not obtain Dropbox client after retry attempts")
            return None
            
    except Exception as e:
        print(f"Error in get_dropbox_client_with_retry: {e}")
        return None

def sync_dropbox_images():
    """Sync images from Dropbox to local images folder"""
    try:
        print("=== Starting Dropbox sync ===")
        
        # Check environment variables (only show key info, not full values)
        app_key = os.environ.get('APPKEY', 'your_new_app_key_here')
        app_secret = os.environ.get('APPSECRET', 'your_new_app_secret_here')
        access_token = os.environ.get('DROPBOX_ACCESS_TOKEN')
        
        print(f"App Key: {app_key[:10]}... (length: {len(app_key)})")
        print(f"App Secret: {app_secret[:10]}... (length: {len(app_secret)})")
        print(f"Access Token from env: {'YES' if access_token else 'NO'}")
        
        # Get Dropbox client with automatic token refresh
        dbx = get_dropbox_client_with_retry()
        if not dbx:
            print("ERROR: Failed to connect to Dropbox - no client returned")
            return False
        
        print("SUCCESS: Dropbox client created and authenticated")
        
        # Create local images directory if it doesn't exist
        os.makedirs(IMAGE_FOLDER, exist_ok=True)
        print(f"Local images folder: {IMAGE_FOLDER}")
        
        # Get list of existing local images
        existing_images = set()
        if os.path.exists(IMAGE_FOLDER):
            for f in os.listdir(IMAGE_FOLDER):
                if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS:
                    existing_images.add(f)
        
        print(f"Found {len(existing_images)} existing local images: {list(existing_images)[:5]}{'...' if len(existing_images) > 5 else ''}")
        
        # Check which Dropbox folder we're syncing
        folder_path = DROPBOX_FOLDER if DROPBOX_FOLDER else ''
        print(f"Checking Dropbox folder: '{folder_path}' {'(empty = root folder)' if not folder_path else ''}")
        
        # For Dropbox apps, we operate within the app folder automatically
        # List images directly from the app folder root
        try:
            print("=== Listing app folder root for images ===")
            result = dbx.files_list_folder('')
            dropbox_files = result.entries
            
            # Handle pagination
            while result.has_more:
                result = dbx.files_list_folder_continue(result.cursor)
                dropbox_files.extend(result.entries)
            
            print(f"Found {len(dropbox_files)} total files in app folder root")
            
            # Show some file names for debugging
            for file_entry in dropbox_files[:10]:  # Show first 10 files
                if hasattr(file_entry, 'name'):
                    print(f"App folder file: {file_entry.name}")
            
        except dropbox.exceptions.ApiError as e:
            print(f"ERROR: Failed to list Dropbox app folder: {e}")
            return False
        
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
                            # Download the file from app folder root
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
        
        # Only show detailed summary if there were changes or if verbose logging is needed
        if new_images_count > 0:
            print(f"=== Sync Summary ===")
            print(f"Total files in Dropbox: {len(dropbox_files)}")
            print(f"Image files in Dropbox: {image_files_count}")
            print(f"Existing local images: {len(existing_images)}")
            print(f"New images downloaded: {new_images_count}")
        else:
            print(f"Sync complete: {image_files_count} images in sync, no new downloads needed")
        
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
        
        # Get Dropbox client with automatic token refresh
        dbx = get_dropbox_client_with_retry()
        if not dbx:
            print("ERROR: Failed to connect to Dropbox - no client returned")
            return False
        
        # For Dropbox apps, we operate within the app folder automatically
        # Upload directly to the app folder root to avoid nested sfc30/sfc30 structure
        dropbox_path = f'/{filename}'
        print(f"Uploading to app folder root: {dropbox_path}")
        
        # Read file content and upload
        with open(file_path, 'rb') as f:
            file_content = f.read()
        
        print(f"Uploading file {filename} ({len(file_content)} bytes) to {dropbox_path}")
        
        # Guard clause: Try upload with token expiration handling
        try:
            # Upload file to Dropbox
            dbx.files_upload(
                file_content,
                dropbox_path,
                mode=dropbox.files.WriteMode.overwrite
            )
            
            print(f"SUCCESS: Uploaded {filename} to Dropbox app folder")
            return True
            
        except dropbox.exceptions.AuthError as auth_error:
            print(f"Authentication error during upload: {auth_error}")
            
            if 'expired_access_token' in str(auth_error):
                print("Token expired during upload - attempting to refresh and retry...")
                
                # Try to get a fresh client and retry
                fresh_dbx = get_dropbox_client_with_retry()
                if fresh_dbx:
                    try:
                        print("Retrying upload with refreshed token...")
                        fresh_dbx.files_upload(
                            file_content,
                            dropbox_path,
                            mode=dropbox.files.WriteMode.overwrite
                        )
                        print(f"SUCCESS: Uploaded {filename} to Dropbox after token refresh")
                        return True
                    except Exception as retry_error:
                        print(f"ERROR: Upload failed even after token refresh: {retry_error}")
                        return False
                else:
                    print("ERROR: Could not refresh token for retry")
                    return False
            else:
                print(f"Authentication error (not expired token): {auth_error}")
                return False
                
        except Exception as upload_error:
            print(f"ERROR: Upload failed with non-auth error: {upload_error}")
            return False
        
    except Exception as e:
        print(f"ERROR uploading {filename} to Dropbox: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False

def get_images():
    """Get list of image files from the images folder"""
    try:
        if not os.path.exists(IMAGE_FOLDER):
            print(f"Images folder does not exist: {IMAGE_FOLDER}")
            return []
        
        images = []
        for filename in os.listdir(IMAGE_FOLDER):
            if any(filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                # Return objects with filename and URL
                images.append({
                    'filename': filename,
                    'url': f"/images/{filename}",
                    'path': os.path.join(IMAGE_FOLDER, filename)
                })
        
        # Sort by modification time (newest first)
        images.sort(key=lambda x: os.path.getmtime(x['path']), reverse=True)
        
        print(f"Found {len(images)} images in {IMAGE_FOLDER}")
        return images
        
    except Exception as e:
        print(f"ERROR: Failed to get images: {e}")
        return []

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in UPLOAD_EXTENSIONS

LAST_SYNC_TIME = 0
SYNC_COOLDOWN = 300  # 5 minutes between syncs

@app.route('/')
def main():
    """Main page - just serve images without any Dropbox operations"""
    print("=== Loading main page (no Dropbox sync) ===")
    
    # Just get images from local folder - no Dropbox operations
    images = get_images()
    
    # Prepare data for template
    main_image = None
    carousel_images = []
    
    if images:
        # Extract first image for main display
        if isinstance(images[0], dict):
            main_image = images[0]
        else:
            # If it's a string, create object
            main_image = {
                'filename': images[0],
                'url': f"/images/{images[0]}"
            }
        
        # Extract remaining images for carousel
        carousel_images = images[1:] if len(images) > 1 else []
        
        # Ensure carousel images are in the right format
        formatted_carousel = []
        for img in carousel_images:
            if isinstance(img, dict):
                formatted_carousel.append(img)
            else:
                formatted_carousel.append({
                    'filename': img,
                    'url': f"/images/{img}"
                })
        carousel_images = formatted_carousel
    
    print(f"Serving {len(images)} images from local cache")
    return render_template('index.html', main_image=main_image, carousel_images=carousel_images)

@app.route('/images/<filename>')
def serve_image(filename):
    """Serve images from the images folder"""
    try:
        return send_from_directory(IMAGE_FOLDER, filename)
    except FileNotFoundError:
        # If image not found, try to sync and then serve
        print(f"Image not found: {filename}, attempting sync...")
        sync_dropbox_images()
        try:
            return send_from_directory(IMAGE_FOLDER, filename)
        except FileNotFoundError:
            # Return a placeholder or 404
            return jsonify({'error': 'Image not found'}), 404

@app.route('/<filename>')
def serve_image_root(filename):
    """Serve images from root path (for backward compatibility)"""
    # Check if it's an image file
    if any(filename.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
        return serve_image(filename)
    else:
        # Not an image, return 404
        return jsonify({'error': 'File not found'}), 404

@app.route('/api/images')
def api_images():
    """API endpoint to get images as JSON"""
    try:
        images = get_images()
        
        # Extract just the URLs for the frontend
        image_urls = []
        for image in images:
            if isinstance(image, dict) and 'url' in image:
                image_urls.append(image['url'])
            elif isinstance(image, str):
                # If it's already a string, assume it's the filename and create URL
                image_urls.append(f"/images/{image}")
            else:
                # Fallback - treat as filename
                image_urls.append(f"/images/{str(image)}")
        
        return jsonify({
            'images': image_urls,
            'count': len(image_urls)
        })
        
    except Exception as e:
        print(f"ERROR: Failed to get images via API: {e}")
        return jsonify({
            'images': [],
            'count': 0,
            'error': str(e)
        }), 500
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
            
            # Guard clause: Test Dropbox connection before upload
            print("=== Testing Dropbox connection before upload ===")
            test_dbx = get_dropbox_client_with_retry()
            
            if not test_dbx:
                print("ERROR: Could not establish Dropbox connection")
                flash('Photo uploaded to gallery, but Dropbox connection failed.')
                print(f"WARNING: Photo uploaded locally but Dropbox connection failed: {filename}")
                return redirect(url_for('main'))
            
            # Test the connection with a simple API call
            try:
                account = test_dbx.users_get_current_account()
                print(f"SUCCESS: Dropbox connection verified - Connected as {account.name.display_name}")
            except dropbox.exceptions.AuthError as auth_error:
                print(f"Authentication error during connection test: {auth_error}")
                if 'expired_access_token' in str(auth_error):
                    print("ERROR: Token expired and could not be refreshed")
                    flash('Photo uploaded to gallery, but Dropbox token expired. Please check your Dropbox configuration.')
                else:
                    flash('Photo uploaded to gallery, but Dropbox authentication failed.')
                print(f"WARNING: Photo uploaded locally but Dropbox auth failed: {filename}")
                return redirect(url_for('main'))
            except Exception as e:
                print(f"ERROR: Dropbox connection test failed: {e}")
                flash('Photo uploaded to gallery, but Dropbox connection test failed.')
                print(f"WARNING: Photo uploaded locally but Dropbox test failed: {filename}")
                return redirect(url_for('main'))
            
            # Upload to Dropbox (connection is verified)
            print("=== Proceeding with Dropbox upload ===")
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

@app.route('/generate-dropbox-token')
def token_generator_page():
    """Serve the token generator page"""
    return render_template('token_generator.html')

@app.route('/generate-tokens', methods=['POST'])
def generate_tokens():
    """Generate Dropbox tokens via web interface"""
    try:
        data = request.get_json()
        app_key = data.get('app_key')
        app_secret = data.get('app_secret')
        auth_code = data.get('auth_code')
        
        if not all([app_key, app_secret, auth_code]):
            return jsonify({'success': False, 'error': 'Missing required parameters'})
        
        # Create OAuth2 flow
        auth_flow = dropbox.DropboxOAuth2FlowNoRedirect(
            app_key, 
            app_secret,
            token_access_type='offline'  # This is key for getting refresh tokens
        )
        
        # Complete the OAuth flow
        oauth_result = auth_flow.finish(auth_code)
        
        # Test the refresh token
        try:
            test_dbx = dropbox.Dropbox(
                oauth2_refresh_token=oauth_result.refresh_token,
                app_key=app_key,
                app_secret=app_secret
            )
            account = test_dbx.users_get_current_account()
            user_name = account.name.display_name
            user_email = account.email
            
            print(f"SUCCESS: Generated tokens for {user_name} ({user_email})")
            
        except Exception as e:
            print(f"WARNING: Token validation failed: {e}")
            user_name = "Unknown"
            user_email = "Unknown"
        
        # Auto-update environment variables
        env_updated = False
        if update_env_variable('DROPBOX_ACCESS_TOKEN', oauth_result.access_token):
            env_updated = True
            print(f"SUCCESS: Auto-updated DROPBOX_ACCESS_TOKEN")
        
        if update_env_variable('DROPBOX_REFRESH_TOKEN', oauth_result.refresh_token):
            env_updated = True
            print(f"SUCCESS: Auto-updated DROPBOX_REFRESH_TOKEN")
        
        if update_env_variable('APPKEY', app_key):
            env_updated = True
            print(f"SUCCESS: Auto-updated APPKEY")
        
        if update_env_variable('APPSECRET', app_secret):
            env_updated = True
            print(f"SUCCESS: Auto-updated APPSECRET")

        return jsonify({
            'success': True,
            'access_token': oauth_result.access_token,
            'refresh_token': oauth_result.refresh_token,
            'account_id': oauth_result.account_id,
            'user_name': user_name,
            'user_email': user_email,
            'env_updated': env_updated
        })
        
    except Exception as e:
        print(f"ERROR: Token generation failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/test-dropbox-token', methods=['POST'])
def test_dropbox_token_endpoint():
    """Test a Dropbox token via web interface"""
    try:
        data = request.get_json()
        refresh_token = data.get('refresh_token')
        app_key = data.get('app_key')
        app_secret = data.get('app_secret')
        
        if not all([refresh_token, app_key, app_secret]):
            return jsonify({'success': False, 'error': 'Missing required parameters'})
        
        # Test the refresh token
        test_dbx = dropbox.Dropbox(
            oauth2_refresh_token=refresh_token,
            app_key=app_key,
            app_secret=app_secret
        )
        
        account = test_dbx.users_get_current_account()
        
        print(f"SUCCESS: Token test passed for {account.name.display_name}")
        
        return jsonify({
            'success': True,
            'user_name': account.name.display_name,
            'user_email': account.email,
            'account_id': account.account_id
        })
        
    except Exception as e:
        print(f"ERROR: Token test failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

def test_dropbox_token():
    """Test if the current Dropbox token is valid and working"""
    try:
        print("=== Testing Dropbox token validity ===")
        
        # Try to get a client
        dbx = get_dropbox_client_with_retry()
        if not dbx:
            print("ERROR: Could not create Dropbox client")
            return False
        
        # Test with a simple API call
        try:
            account = dbx.users_get_current_account()
            print(f"SUCCESS: Token is valid - Connected as {account.name.display_name}")
            return True
        except dropbox.exceptions.AuthError as auth_error:
            print(f"Authentication error: {auth_error}")
            if 'expired_access_token' in str(auth_error):
                print("Token has expired and could not be refreshed")
            return False
        except Exception as e:
            print(f"ERROR: API call failed: {e}")
            return False
            
    except Exception as e:
        print(f"ERROR: Token test failed: {e}")
        return False

@app.route('/update-access-token', methods=['POST'])
def update_access_token():
    """Update the access token from refresh token"""
    try:
        # Get new access token from refresh token
        new_access_token = get_current_access_token()
        
        if not new_access_token:
            return jsonify({
                'success': False, 
                'error': 'Failed to get new access token. Check your refresh token and app credentials.'
            })
            
        # Update the environment variable
        if update_env_variable('DROPBOX_ACCESS_TOKEN', new_access_token):
            return jsonify({
                'success': True,
                'access_token': new_access_token,
                'message': 'Access token updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to update access token environment variable'
            })
            
    except Exception as e:
        print(f"ERROR: Update access token failed: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/test-refresh-token')
def test_refresh_token():
    """Test endpoint to verify refresh token functionality"""
    try:
        refresh_token = os.environ.get('DROPBOX_REFRESH_TOKEN')
        app_key = os.environ.get('APPKEY')
        app_secret = os.environ.get('APPSECRET')
        
        if not all([refresh_token, app_key, app_secret]):
            return jsonify({
                'status': 'error',
                'message': 'Missing refresh token or app credentials',
                'refresh_token': 'YES' if refresh_token else 'NO',
                'app_key': 'YES' if app_key else 'NO',
                'app_secret': 'YES' if app_secret else 'NO'
            })
        
        # Test refresh token by getting a new access token
        new_access_token = refresh_access_token(refresh_token, app_key, app_secret)
        
        if new_access_token:
            # Test the new access token
            try:
                test_dbx = dropbox.Dropbox(new_access_token)
                account = test_dbx.users_get_current_account()
                
                return jsonify({
                    'status': 'success',
                    'message': 'Refresh token is working properly',
                    'user_name': account.name.display_name,
                    'user_email': account.email,
                    'new_token_preview': new_access_token[:20] + '...',
                    'refresh_token_preview': refresh_token[:20] + '...' if refresh_token else 'None'
                })
                
            except Exception as test_error:
                return jsonify({
                    'status': 'error',
                    'message': f'New access token test failed: {str(test_error)}',
                    'refresh_token_preview': refresh_token[:20] + '...' if refresh_token else 'None'
                })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Failed to refresh access token',
                'refresh_token_preview': refresh_token[:20] + '...' if refresh_token else 'None'
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Test failed: {str(e)}'
        })

@app.route('/health')
def health_check():
    """Simple health check endpoint that doesn't trigger sync"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time(),
        'images_available': len(get_images())
    })

@app.route('/ping')
def ping():
    """Simple ping endpoint for monitoring"""
    return 'pong'

@app.route('/debug-env')
def debug_env():
    """Debug endpoint to check environment variables (for development only)"""
    try:
        env_info = {}
        
        # Check each environment variable
        variables = ['APPKEY', 'APPSECRET', 'DROPBOX_ACCESS_TOKEN', 'DROPBOX_REFRESH_TOKEN']
        
        for var in variables:
            value = os.environ.get(var)
            if value:
                # Show only first 10 chars for security
                env_info[var] = {
                    'present': True,
                    'length': len(value),
                    'preview': value[:10] + '...' if len(value) > 10 else value
                }
            else:
                env_info[var] = {
                    'present': False,
                    'length': 0,
                    'preview': 'NOT SET'
                }
        
        return jsonify({
            'status': 'debug',
            'environment_variables': env_info,
            'python_version': sys.version,
            'platform': os.name
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/force-sync')
def force_sync():
    """Force sync with Dropbox regardless of cooldown"""
    global LAST_SYNC_TIME
    
    try:
        print("=== Manual sync triggered ===")
        success = sync_dropbox_images()
        if success:
            LAST_SYNC_TIME = time.time()
            return jsonify({'status': 'success', 'message': 'Manual sync completed successfully'})
        else:
            return jsonify({'status': 'error', 'message': 'Manual sync failed'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Manual sync error: {str(e)}'}), 500

@app.route('/sync')
def sync_page():
    """Dedicated sync page for Dropbox operations"""
    return render_template('sync.html')

@app.route('/sync-status')
def sync_status():
    """Get current sync status and statistics"""
    try:
        # Check Dropbox connection without syncing
        dbx = get_dropbox_client_with_retry()
        dropbox_connected = dbx is not None
        
        if dropbox_connected:
            try:
                account = dbx.users_get_current_account()
                user_info = {
                    'name': account.name.display_name,
                    'email': account.email
                }
            except:
                user_info = None
        else:
            user_info = None
        
        # Get local image count
        local_images = get_images()
        
        # Get last sync time
        global LAST_SYNC_TIME
        time_since_last_sync = int(time.time() - LAST_SYNC_TIME) if LAST_SYNC_TIME > 0 else None
        
        return jsonify({
            'status': 'success',
            'dropbox_connected': dropbox_connected,
            'user_info': user_info,
            'local_images_count': len(local_images),
            'last_sync_seconds_ago': time_since_last_sync,
            'sync_cooldown_seconds': SYNC_COOLDOWN,
            'can_sync_now': time_since_last_sync is None or time_since_last_sync > SYNC_COOLDOWN
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        })

@app.route('/sync-dropbox-manual', methods=['POST'])
def sync_dropbox_manual():
    """Manual Dropbox sync with detailed progress"""
    global LAST_SYNC_TIME
    
    try:
        print("=== Manual Dropbox sync started ===")
        
        # Check if we can sync (respect cooldown for manual syncs too, but allow override)
        current_time = time.time()
        time_since_last = current_time - LAST_SYNC_TIME if LAST_SYNC_TIME > 0 else SYNC_COOLDOWN + 1
        
        force_sync = request.json.get('force', False) if request.is_json else False
        
        if time_since_last < SYNC_COOLDOWN and not force_sync:
            return jsonify({
                'status': 'cooldown',
                'message': f'Sync on cooldown. Wait {int(SYNC_COOLDOWN - time_since_last)} more seconds or use force=true',
                'seconds_remaining': int(SYNC_COOLDOWN - time_since_last)
            })
        
        # Perform the sync
        success = sync_dropbox_images()
        
        if success:
            LAST_SYNC_TIME = current_time
            # Get updated image count
            images = get_images()
            return jsonify({
                'status': 'success',
                'message': 'Dropbox sync completed successfully',
                'images_count': len(images),
                'sync_time': current_time
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Dropbox sync failed'
            }), 500
            
    except Exception as e:
        print(f"ERROR: Manual sync failed: {e}")
        return jsonify({
            'status': 'error',
            'message': f'Sync error: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)