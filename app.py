from flask import Flask, jsonify, render_template, send_from_directory, request, redirect, url_for, flash, abort
import os, uuid, dropbox, time, logging
from werkzeug.utils import secure_filename
from threading import Lock

# Optional .env
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

# Extensions
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
UPLOAD_EXTENSIONS = {'jpg','jpeg','png','gif','webp'}

# Caching
_IMAGE_CACHE = {"items":[], "last_scan":0.0, "fingerprint":0.0}
_CACHE_LOCK = Lock()
SCAN_MIN_INTERVAL = 1.0

# Sync state
LAST_SYNC_TIME = None
SYNC_COOLDOWN_SECONDS = 300  # 5 minutes
DROPBOX_FOLDER = os.environ.get("DROPBOX_FOLDER","").strip()  # empty = root of app folder

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(message)s')
log = logging.getLogger("app")

def _scan_images():
    items = []
    max_mtime = 0.0
    if not os.path.isdir(IMAGE_FOLDER):
        return [], 0.0
    try:
        with os.scandir(IMAGE_FOLDER) as it:
            for e in it:
                if not e.is_file(): continue
                name_lower = e.name.lower()
                if not any(name_lower.endswith(ext) for ext in ALLOWED_EXTENSIONS):
                    continue
                try:
                    st = e.stat()
                    mtime = st.st_mtime
                    max_mtime = max(max_mtime, mtime)
                    items.append({
                        "filename": e.name,
                        "url": f"/images/{e.name}",
                        "path": e.path,
                        "mtime": mtime
                    })
                except FileNotFoundError:
                    continue
        items.sort(key=lambda x: x["mtime"], reverse=True)
        return items, max_mtime
    except Exception as ex:
        log.error(f"Scan error: {ex}")
        return [], 0.0

def get_images(force=False):
    now = time.time()
    with _CACHE_LOCK:
        if not force and (now - _IMAGE_CACHE["last_scan"] < SCAN_MIN_INTERVAL):
            return _IMAGE_CACHE["items"]
        items, fp = _scan_images()
        if force or fp != _IMAGE_CACHE["fingerprint"]:
            _IMAGE_CACHE["items"] = items
            _IMAGE_CACHE["fingerprint"] = fp
        _IMAGE_CACHE["last_scan"] = now
        return _IMAGE_CACHE["items"]

def allowed_file(filename:str):
    return '.' in filename and filename.rsplit('.',1)[1].lower() in UPLOAD_EXTENSIONS

# Dropbox helpers
def update_env_variable(key, value):
    try:
        os.environ[key]=value
        env_path=os.path.join(BASE_DIR,'.env')
        existing={}
        if os.path.exists(env_path):
            with open(env_path,'r') as f:
                for line in f:
                    line=line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k,v=line.split('=',1)
                        existing[k]=v
        existing[key]=value
        with open(env_path,'w') as f:
            for k,v in existing.items():
                f.write(f"{k}={v}\n")
        return True
    except Exception as e:
        log.warning(f"Env write failed: {e}")
        return False

def get_dropbox_client():
    try:
        refresh_token=os.environ.get('DROPBOX_REFRESH_TOKEN')
        app_key=os.environ.get('APPKEY')
        app_secret=os.environ.get('APPSECRET')
        access_token=os.environ.get('DROPBOX_ACCESS_TOKEN')

        # OAuth2 refresh token flow
        if refresh_token and app_key and app_secret:
            try:
                dbx=dropbox.Dropbox(oauth2_refresh_token=refresh_token, app_key=app_key, app_secret=app_secret)
                account=dbx.users_get_current_account()
                if dbx._oauth2_access_token:
                    update_env_variable('DROPBOX_ACCESS_TOKEN', dbx._oauth2_access_token)
                log.info(f"Dropbox connected (refresh token) as {account.name.display_name}")
                return dbx
            except Exception as e:
                log.warning(f"Refresh token auth failed: {e}")

        # Legacy token
        if not access_token:
            tok_file=os.path.join(BASE_DIR,'dropbox-token.txt')
            if os.path.exists(tok_file):
                with open(tok_file,'r') as f:
                    access_token=f.read().strip()

        if not access_token:
            return None

        dbx=dropbox.Dropbox(access_token)
        dbx.users_get_current_account()
        return dbx
    except Exception as e:
        log.error(f"Dropbox client error: {e}")
        return None

def sync_dropbox_images(target_folder: str = ""):
    """
    Download new images from Dropbox (App Folder scope).
    target_folder: subfolder path ('' = root)
    """
    try:
        dbx=get_dropbox_client()
        if not dbx:
            return False, "No Dropbox credentials"

        folder = target_folder.strip()
        if folder.startswith('/'):
            folder = folder[1:]
        list_path = f"/{folder}" if folder else ""

        try:
            result=dbx.files_list_folder(list_path)
        except dropbox.exceptions.ApiError as e:
            return False, f"List error: {e}"

        entries=result.entries
        while result.has_more:
            result=dbx.files_list_folder_continue(result.cursor)
            entries.extend(result.entries)

        existing=set(os.listdir(IMAGE_FOLDER))
        new_count=0

        for ent in entries:
            # Only FileMetadata
            if isinstance(ent, dropbox.files.FileMetadata):
                name=ent.name
                ext=os.path.splitext(name)[1].lower()
                if ext in ALLOWED_EXTENSIONS and name not in existing:
                    try:
                        _,resp=dbx.files_download(ent.path_lower)
                        local_path=os.path.join(IMAGE_FOLDER,name)
                        with open(local_path,'wb') as f:
                            f.write(resp.content)
                        now=time.time()
                        os.utime(local_path,(now,now))
                        new_count+=1
                    except Exception as e:
                        log.warning(f"Download failed {name}: {e}")

        if new_count>0:
            get_images(force=True)
        return True, f"Downloaded {new_count} new files"
    except Exception as e:
        return False, f"Sync error: {e}"

