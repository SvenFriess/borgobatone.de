from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import logging
import time
import requests

# Flask-App initialisieren
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Startseite (index.html liefern)
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

# API-Endpunkt für Chatbot-Fragen
@app.route('/api/generate', methods=['POST'])
def generate():
    user_input = request.json.get("user_input", "")
    print(f"📨 Eingabe: {user_input}")

    try:
        # Kontext laden
        with open('/Users/svenfriess/Desktop/borgobatone.de/borgobatone.txt', 'r', encoding='utf-8') as f:
            kontext = f.read().strip()

        # Prompt zusammensetzen
        prompt = kontext + "\n\nFrage: " + user_input
        print("📤 Prompt an Modell:\n", prompt[:1000])
        start = time.time()

        # Anfrage an Ollama
        ollama_payload = {
            "model": "mistral:instruct",
            "prompt": prompt,
            "stream": False
        }

        response = requests.post("http://localhost:11434/api/generate", json=ollama_payload, timeout=60)
        print("🔍 Antwort von Ollama:", response.text)

        response.raise_for_status()
        output = response.json()

        antwort = output.get("response", "⚠️ Keine Antwort erhalten.")
        dauer = round(time.time() - start, 2)
        print(f"⏱️ Antwortdauer: {dauer}s")
        return jsonify({"response": antwort})

    except Exception as e:
        print("❗Fehler beim Generieren der Antwort:", str(e))
        return jsonify({"response": f"Fehler: {str(e)}"}), 500

# Server starten
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5200, debug=True)