from pydantic import BaseModel, Field, ValidationError


class GetWeatherInput(BaseModel):
    location: str = Field(min_length=1)
    month: str = Field(min_length=1)


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
    try:
        data = GetWeatherInput.model_validate(tool_input)
    except ValidationError as e:
        err = e.errors()[0]
        return f"Invalid input for get_weather: {err['msg']} (field: {err['loc'][0]})"

    location = data.location.strip()
    month = data.month.strip()
    key = (location.lower(), month.lower())

    if key in _WEATHER:
        return f"{month} in {location}: {_WEATHER[key]}."

    return (
        f"No specific data for {location} in {month}. "
        "Generic temperate-Europe summer estimate: avg ~16°C, frequent light "
        "rain (~10 days), mild westerly winds. Present this to the user as a "
        "rough regional guess, not location-specific data."
    )
