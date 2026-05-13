DEFINITION = {
    "name": "get_weather",
    "description": (
        "Get typical weather for a location in a given month. "
        "Use this to advise the cyclist on what to expect (temperature, rain, wind) "
        "for the month they plan to travel."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "City or region, e.g. 'Amsterdam' or 'Northern Germany'",
            },
            "month": {
                "type": "string",
                "description": "Month of travel, e.g. 'June'",
            },
        },
        "required": ["location", "month"],
    },
}


# Tiny mock lookup. Keyed by (location_lowercase, month_lowercase).
# Anything not found falls back to a generic temperate-Europe summary.
_WEATHER = {
    ("amsterdam", "june"): "avg 17°C, ~10 rainy days, mild W headwinds",
    ("amsterdam", "july"): "avg 19°C, ~9 rainy days, occasional W winds",
    ("hamburg", "june"): "avg 16°C, ~11 rainy days, cool mornings",
    ("bremen", "june"): "avg 16°C, ~10 rainy days, light winds",
    ("copenhagen", "june"): "avg 15°C, ~9 rainy days, breezy from W/NW",
    ("berlin", "june"): "avg 18°C, ~8 rainy days, mostly calm",
}


def execute(tool_input):
    location = tool_input.get("location", "").strip()
    month = tool_input.get("month", "").strip()
    key = (location.lower(), month.lower())

    if key in _WEATHER:
        return f"{month} in {location}: {_WEATHER[key]}."

    return (
        f"{month} in {location}: typical temperate-Europe summer — "
        "avg ~16°C, frequent light rain (~10 days), mild westerly winds."
    )
