from flask import Flask, jsonify, render_template, send_from_directory
import os
import random

app = Flask(__name__)
IMAGE_FOLDER = os.path.join(os.path.dirname(__file__), 'images')
ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

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

@app.route('/')
def main():
    images = get_images()
    if not images:
        return render_template('index.html', main_image=None, carousel_images=[])
    
    main_image = images[0]
    carousel_images = images[1:] if len(images) > 1 else []
    
    return render_template('index.html', main_image=main_image, carousel_images=carousel_images)

@app.route('/images/<filename>')
def serve_image(filename):
    return send_from_directory(IMAGE_FOLDER, filename)

@app.route('/list-images')
def list_images():
    images = get_images()
    return '<br>'.join(images)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
