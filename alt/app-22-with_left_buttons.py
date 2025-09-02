from flask import Flask, request, jsonify, render_template, render_template_string
import os
from datetime import datetime
import subprocess
import logging
from time import perf_counter
from langdetect import detect

app = Flask(__name__)

# 🔹 Logging einrichten
logger = logging.getLogger('borgo_chatbot')
logger.setLevel(logging.INFO)
handler = logging.FileHandler('borgo_chatbot.log')
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(module)s - %(funcName)s - USER:%(user_id)s - IP:%(ip_address)s - %(message)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# 🔹 Logging-Helferfunktion
def log_request(message, user_id='anonymous'):
    try:
        forwarded_for = request.headers.get('X-Forwarded-For', request.remote_addr)
        extra = {
            'user_id': user_id,
            'ip_address': forwarded_for
        }
        logger.info(message, extra=extra)
    except Exception as e:
        print(f"[LOGGING-FEHLER] {e}")


# Kontextdatei laden
with open("static/borgobatone.txt", "r", encoding="utf-8") as f:
    borgo_text = f.read()

# HTML für das Frontend (Startseite)
html_page = """<!DOCTYPE html>
<html>
<head>
  <title>Borgo Batone</title>
  <style>
    body {
      background-image: url('/static/Borgo-Landscape.jpg');
      background-size: cover;
      background-repeat: no-repeat;
      background-position: center center;
      color: white;
      text-shadow: 0 0 5px black;
      font-family: sans-serif;
    }
    label, input, select, button {
      background: rgba(255, 255, 255, 0.8);
      color: black;
      padding: 5px;
      margin: 5px 0;
      border-radius: 4px;
      border: none;
    }
    input, select {
      width: 300px;
    }
  </style>
</head>
<body>
  <h1>Borgo Batone Bot</h1>
  <form id=\"chatForm\">
    <label for=\"modellwahl\">Modell wählen:</label>
    <select id=\"modellwahl\">
      <option value=\"llama3.2:latest\">llama3.2:latest</option>
      <option value=\"mistral:latest\">mistral:latest</option>
      <option value=\"gemma:2b\">gemma:2b</option>
    </select><br><br>


    <input type="text" id="userInput" name="prompt" placeholder="Frag mich was..." required>

    <button type=\"submit\">Senden</button>
  </form>
  <p id=\"antwort\"></p>
  <p id=\"zeitstempel\" style=\"font-size: small; color: gray;\"></p>
  <h1>_</h1> 
  

<div style="padding: 1rem; background: #fff8e1; font-size: 14px; margin: 1rem; border-radius: 8px; width: 90%; max-width: 500px; text-align: left;">
  <strong>Beispielfragen:</strong><br><br>
  <button onclick="insertText('Wo kann ich in der Nähe einkaufen?')">🛒 Einkaufen</button>
  <button onclick="insertText('Was sollte ich bei der Abreise beachten?')">🚪 Abreise</button>
  <button onclick="insertText('Wie funktioniert die Mülltrennung im Borgo?')">♻️ Müll</button>
  <button onclick="insertText('Gibt es WLAN im Borgo?')">📶 WLAN</button>
  <button onclick="insertText('Welche Yoga-Ausstattung ist vorhanden?')">🧘 Yoga</button>
  <button onclick="insertText('Gibt es gemeinschaftliche Lebensmittel?')">🥫 Vorrat</button>
  <button onclick="insertText('Wie benutze ich den Pizzaofen in Casa Gabriello?')">🍕 Pizzaofen</button>
  <button onclick="insertText('Was mache ich, wenn ich ein Tier im Haus finde?')">🐞 Tiere</button>
  <button onclick="insertText('Gibt es voll ausgestattete Küchen im Borgo?')">🍳 Küche</button>
  <button onclick="insertText('Was kann ich zur Gemeinschaft beitragen?')">🌱 Beitrag</button>
  <button onclick="insertText('Welche Häuser sind aktuell bewohnbar?')">🏠 Häuser</button>
  <button onclick="insertText('Welche Wanderungen gibt es rund um das Borgo?')">🥾 Wandern</button>
  <button onclick="insertText('Was sollte ich für meinen Aufenthalt mitbringen?')">🎒 Packliste</button>
  <button onclick="insertText('Gibt es eine Waschmaschine im Borgo?')">🧺 Waschmaschine</button>
  <button onclick="insertText('Welche Ausflugsziele gibt es in der Umgebung?')">🚗 Ausflüge</button>
</div>


  <h2>Testfragen (aus borgobatone.txt):</h2>
  <p>Welche Supermärkte gibt es in der Nähe von Borgo Batone?</p>
  <p>Wo genau ist der Parkplatz von Borgo Batone?</p>
  <p>Wie wird die Stromversorgung bei Borgo Batone sichergestellt?</p>
  <p>Gibt es eine Apotheke oder einen Arzt in der Nähe von Borgo Batone?</p>
  <p>Wie funktioniert die Wasserversorgung bei Borgo Batone?</p>

<script>
  document.addEventListener("DOMContentLoaded", function() {
    window.insertText = function(text) {
      const input = document.getElementById("userInput");
      if (input) {
        input.value = text;
        input.focus();
      } else {
        alert("❌ Eingabefeld mit id='userInput' nicht gefunden!");
      }
    };
  });
</script>

</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(html_page)

@app.route("/chatwindow")
def chatwindow():
    return render_template_string(html_page)



@app.route("/api/generate", methods=["POST"])
def generate():
    start_time = perf_counter()
    data = request.get_json()
    frage = data.get("user_input", "").strip()
    modell = data.get("model", "llama3.2:latest")
    user_id = data.get("user_id", "anonymous")

    log_request(f"Empfangene Frage: {frage}", user_id=user_id)

    prompt = f"""
Du bist ein freundlicher Assistent für das Projekt Borgo Batone.
Nutze den folgenden Kontext zur Beantwortung der Frage:

{borgo_text}

Frage: {frage}
Antwort:
""".strip()

    try:
        result = subprocess.run(
            ["/usr/local/bin/ollama", "run", modell],
            input=prompt.encode("utf-8"),
            capture_output=True,
            check=True
        )
        antwort = result.stdout.decode("utf-8").strip()
        sprache = detect(antwort)
        fehlercode = "0"
    except subprocess.CalledProcessError as e:
        antwort = "Fehler beim Aufruf des LLM."
        sprache = "unbekannt"
        fehlercode = str(e.returncode)

    dauer_ms = int((perf_counter() - start_time) * 1000)
    log_request(f"Antwort: {antwort} | Dauer: {dauer_ms}ms | Modell: {modell} | Länge: {len(antwort)} Zeichen | Sprache: {sprache} | Fehlercode: {fehlercode}", user_id=user_id)

    return jsonify({
        "timestamp": datetime.utcnow().isoformat(),
        "response": antwort
    })


@app.route("/ping")
def ping():
    return "Server läuft 🚀"

@app.route("/chat")
def chat():
    return render_template("chat.html")

if __name__ == "__main__":
    app.run(port=5200)
