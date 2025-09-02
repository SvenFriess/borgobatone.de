
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

# Startseite mit Button und Popup-Chat
@app.route("/")
@app.route("/chat")
def chat_popup():
    return render_template("chat.html")

# Reiner Chat-Inhalt im iFrame
@app.route("/chatwindow")
def chat_window_only():
    return render_template("chat_only.html")

# API-Endpoint zum Generieren von Antworten
@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json()
    user_input = data.get("user_input", "")
    logging.info(f"🟡 Eingabe erhalten: {user_input}")

    # Custom-Wissen direkt im Systemprompt
    system_prompt = """
Du bist ein deutschsprachiger Assistent für das Projekt Borgo Batone in Italien.
Antworte stets in 2–3 kurzen, freundlichen und informativen Sätzen auf Deutsch.

Hier ist dein Hintergrundwissen:
- Borgo Batone liegt in Italien und wird gemeinschaftlich renoviert.
- Es gibt Strom durch Solarpanels und ein Batteriesystem.
- Einkaufsmöglichkeiten sind mit dem Auto gut erreichbar.
- Gäste können bei kleinen Projekten mithelfen (z. B. Möbel reparieren).
- Es gibt keine festen Öffnungszeiten – Flexibilität ist Teil des Konzepts.
"""

    try:
        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "mistral",
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
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

if __name__ == "__main__":
    app.run(port=5200)
