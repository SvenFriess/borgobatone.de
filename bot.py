import yaml
import requests
import subprocess
import json
import time

# === Konfiguration laden ===
with open("config.yaml") as f:
    config = yaml.safe_load(f)

MODEL = config["llm"]["model"]
ENDPOINT = config["llm"]["endpoint"]
SYSTEM_PROMPT = config["llm"]["system_prompt"]
TEMPERATURE = config["llm"]["temperature"]

# === Ollama-Request ===
def query_llm(prompt):
    response = requests.post(
        f"{ENDPOINT}/api/generate",
        json={
            "model": MODEL,
            "prompt": prompt,
            "system": SYSTEM_PROMPT,
            "temperature": TEMPERATURE,
            "stream": False
        }
    )
    return response.json()["response"]

# === Signal-Empfang via signal-cli JSON-RPC (vereinfacht) ===
def listen_and_respond():
    print("Starte Borgobatone-Bot…")
    while True:
        try:
            raw = subprocess.run(
                ["signal-cli", "-u", "+4915755901211", "receive", "-t", "json"],
                capture_output=True, text=True, timeout=10
            )
            if raw.stdout.strip() == "":
                time.sleep(1)
                continue

            for line in raw.stdout.strip().split("\n"):
                msg = json.loads(line)
                if "envelope" in msg and "dataMessage" in msg["envelope"]:
                    sender = msg["envelope"]["source"]
                    message = msg["envelope"]["dataMessage"].get("message", "")
                    print(f"[{sender}] {message}")

                    reply = query_llm(message)
                    subprocess.run([
                        "signal-cli", "-u", "+4915755901211", "send", "-m", reply, sender
                    ])
        except subprocess.TimeoutExpired:
            pass
        except Exception as e:
            print(f"[Fehler] {e}")
            time.sleep(5)

if __name__ == "__main__":
    listen_and_respond()