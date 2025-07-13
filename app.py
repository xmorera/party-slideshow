from flask import Flask, jsonify
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
    return '<br>'.join(images)

@app.route('/list-images')
def list_images():
    images = get_images()
    return '<br>'.join(images)
