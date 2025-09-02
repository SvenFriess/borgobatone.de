import requests
import json
import logging

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "mistral:instruct"

logging.basicConfig(
    filename="ollama_test.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

def test_ollama():
    prompt = "User: Was tun im Notfall?\nAssistant:"
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        logging.info("CT=" + content_type)
        raw = response.text
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            logging.info("🔍 Chunk: " + line[:300])
            try:
                data = json.loads(line)
                if "message" in data:
                    antwort = data["message"].get("content", "").strip()
                    if antwort:
                        logging.info("✅ Antwort: " + antwort[:200])
                        print("Antwort:", antwort)
                        return
            except Exception as e:
                logging.warning("Skipping line, decode error: " + str(e))
        logging.warning("⚠️ Keine gültige Antwort empfangen")
    except Exception as e:
        logging.error("Fehler bei Anfrage an Ollama: " + str(e))

if __name__ == "__main__":
    test_ollama()
