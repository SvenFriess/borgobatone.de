from flask import Flask, request, jsonify, render_template_string
import os

app = Flask(__name__)

# Kontextdatei laden
with open("static/borgobatone.txt", "r", encoding="utf-8") as f:
    borgo_text = f.read()

# HTML für das Frontend
html_page = """
<!DOCTYPE html>
<html>
<head><title>Borgo Batone</title></head>
<body>
  <h1>Borgo Batone sagt hallo!</h1>
  <form id="chatForm">
    <input type="text" name="prompt" placeholder="Frag mich was..." required>
    <button type="submit">Senden</button>
  </form>
  <p id="antwort"></p>

  <script>
    document.getElementById("chatForm").addEventListener("submit", async function(e) {
      e.preventDefault();
      const prompt = document.querySelector("input[name='prompt']").value;
      const response = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_input: prompt })
      });
      const data = await response.json();
      document.getElementById("antwort").innerText = "Antwort: " + data.response;
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
    frage = data.get("user_input", "").strip().lower()

    # Suche nach Antwort im Text
    antwort = "Ich habe darauf leider keine passende Antwort gefunden."
    for abschnitt in borgo_text.split("Frage: "):
        if frage in abschnitt.lower():
            teile = abschnitt.split("Antwort:")
            if len(teile) > 1:
                antwort = teile[1].strip()
            break

    return jsonify({"response": antwort})

@app.route("/ping")
def ping():
    return "Server läuft 🚀"

if __name__ == "__main__":
    app.run(port=5200)