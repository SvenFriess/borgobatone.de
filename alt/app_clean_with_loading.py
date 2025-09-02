
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def index():
    return """<!DOCTYPE html>
<html>
<head>
    <title>BorgoBot</title>
    <style>
        body { font-family: Arial; margin: 40px; }
        .question-button {
            display: block;
            margin: 5px 0;
            padding: 8px 12px;
            background-color: #f0f0f0;
            border: 1px solid #ccc;
            cursor: pointer;
        }
        .question-button:hover {
            background-color: #e0e0e0;
        }
        #loading {
            margin-top: 10px;
            font-weight: bold;
            display: none;
        }
    </style>
</head>
<body>
    <h1>BorgoBot – Frag mich was!</h1>
    <form id="chat-form">
        <input type="text" name="user_input" placeholder="Deine Frage..." required>
        <button type="submit">Senden</button>
    </form>

    <div id="loading">⏳ Bitte warten...</div>
    <div id="antwort" style="margin-top:20px;"></div>

    <script>
    document.querySelector("#chat-form").addEventListener("submit", async function(e) {
        e.preventDefault();
        document.getElementById("loading").style.display = "block";

        const formData = new FormData(this);
        const response = await fetch("/api/generate", {
            method: "POST",
            body: formData
        });

        const result = await response.json();
        document.getElementById("loading").style.display = "none";
        document.getElementById("antwort").innerText = result.text;
    });
    </script>
</body>
</html>"""

@app.route("/api/generate", methods=["POST"])
def generate():
    user_input = request.form["user_input"]
    # Beispielantwort, bitte durch Modellaufruf ersetzen
    response_text = f"Du hast gefragt: {user_input} – Hier kommt eine Demo-Antwort."
    return jsonify({"text": response_text})
