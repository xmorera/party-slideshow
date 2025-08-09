from flask import Flask, jsonify, render_template, send_from_directory, request, redirect, url_for, flash, abort
import os
from werkzeug.utils import secure_filename
import uuid
import dropbox
import time
import sys
import logging
from threading import Lock

# Optional .env loading
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY","change-me")

BASE_DIR = os.path.dirname(__file__)
IMAGE_FOLDER = os.path.join(BASE_DIR, 'images')
MEDIA_FOLDER = os.path.join(BASE_DIR, 'media')
os.makedirs(IMAGE_FOLDER, exist_ok=True)
os.makedirs(MEDIA_FOLDER, exist_ok=True)

# Extensions (with dot for scan, without dot for upload validation)
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
UPLOAD_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

# ------------ Caching for image list ------------
_IMAGE_CACHE = {
    "items": [],
    "last_scan": 0.0,
    "fingerprint": 0.0
}
_CACHE_LOCK = Lock()
SCAN_MIN_INTERVAL = 1.0  # seconds

def log_info(msg):
    logging.info(msg)
    print(msg)

def log_error(msg):
    logging.error(msg)
    print(msg)

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')

def _scan_images():
    items = []
    max_mtime = 0.0
    if not os.path.isdir(IMAGE_FOLDER):
        return [], 0.0
    try:
        with os.scandir(IMAGE_FOLDER) as it:
            for entry in it:
                if not entry.is_file():
                    continue
                name_lower = entry.name.lower()
                if not any(name_lower.endswith(ext) for ext in ALLOWED_EXTENSIONS):
                    continue
                try:
                    stat = entry.stat()
                    mtime = stat.st_mtime
                    max_mtime = max(max_mtime, mtime)
                    items.append({
                        'filename': entry.name,
                        'url': f"/images/{entry.name}",
                        'path': entry.path,
                        'mtime': mtime
                    })
                except FileNotFoundError:
                    continue
        items.sort(key=lambda x: x['mtime'], reverse=True)
        return items, max_mtime
    except Exception as e:
        log_error(f"Image scan error: {e}")
        return [], 0.0

def get_images(force=False):
    """
    Return cached list of image metadata.
    force=True forces a directory rescan.
    """
    now = time.time()
    with _CACHE_LOCK:
        if not force and (now - _IMAGE_CACHE['last_scan'] < SCAN_MIN_INTERVAL):
            return _IMAGE_CACHE['items']
        items, fp = _scan_images()
        if force or fp != _IMAGE_CACHE['fingerprint']:
            _IMAGE_CACHE['items'] = items
            _IMAGE_CACHE['fingerprint'] = fp
        _IMAGE_CACHE['last_scan'] = now
        return _IMAGE_CACHE['items']

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in UPLOAD_EXTENSIONS

# ------------ Dropbox (optional) ------------
def update_env_variable(key, value):
    try:
        os.environ[key] = value
        env_file_path = os.path.join(os.path.dirname(__file__), '.env')
        existing = {}
        if os.path.exists(env_file_path):
            with open(env_file_path,'r') as f:
                for line in f:
                    line=line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k,v=line.split('=',1)
                        existing[k]=v
        existing[key]=value
        with open(env_file_path,'w') as f:
            for k,v in existing.items():
                f.write(f"{k}={v}\n")
        return True
    except Exception as e:
        print(f"ENV update failed: {e}")
        return False

def refresh_access_token(refresh_token, app_key, app_secret):
    import requests
    try:
        resp=requests.post('https://api.dropboxapi.com/oauth2/token',data={
            'grant_type':'refresh_token',
            'refresh_token':refresh_token,
            'client_id':app_key,
            'client_secret':app_secret
        })
        if resp.status_code==200:
            data=resp.json()
            new_token=data.get('access_token')
            if new_token:
                token_file=os.path.join(os.path.dirname(__file__),'dropbox-token.txt')
                try:
                    with open(token_file,'w') as f: f.write(new_token)
                except: pass
                return new_token
        return None
    except Exception:
        return None

def get_dropbox_client():
    try:
        refresh_token=os.environ.get('DROPBOX_REFRESH_TOKEN')
        app_key=os.environ.get('APPKEY')
        app_secret=os.environ.get('APPSECRET')
        access_token=os.environ.get('DROPBOX_ACCESS_TOKEN')

        if refresh_token and app_key and app_secret:
            try:
                dbx=dropbox.Dropbox(
                    oauth2_refresh_token=refresh_token,
                    app_key=app_key,
                    app_secret=app_secret
                )
                account=dbx.users_get_current_account()
                if dbx._oauth2_access_token:
                    update_env_variable('DROPBOX_ACCESS_TOKEN', dbx._oauth2_access_token)
                print(f"Dropbox OK (refresh token): {account.name.display_name}")
                return dbx
            except Exception as e:
                print(f"Refresh token auth failed: {e}")

        if not access_token:
            token_file=os.path.join(os.path.dirname(__file__),'dropbox-token.txt')
            if os.path.exists(token_file):
                with open(token_file,'r') as f: access_token=f.read().strip()
        if not access_token:
            print("No Dropbox credentials.")
            return None
        dbx=dropbox.Dropbox(access_token)
        dbx.users_get_current_account()
        return dbx
    except Exception as e:
        print(f"Dropbox client error: {e}")
        return None

def get_dropbox_client_with_retry():
    dbx=get_dropbox_client()
    return dbx

