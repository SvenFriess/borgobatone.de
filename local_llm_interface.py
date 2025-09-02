# Datei: local_llm_interface.py

import subprocess

def generate_response_with_llm(prompt, debug=False, model_name="mistral:latest"):
    """
    Sendet ein Prompt an das lokal laufende Modell via Ollama und gibt die Antwort zurück.
    """
    if debug:
        print(f"[LLM DEBUG] Prompt → Modell '{model_name}': {prompt}")

    try:
        result = subprocess.run(
            ["ollama", "run", model_name, prompt],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )

        if result.returncode != 0:
            raise RuntimeError(f"Ollama-Fehler: {result.stderr.strip()}")

        antwort = result.stdout.strip()
        if debug:
            print(f"[LLM DEBUG] Antwort:\n{antwort}")

        return antwort

    except subprocess.TimeoutExpired:
        return "⏱️ Das Modell hat zu lange gebraucht. Bitte versuch es nochmal."

    except Exception as e:
        return f"❌ LLM-Fehler: {str(e)}"