# Utility
def get_unique_filename(filepath, original_size):
    if not os.path.exists(filepath):
        return filepath
    if os.path.getsize(filepath) == original_size:
        return None
    directory=os.path.dirname(filepath)
    name,ext=os.path.splitext(os.path.basename(filepath))
    counter=1
    while counter<=100:
        cand=os.path.join(directory,f"{name} ({counter}){ext}")
        if not os.path.exists(cand):
            return cand
        if os.path.getsize(cand)==original_size:
            return None
        counter+=1
    return None

# Routes
@app.route('/')
def main():
    images=get_images()
    main_image=images[0] if images else None
    carousel_images=images[1:] if len(images)>1 else []
    return render_template('index.html', main_image=main_image, carousel_images=carousel_images)

@app.route('/all')
def all_photos():
    return render_template('all.html')

@app.route('/sync')
def sync_page():
    return render_template('sync.html')

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
    return jsonify({'status':'success','images':[i['url'] for i in imgs],'count':len(imgs)})

@app.route('/media/<filename>')
def serve_media(filename):
    return send_from_directory(MEDIA_FOLDER, filename)

@app.route('/list-images')
def list_images():
    return '<br>'.join(i['filename'] for i in get_images())

@app.route('/upload', methods=['GET','POST'])
def upload():
    if request.method=='POST':
        files=[]
        if 'files[]' in request.files:
            files.extend([f for f in request.files.getlist('files[]') if f and f.filename])
        if 'file' in request.files:
            sf=request.files['file']
            if sf and sf.filename:
                files.append(sf)

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
                tmp=os.path.join(IMAGE_FOLDER,f"temp_{uuid.uuid4().hex}_{safe}")
                file.save(tmp)
                size=os.path.getsize(tmp)
                dest=os.path.join(IMAGE_FOLDER,safe)
                unique=get_unique_filename(dest,size)
                if unique is None:
                    os.remove(tmp)
                    ignored_count+=1
                    continue
                if tmp!=unique:
                    os.rename(tmp,unique)
                uploaded_files.append(os.path.basename(unique))
                uploaded_count+=1
            except Exception as e:
                error_count+=1
                try:
                    if os.path.exists(tmp): os.remove(tmp)
                except: pass
                log.warning(f"Upload error {file.filename}: {e}")

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
            ok,msg=sync_dropbox_images(DROPBOX_FOLDER)
            if ok: flash("🔄 Synced to Dropbox")
            else: flash(f"⚠️ Dropbox sync failed: {msg}")

        return redirect(url_for('upload'))

    images=get_images()
    return render_template('upload.html', images=images)

# --- Sync API used by sync.html ---

def _dropbox_basic_status():
    dbx=get_dropbox_client()
    if not dbx:
        return False, None
    try:
        acc=dbx.users_get_current_account()
        return True, {"name":acc.name.display_name, "email":acc.email}
    except Exception as e:
        log.warning(f"Account info error: {e}")
        return False, None

@app.route('/sync-status')
def sync_status():
    global LAST_SYNC_TIME
    connected, user_info = _dropbox_basic_status()
    imgs=get_images()
    now=time.time()
    last_sync_seconds_ago = None
    if LAST_SYNC_TIME:
        last_sync_seconds_ago = int(now - LAST_SYNC_TIME)
    can_sync_now = True
    if last_sync_seconds_ago is not None and last_sync_seconds_ago < SYNC_COOLDOWN_SECONDS:
        can_sync_now = False
    return jsonify({
        "status":"success",
        "dropbox_connected":connected,
        "user_info":user_info,
        "local_images_count":len(imgs),
        "last_sync_seconds_ago":last_sync_seconds_ago,
        "sync_cooldown_seconds":SYNC_COOLDOWN_SECONDS,
        "can_sync_now":can_sync_now
    })

@app.route('/sync-dropbox-manual', methods=['POST'])
def sync_dropbox_manual():
    global LAST_SYNC_TIME
    payload=request.get_json(silent=True) or {}
    force=bool(payload.get("force"))
    now=time.time()
    last_ago = None if LAST_SYNC_TIME is None else now - LAST_SYNC_TIME
    if not force and LAST_SYNC_TIME and last_ago < SYNC_COOLDOWN_SECONDS:
        remaining=int(SYNC_COOLDOWN_SECONDS - last_ago)
        return jsonify({"status":"cooldown","message":f"Cooldown active ({remaining}s remaining)"})
    ok,msg=sync_dropbox_images(DROPBOX_FOLDER)
    if ok:
        LAST_SYNC_TIME=time.time()
        imgs=get_images()
        return jsonify({"status":"success","message":msg,"images_count":len(imgs)})
    return jsonify({"status":"error","message":msg}),500

@app.route('/generate-dropbox-token')
def generate_dropbox_token_page():
    return "<h1>Provide Dropbox credentials via environment variables (refresh token flow).</h1>"

# Health
@app.route('/health')
def health():
    return jsonify({"status":"ok","count":len(get_images())})

@app.route('/ping')
def ping():
    return "pong"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',5000)), debug=True)