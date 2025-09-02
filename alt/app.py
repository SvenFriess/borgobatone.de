from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import logging
from datetime import datetime
import time
import uuid
import traceback
import json
import user_agents
import os
import pandas as pd
import matplotlib.pyplot as plt

app = Flask(__name__)
CORS(app)

log_file_path = "/Users/svenfriess/Desktop/borgobatone.de/chatbot.log"
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)

with open("/Users/svenfriess/Desktop/borgobatone.de/static/borgobatone.txt", "r", encoding="utf-8") as f:
    borgobatone_context = f.read()

@app.route("/")
@app.route("/chat")
def chat_popup():
    return render_template("chat.html")

@app.route("/chatwindow")
def chat_window_only():
    return render_template("chat_only.html")

@app.after_request
def log_response(response):
    return response

@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json()
    user_input = data.get("user_input", "")

    USE_NEW_CODE = True

    ip_address = request.remote_addr
    user_agent_str = request.headers.get("User-Agent", "Unbekannt")
    user_agent = user_agents.parse(user_agent_str)
    location = "Unbekannt"
    request_id = uuid.uuid4()

    logging.info(f"🟡 [{request_id}] Eingabe von {ip_address} ({location}) mit {user_agent.browser.family} auf {user_agent.os.family} – {user_input}")

    try:
        start_time = time.time()

        system_prompt = (
            "Du bist ein Chatbot für Borgo Batone. Antworte ausschließlich mit Inhalten aus dem bereitgestellten Kontext. "
            "Wenn keine Information vorhanden ist, antworte klar: \"Ich habe dazu keine Information im aktuellen Kontext.\" "
            "Keine freien Formulierungen. Keine Tipps. Keine Auslegungen. Maximal 2 kurze Sätze, höchstens 300 Zeichen.\n\n"
            "Kontext:\n"
            + borgobatone_context
        )

        response = requests.post(
            "http://localhost:11434/api/chat",
            json={
                "model": "llama3.1",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ],
                "stream": False,
                "options": {
                    "num_predict": 300
                }
            }
        )

        duration = round(time.time() - start_time, 2)
        response.raise_for_status()
        result = response.json()
        reply = result.get("message", {}).get("content", "Ich habe dazu keine Information im aktuellen Kontext.")

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": str(request_id),
            "ip": ip_address,
            "location": location,
            "browser": user_agent.browser.family,
            "os": user_agent.os.family,
            "user_agent": user_agent_str,
            "user_input": user_input,
            "response_time": duration,
            "model": "llama3.1",
            "reply": reply
        }
        logging.info("🟢 Antwort generiert: " + json.dumps(log_entry, ensure_ascii=False))

        return jsonify({"response": reply})
    except Exception as e:
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": str(request_id),
            "ip": ip_address,
            "user_agent": user_agent_str,
            "location": location,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        logging.error("🔴 Fehler bei Anfrage: " + json.dumps(error_entry, ensure_ascii=False))
        return jsonify({"error": str(e)}), 500

@app.route("/logs/auswertung")
def auswertung():
    lines = []
    with open(log_file_path, "r") as f:
        for line in f:
            if "Antwort generiert" in line:
                try:
                    data = json.loads(line.split("🟢 Antwort generiert: ")[-1])
                    lines.append(data)
                except:
                    continue

    df = pd.DataFrame(lines)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.sort_values("timestamp", inplace=True)

    df["date"] = df["timestamp"].dt.date
    count_per_day = df.groupby("date").size()
    count_per_day.plot(kind="bar", title="Zugriffe pro Tag")
    plt.tight_layout()
    plt.savefig("/Users/svenfriess/Desktop/logs_anzahl.png")

    df.plot(x="timestamp", y="response_time", title="Antwortzeitverlauf", figsize=(10,4))
    plt.tight_layout()
    plt.savefig("/Users/svenfriess/Desktop/logs_responsezeit.png")

    return "Logauswertung abgeschlossen. Grafiken wurden gespeichert."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5200)
