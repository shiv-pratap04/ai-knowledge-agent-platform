import json
import sys

import requests

OLLAMA_URL = "http://localhost:11434"
MODEL = "llama3.2"
USER_PROMPT = "What's the weather like in Manipur?"

SYSTEM_PROMPT = (
    "You have access to a tool called get_weather(city). "
    "If the user asks about weather, respond ONLY with JSON in this exact format: "
    '{"tool": "get_weather", "args": {"city": "<city name>"}}. '
    "Otherwise respond normally with plain text."
)

# Schema describing the dummy tool to the LLM (used conceptually; the prompt is the contract).
GET_WEATHER_SCHEMA = {
    "name": "get_weather",
    "description": "Get the current weather for a city.",
    "parameters": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name to look up weather for."}
        },
        "required": ["city"],
    },
}


def get_weather(city: str) -> str:
    return f"It's sunny in {city}, 28°C"


def generate(system_prompt, user_prompt):
    try:
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "system": system_prompt,
                "prompt": user_prompt,
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


def parse_tool_call(raw_text):
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None
    if data.get("tool") != "get_weather":
        return None
    args = data.get("args") or {}
    city = args.get("city")
    if not city:
        return None
    return city


def main():
    print("Available tool schema:")
    print(json.dumps(GET_WEATHER_SCHEMA, indent=2))
    print()
    print(f"User: {USER_PROMPT}\n")

    raw = generate(SYSTEM_PROMPT, USER_PROMPT)
    print("Raw LLM response:")
    print(raw)
    print()

    city = parse_tool_call(raw)
    if city:
        print(f"LLM wants to call: get_weather({city})")
        print("(Not executing the tool yet - that is tomorrow's task.)")
    else:
        print("No tool-call JSON detected. Treating this as a normal text reply.")


if __name__ == "__main__":
    main()
