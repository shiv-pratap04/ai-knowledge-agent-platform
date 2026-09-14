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
    print("Step 1 - User question:")
    print(USER_PROMPT)
    print()

    first_response = generate(SYSTEM_PROMPT, USER_PROMPT)
    print("Step 2 - LLM tool-call decision:")
    print(first_response.strip())
    print()

    city = parse_tool_call(first_response)
    if not city:
        print("Step 3 - No tool call. Using the first reply as the final answer:")
        print(first_response.strip())
        return

    print(f"Calling get_weather({city})...")
    tool_result = get_weather(city)
    print("Step 3 - Tool execution result:")
    print(tool_result)
    print()

    follow_up_prompt = (
        f"User question: {USER_PROMPT}\n"
        f"Your previous tool-call response: {first_response.strip()}\n"
        f"Tool result: {tool_result}\n\n"
        "Given this tool result, answer the user's original question in a natural sentence."
    )
    final_answer = generate(SYSTEM_PROMPT, follow_up_prompt)

    print("Step 4 - Final LLM answer:")
    print(final_answer.strip())


if __name__ == "__main__":
    main()
