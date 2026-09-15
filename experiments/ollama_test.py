import sys

import requests

OLLAMA_URL = "http://localhost:11434"
MODEL = "llama3.2"
PROMPT = "What is AI?"


def main():
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": MODEL, "prompt": PROMPT, "stream": False},
            timeout=120,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to Ollama at http://localhost:11434")
        print("Make sure Ollama is installed and running, then try again.")
        sys.exit(1)
    except requests.exceptions.HTTPError as exc:
        print(f"Error: Ollama returned {exc.response.status_code}")
        print(exc.response.text)
        sys.exit(1)

    data = response.json()
    print(data["response"])


if __name__ == "__main__":
    main()
