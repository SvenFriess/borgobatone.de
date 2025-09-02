from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import logging
from datetime import datetime

app = Flask(__name__)
CORS(app)

# 📄 Logging aktivieren
log_file_path = "/Users/svenfriess/Desktop/feinefahrten.de/chatbot.log"
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)

# 🌐 Startseite mit Button und Popup-Chat
@app.route("/")
@app.route("/chat")
def chat_popup():
    return render_template("chat.html")

# 💬 Nur das reine Chatfenster
@app.route("/chatwindow")
def chat_window_only():
    return render_template("chat_only.html")

# 🤖 API-Endpoint zum Generieren von Antworten
@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json()
    user_input = data.get("user_input", "")

    logging.info(f"🟡 Eingabe erhalten: {user_input}")

    try:
        # 📥 Kontext bei jedem Request neu laden
        with open("/Users/svenfriess/Desktop/borgobatone.de/static/borgobatone.txt", "r", encoding="utf-8") as f:
            context = f.read()

        logging.info(f"📄 Kontext geladen (Vorschau): {context[:200]}...")

        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "llama3.1",
                "messages": [
                    {
                        "role": "system",
                        "content": "Du bist ein sachlicher, deutschsprachiger Chatbot für das Projekt Borgo Batone. Nutze ausschließlich den folgenden Kontext für deine Antworten:\n\n" +
                                   context +
                                   "\n\nAntworte kurz und präzise in maximal 3 Sätzen. Keine Begrüßung, keine Gegenfragen. Nur die konkrete Antwort."
                    },
                    {
                        "role": "user",
                        "content": user_input
                    }
                ],
                "stream": False
            }
        )
        response.raise_for_status()
        result = response.json()
        reply = result["message"]["content"]
        logging.info(f"🟢 Antwort generiert: {reply}")
        return jsonify({"response": reply})
    except Exception as e:
        logging.error(f"🔴 Fehler: {e}")
        return jsonify({"error": str(e)}), 500

# 🟢 Server starten
if __name__ == "__main__":
    app.run(port=5200)
