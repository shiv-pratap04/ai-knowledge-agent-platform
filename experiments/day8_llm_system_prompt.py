import sys

import requests

OLLAMA_URL = "http://localhost:11434"
MODEL = "llama3.2"
USER_PROMPT = "What is the capital of France?"

TESTS = [
    {
        "label": "One short sentence",
        "system": "You are a helpful assistant that answers in exactly one short sentence, no more.",
    },
    {
        "label": "Pirate speak",
        "system": "You are a pirate. Answer everything in pirate speak.",
    },
]


def generate(system_prompt):
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "system": system_prompt,
                "prompt": USER_PROMPT,
                "stream": False,
            },
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

    return response.json()["response"]


def main():
    results = []
    for test in TESTS:
        print(f"--- {test['label']} ---")
        print(f"System: {test['system']}")
        print(f"User:   {USER_PROMPT}")
        answer = generate(test["system"])
        print(f"Reply:  {answer.strip()}\n")
        results.append((test["label"], answer.strip()))

    print("=" * 60)
    print("Same question, different system prompts:\n")
    print(f"User: {USER_PROMPT}\n")
    for label, answer in results:
        print(f"{label}:")
        print(f"  {answer}\n")


if __name__ == "__main__":
    main()
