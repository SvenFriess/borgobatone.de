from flask import Flask, send_from_directory, abort, redirect
import os
import socket

app = Flask(__name__)

SIGNALBOT_DIR = "/Users/svenfriess/Projekte/borgobatone.de/signalbot"
WEBBOT_DIR = "/Users/svenfriess/Projekte/borgobatone.de/webbot"

# Root leitet sofort auf /signalbot/ um
@app.route("/")
def root_redirect():
    return redirect("/signalbot/")

# Signalbot
@app.route("/signalbot/")
def serve_signalbot_index():
    index_path = os.path.join(SIGNALBOT_DIR, "index.html")
    if not os.path.exists(index_path):
        abort(404)
    return send_from_directory(SIGNALBOT_DIR, "index.html")

@app.route("/signalbot/<path:filename>")
def serve_signalbot_assets(filename):
    file_path = os.path.join(SIGNALBOT_DIR, filename)
    if not os.path.exists(file_path):
        abort(404)
    return send_from_directory(SIGNALBOT_DIR, filename)

# Webbot (bleibt erreichbar)
@app.route("/webbot/")
def serve_webbot_index():
    index_path = os.path.join(WEBBOT_DIR, "index.html")
    if not os.path.exists(index_path):
        abort(404)
    return send_from_directory(WEBBOT_DIR, "index.html")

@app.route("/webbot/<path:filename>")
def serve_webbot_assets(filename):
    file_path = os.path.join(WEBBOT_DIR, filename)
    if not os.path.exists(file_path):
        abort(404)
    return send_from_directory(WEBBOT_DIR, filename)

def find_free_port(preferred_port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("0.0.0.0", preferred_port))
            return preferred_port
        except OSError:
            return 5050

if __name__ == "__main__":
    port = find_free_port(5000)
    print(f"🚀 Server startet auf Port {port}")
    app.run(host="0.0.0.0", port=port, debug=True)