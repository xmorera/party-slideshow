from flask import Flask, jsonify, render_template, send_from_directory, request, redirect, url_for, flash
import os
import random
from werkzeug.utils import secure_filename
import uuid
from datetime import datetime
import dropbox
import time

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a random secret key
IMAGE_FOLDER = os.path.join(os.path.dirname(__file__), 'images')
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
UPLOAD_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

# Dropbox configuration
DROPBOX_APP_KEY = 'hf4h0oogfmfd9xb'
DROPBOX_APP_SECRET = 'aiin4334ivtyz77'
DROPBOX_FOLDER = '/party-slideshow'

def get_dropbox_client():
    """Get authenticated Dropbox client"""
    try:
        # Read access token from environment or file
        # You'll need to get this token through OAuth flow first
        access_token = os.environ.get('DROPBOX_ACCESS_TOKEN')
        
        if not access_token:
            # Try to read from a token file
            token_file = os.path.join(os.path.dirname(__file__), 'dropbox-token.txt')
            if os.path.exists(token_file):
                with open(token_file, 'r') as f:
                    access_token = f.read().strip()
        
        if not access_token:
            print("No Dropbox access token found. Please set DROPBOX_ACCESS_TOKEN environment variable or create dropbox-token.txt file.")
            return None
            
        dbx = dropbox.Dropbox(access_token)
        return dbx
    except Exception as e:
        print(f"Error creating Dropbox client: {e}")
        return None

def sync_dropbox_images():
    """Sync images from Dropbox to local images folder"""
    try:
        # Get Dropbox client
        dbx = get_dropbox_client()
        if not dbx:
            print("Failed to connect to Dropbox")
            return False
        
        # Create local images directory if it doesn't exist
        os.makedirs(IMAGE_FOLDER, exist_ok=True)
        
        # Get list of existing local images
        existing_images = set()
        if os.path.exists(IMAGE_FOLDER):
            for f in os.listdir(IMAGE_FOLDER):
                if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS:
                    existing_images.add(f)
        
        # Get list of images from Dropbox
        try:
            result = dbx.files_list_folder(DROPBOX_FOLDER)
            dropbox_files = result.entries
            
            # Handle pagination if there are many files
            while result.has_more:
                result = dbx.files_list_folder_continue(result.cursor)
                dropbox_files.extend(result.entries)
                
        except dropbox.exceptions.ApiError as e:
            print(f"Error listing Dropbox folder: {e}")
            return False
        
        # Filter for image files and check for new ones
        new_images_count = 0
        for file_entry in dropbox_files:
            if hasattr(file_entry, 'name'):
                filename = file_entry.name
                file_ext = os.path.splitext(filename)[1].lower()
                
                # Check if it's an image file and not already local
                if file_ext in ALLOWED_EXTENSIONS and filename not in existing_images:
                    try:
                        # Download the file
                        dropbox_path = f"{DROPBOX_FOLDER}/{filename}"
                        local_path = os.path.join(IMAGE_FOLDER, filename)
                        
                        print(f"Downloading new image: {filename}")
                        
                        # Download file from Dropbox
                        metadata, response = dbx.files_download(dropbox_path)
                        
                        # Save to local file
                        with open(local_path, 'wb') as f:
                            f.write(response.content)
                        
                        # Set modified time to current time for proper sorting
                        current_time = time.time()
                        os.utime(local_path, (current_time, current_time))
                        
                        new_images_count += 1
                        print(f"Successfully downloaded: {filename}")
                        
                    except Exception as e:
                        print(f"Error downloading {filename}: {e}")
                        continue
        
        print(f"Dropbox sync completed. Downloaded {new_images_count} new images.")
        return True
        
    except Exception as e:
        print(f"Error in Dropbox sync: {e}")
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
            file.save(filepath)
            flash('Photo uploaded successfully!')
            return redirect(url_for('main'))
        except Exception as e:
            flash(f'Error uploading photo: {str(e)}')
            return redirect(request.url)
    else:
        flash('Invalid file type. Please upload JPG, PNG, GIF, or WebP images.')
        return redirect(request.url)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
