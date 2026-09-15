from langchain_core.tools import tool


@tool
def get_weather(city: str) -> str:
    """Get the current weather for a city."""
    return f"It's sunny in {city}, 28C"


print("name:", get_weather.name)
print("description:", get_weather.description)
print("args:", get_weather.args)
