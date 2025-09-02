from flask_cors import CORS

import logging

logging.basicConfig(
    filename='/Users/svenfriess/Desktop/borgobatone.de/borgo_chatbot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    force=True
)

from flask import Flask, request, jsonify, render_template, render_template_string
import os
from datetime import datetime
import subprocess
import logging
from time import perf_counter
from langdetect import detect

app = Flask(__name__)
CORS(app)  # CORS aktiviert für alle Domains
CORS(app)  # CORS aktiviert für alle Domains

# 🔹 Logging einrichten
logger = logging.getLogger('borgo_chatbot')
logger.setLevel(logging.DEBUG)  # DEBUG statt INFO
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

html_page = """<!DOCTYPE html>
<html lang="de">
<head>
<style>
.spinner {
  display: inline-block;
  width: 12px;
  height: 12px;
  margin-left: 8px;
  border: 2px solid #ccc;
  border-top: 2px solid #333;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  vertical-align: middle;
}
.status-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  margin-left: 8px;
  border-radius: 50%;
  background-color: #4CAF50;
  animation: pulse 1.5s infinite;
  vertical-align: middle;
}
@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
@keyframes pulse {
  0% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.5); opacity: 0.6; }
  100% { transform: scale(1); opacity: 1; }
}
</style>

  <meta charset="UTF-8">
  <title>Borgo Batone Bot</title>
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
    .faq-buttons {
      padding: 1rem;
      background: #fff8e1;
      font-size: 14px;
      margin: 1rem;
      border-radius: 8px;
      width: 90%;
      max-width: 300px;
    }
  </style>
</head>
<body>
  <h1>Borgo Batone Bot</h1>
  <form id="chatForm">
    <label for="modellwahl">Modell wählen:</label>
    <select id="modellwahl">
      <option value="granite3.3:2b">Granite 3.3 (2B)</option>
      <option value="qwen3:latest">Qwen 3</option>
      <option value="deepseek-r1:1.5b">DeepSeek R1 (1.5B)</option>
      <option value="mistral:latest">Mistral</option>
      <option value="gemma:2b">Gemma 2B</option>
      <option value="llama3.2:latest">LLaMA 3.2</option>
</select>



<table>
  <thead>
    <tr><th>Modell</th><th>Beschreibung</th></tr>
  </thead>
  <tbody>
    <tr><td>mistral</td><td>Schnell, gute Deutschleistung (einziges europäisches Modell)</td></tr>
    <tr><td>llama3</td><td>Groß, präzise, langsam</td></tr>
    <tr><td>tinyllama</td><td>Sehr klein, englisch fokussiert</td></tr>
    <tr><td>gemma</td><td>BEST for Usecase "Borgo": schnell, klein, balanciert, stabil</td></tr>
    <tr><td>granite</td><td>Kompakt, reaktionsschnell, für einfache Fragen</td></tr>
    <tr><td>qwen</td><td>Stark bei Code & Multilingualität</td></tr>
  </tbody>
</table>

<!-- Hier kommt dein Zusatztext -->
<p><b>Frage eingeben oder Beispielfrage wählen. Auf “Senden” klicken. Antwort erscheint nach kurzer Verarbeitugszeit.</b></p>




    <input type="text" id="userInput" name="prompt" placeholder="Frag mich was..." required>
    <button type="submit">Senden</button>
  </form>
  <p id="antwort"></p>
  <p id="zeitstempel" style="font-size: small; color: gray;"></p>

  <div class="faq-buttons">
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

  <script>
    function insertText(text) {
      const input = document.getElementById("userInput");
      input.value = text;
      sendMessage();
    }

    async function sendMessage() {
      const prompt = document.querySelector("input[name='prompt']").value;
      const modell = document.getElementById("modellwahl").value;
      const response = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_input: prompt, model: modell, user_id: "frontend-user" })
      });
      const data = await response.json();
      document.getElementById("antwort").innerText = "Antwort: " + data.response;
      document.getElementById("zeitstempel").innerText = "Zeitstempel: " + data.timestamp;
    }

    document.getElementById("chatForm").addEventListener("submit", function(e) {
      e.preventDefault();
      sendMessage();
    });
  </script>

<script>
function showModelLoading() {
  document.getElementById("model-name").innerText = "Wird geladen...";
  document.getElementById("status-icon").className = "spinner";
}
function updateModelStatus(modelName) {
  document.getElementById("model-name").innerText = modelName;
  document.getElementById("status-icon").className = "status-dot";
}
function onModelChange() {
  const select = document.getElementById("model-select");
  const selectedModel = select.value;
  if (!selectedModel) return;
  showModelLoading();
  setTimeout(() => updateModelStatus(selectedModel), 1500);
}
</script>

</body>
</html>
"""

@app.route("/")
def home():
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

    logger.debug(f"Frage an Modell: {frage} (Modell: {modell})", extra={"user_id": user_id, "ip_address": request.remote_addr})

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

if __name__ == "__main__":
  import sys
  port = int(sys.argv[1]) if len(sys.argv) > 1 else 5200
  app.run(host="0.0.0.0", port=5200)