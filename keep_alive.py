from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    # Runs the web server on port 8080
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    # Creates a separate thread so it doesn't block the bot
    t = Thread(target=run)
    t.start()