from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import logging
import time
import requests

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/api/generate', methods=['POST'])
def generate():
    user_input = request.json.get("user_input", "")
    print(f"📨 Eingabe: {user_input}")
    start = time.time()

    try:
        # Anfrage an das lokale Ollama-Modell
        ollama_payload = {
          "model": "gemma:2b",
          "prompt": user_input,
          "stream": False
}

        response = requests.post("http://localhost:11434/api/generate", json=ollama_payload, timeout=20)
        
        response.raise_for_status()
        output = response.json()

        antwort = output.get("response", "⚠️ Keine Antwort erhalten.")
        dauer = round(time.time() - start, 2)
        print(f"⏱️ Antwortdauer: {dauer}s")
        return jsonify({"response": antwort})

    except Exception as e:
        print("❌ Fehler:", str(e))
        return jsonify({"response": "⚠️ Fehler bei der Kommunikation mit dem Modell."})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5200, debug=True)