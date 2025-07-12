from flask import Flask

app = Flask(__name__)

@app.route('/')
def hello():
    return 'Hello, world! This is your Render Flask app.'
