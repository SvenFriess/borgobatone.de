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
    with open('/Users/svenfriess/Desktop/borgobatone.de/borgobatone.txt', 'r', encoding='utf-8') as f:
        kontext = f.read().strip()


    # Prompt erstellen
    prompt = kontext + "\n\nFrage: " + user_input
    print("📤 Prompt an Modell:\n", prompt[:1000])  # Zeigt die ersten 1000 Zeichen
    start = time.time()

    try:
        # 📄 Kontextdatei lesen
        with open('/Users/svenfriess/Desktop/borgobatone.de/borgobatone.txt', 'r', encoding='utf-8') as f:
            kontext = f.read().strip()

        # 📦 Kombinierten Prompt erstellen
        full_prompt = f"{kontext}\n\nFrage: {user_input}"

        # 🔁 Anfrage an das Ollama-Modell
        ollama_payload = {
            "model": "gemma:2b",
            "prompt": full_prompt,
            "stream": False
        }

        response = requests.post("http://localhost:11434/api/generate", json=ollama_payload, timeout=20)
        print("🔍 Antwort von Ollama:", response.text)

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