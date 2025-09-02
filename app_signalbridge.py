from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# Wo läuft dein Ollama-Server?
OLLAMA_URL = "http://localhost:11434/api/generate"

def ask_ollama(prompt, model="mistral"):
    """
    Fragt dein Ollama/Mistral-Modell nach einer Antwort.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    response = requests.post(OLLAMA_URL, json=payload)
    response.raise_for_status()
    return response.json()["response"]

@app.route("/ask", methods=["POST"])
def handle_ask():
    """
    Endpoint für eingehende Signal-Bridge-POST-Requests.
    Erwartet JSON mit {"message": "User-Frage"}
    """
    data = request.json
    if not data or "message" not in data:
        return jsonify({"error": "No message provided"}), 400

    user_message = data["message"]
    print(f"[INPUT] {user_message}")

    try:
        bot_response = ask_ollama(user_message)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    print(f"[OUTPUT] {bot_response}")
    return jsonify({"response": bot_response})

if __name__ == "__main__":
    # Achtung: Port 5210, damit es nicht mit deinem 5200er kollidiert!
    app.run(host="0.0.0.0", port=5210, debug=True)