from flask import Flask, request, jsonify, render_template, render_template_string
import os
from datetime import datetime
import subprocess

app = Flask(__name__)

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
  <h1>Borgo Batone sagt hallo!</h1>
  <form id=\"chatForm\">
    <label for=\"modellwahl\">Modell wählen:</label>
    <select id=\"modellwahl\">
      <option value=\"llama3.2:latest\">llama3.2:latest</option>
      <option value=\"mistral:latest\">mistral:latest</option>
      <option value=\"gemma:2b\">gemma:2b</option>
    </select><br><br>

    <input type=\"text\" name=\"prompt\" placeholder=\"Frag mich was...\" required>
    <button type=\"submit\">Senden</button>
  </form>
  <p id=\"antwort\"></p>
  <p id=\"zeitstempel\" style=\"font-size: small; color: gray;\"></p>

  <script>
    document.getElementById("chatForm").addEventListener("submit", async function(e) {
      e.preventDefault();
      const prompt = document.querySelector("input[name='prompt']").value;
      const modell = document.getElementById("modellwahl").value;
      const response = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_input: prompt, model: modell })
      });
      const data = await response.json();
      document.getElementById("antwort").innerText = "Antwort: " + data.response;
      document.getElementById("zeitstempel").innerText = "Zeitstempel: " + data.timestamp;
    });
  </script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(html_page)

@app.route("/api/generate", methods=["POST"])
def generate():
    data = request.get_json()
    frage = data.get("user_input", "").strip()
    modell = data.get("model", "llama3.2:latest")

    # LLM-Prompt mit Kontext
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
    except subprocess.CalledProcessError as e:
        antwort = "Fehler beim Aufruf des LLM."

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
