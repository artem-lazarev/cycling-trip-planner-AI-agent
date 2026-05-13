DEFINITION = {
    "name": "get_elevation_profile",
    "description": (
        "Get terrain difficulty for a cycling segment. Returns total elevation "
        "gain in metres and a difficulty rating (flat, rolling, hilly, or "
        "mountainous)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "start": {
                "type": "string",
                "description": "Start of the segment, e.g. 'Hamburg'",
            },
            "end": {
                "type": "string",
                "description": "End of the segment, e.g. 'Lübeck'",
            },
        },
        "required": ["start", "end"],
    },
}


# Hardcoded gain (in metres) for a few known European segments. The agent uses
# this to flag tough days. Unknown segments fall back to "rolling".
_SEGMENTS = {
    ("amsterdam", "bremen"): 120,
    ("bremen", "hamburg"): 90,
    ("hamburg", "lübeck"): 110,
    ("lübeck", "puttgarden"): 80,
    ("puttgarden", "copenhagen"): 140,
    ("amsterdam", "osnabrück"): 180,
    ("paris", "lille"): 350,
}


def _rating(gain):
    if gain < 150:
        return "flat"
    if gain < 400:
        return "rolling"
    if gain < 900:
        return "hilly"
    return "mountainous"


def execute(tool_input):
    start = tool_input.get("start", "").strip()
    end = tool_input.get("end", "").strip()
    key = (start.lower(), end.lower())

    gain = _SEGMENTS.get(key, 200)
    return f"{start} -> {end}: ~{gain} m elevation gain, terrain is {_rating(gain)}."