def sync_dropbox_images():
    """
    Download new images from Dropbox root (App Folder) into IMAGE_FOLDER.
    """
    try:
        dbx=get_dropbox_client_with_retry()
        if not dbx:
            return False
        existing=set(f for f in os.listdir(IMAGE_FOLDER) if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS)
        try:
            result=dbx.files_list_folder('')
        except Exception as e:
            print(f"Dropbox list error: {e}")
            return False
        entries=result.entries
        while result.has_more:
            result=dbx.files_list_folder_continue(result.cursor)
            entries.extend(result.entries)
        new_count=0
        for ent in entries:
            if hasattr(ent,'name'):
                name=ent.name
                ext=os.path.splitext(name)[1].lower()
                if ext in ALLOWED_EXTENSIONS and name not in existing:
                    try:
                        _,resp=dbx.files_download('/'+name)
                        local_path=os.path.join(IMAGE_FOLDER,name)
                        with open(local_path,'wb') as f: f.write(resp.content)
                        current=time.time()
                        os.utime(local_path,(current,current))
                        new_count+=1
                    except Exception as e:
                        print(f"Download failed {name}: {e}")
        if new_count>0:
            get_images(force=True)
        return True
    except Exception as e:
        print(f"Sync error: {e}")
        return False

# ------------ App Routes ------------
@app.route('/')
def main():
    images=get_images()
    main_image=images[0] if images else None
    carousel_images=images[1:] if len(images)>1 else []
    return render_template('index.html', main_image=main_image, carousel_images=carousel_images)

@app.route('/all')
def all_photos():
    return render_template('all.html')

@app.route('/images/<filename>')
def serve_image(filename):
    try:
        return send_from_directory(IMAGE_FOLDER, filename)
    except:
        abort(404)

@app.route('/<filename>')
def serve_image_root(filename):
    if any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
        return serve_image(filename)
    return jsonify({'error':'File not found'}),404

@app.route('/api/images')
def api_images():
    imgs=get_images()
    return jsonify({
        'status':'success',
        'images':[i['url'] for i in imgs],
        'count':len(imgs)
    })

@app.route('/media/<filename>')
def serve_media(filename):
    return send_from_directory(MEDIA_FOLDER, filename)

@app.route('/list-images')
def list_images():
    return '<br>'.join(i['filename'] for i in get_images())

def get_unique_filename(filepath, original_size):
    if not os.path.exists(filepath):
        return filepath
    existing_size=os.path.getsize(filepath)
    if existing_size == original_size:
        return None
    directory=os.path.dirname(filepath)
    name,ext=os.path.splitext(os.path.basename(filepath))
    counter=1
    while counter<=100:
        new_name=f"{name} ({counter}){ext}"
        new_path=os.path.join(directory,new_name)
        if not os.path.exists(new_path):
            return new_path
        if os.path.getsize(new_path)==original_size:
            return None
        counter+=1
    return None

@app.route('/upload', methods=['GET','POST'])
def upload():
    """
    Single or multiple file upload.
    Single input name='file'
    Multiple input name='files[]'
    """
    if request.method=='POST':
        files=[]
        if 'files[]' in request.files:
            files.extend([f for f in request.files.getlist('files[]') if f and f.filename])
        if 'file' in request.files:
            f=request.files['file']
            if f and f.filename:
                files.append(f)
        if not files:
            flash('No file selected')
            return redirect(request.url)

        uploaded_count=0
        ignored_count=0
        error_count=0
        uploaded_files=[]

        for file in files:
            if not allowed_file(file.filename):
                error_count+=1
                continue
            try:
                safe=secure_filename(file.filename)
                temp_path=os.path.join(IMAGE_FOLDER, f"temp_{uuid.uuid4().hex}_{safe}")
                file.save(temp_path)
                size=os.path.getsize(temp_path)
                final_path=os.path.join(IMAGE_FOLDER, safe)
                unique_path=get_unique_filename(final_path, size)
                if unique_path is None:
                    os.remove(temp_path)
                    ignored_count+=1
                    continue
                if temp_path != unique_path:
                    os.rename(temp_path, unique_path)
                uploaded_files.append(os.path.basename(unique_path))
                uploaded_count+=1
            except Exception as e:
                error_count+=1
                try:
                    if os.path.exists(temp_path): os.remove(temp_path)
                except: pass
                print(f"Upload error {file.filename}: {e}")

        if uploaded_count:
            flash(f"✅ Uploaded {uploaded_count} photo{'s' if uploaded_count!=1 else ''}")
            if len(uploaded_files)<=5:
                flash("Files: "+", ".join(uploaded_files))
        if ignored_count:
            flash(f"📋 Ignored {ignored_count} duplicate photo{'s' if ignored_count!=1 else ''}")
        if error_count:
            flash(f"❌ Failed {error_count} file{'s' if error_count!=1 else ''}")

        if uploaded_count:
            get_images(force=True)
            try:
                if sync_dropbox_images():
                    flash("🔄 Synced to Dropbox")
                else:
                    flash("⚠️ Dropbox sync failed")
            except Exception as e:
                flash(f"⚠️ Sync error: {e}")

        return redirect(url_for('upload'))

    images=get_images()
    return render_template('upload.html', images=images)

# Simple health endpoints
@app.route('/health')
def health():
    return jsonify({'status':'ok','count':len(get_images())})

@app.route('/ping')
def ping():
    return 'pong'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)), debug=True)