from pydantic import BaseModel, Field, ValidationError


class GetElevationInput(BaseModel):
    start: str = Field(min_length=1)
    end: str = Field(min_length=1)


DEFINITION = {
    "name": "get_elevation_profile",
    "description": (
        "Get terrain difficulty for a cycling segment. Returns total elevation "
        "gain in metres and a difficulty rating (flat, rolling, hilly, or "
        "mountainous). Direction-agnostic — A->B and B->A return the same gain."
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


# Hardcoded gain (in metres) for known European segments. Keys are
# frozenset({city_a, city_b}) so lookup is direction-agnostic. Coverage
# must include every consecutive waypoint pair used in get_route._ROUTES.
def _seg(a, b):
    return frozenset({a, b})


_SEGMENTS = {
    # Amsterdam -> Copenhagen
    _seg("amsterdam", "bremen"): 120,
    _seg("bremen", "hamburg"): 90,
    _seg("hamburg", "lübeck"): 110,
    _seg("lübeck", "puttgarden"): 80,
    _seg("puttgarden", "copenhagen"): 140,
    # Amsterdam -> Berlin
    _seg("amsterdam", "osnabrück"): 180,
    _seg("osnabrück", "hannover"): 220,
    _seg("hannover", "magdeburg"): 170,
    _seg("magdeburg", "berlin"): 140,
    # Paris -> Amsterdam
    _seg("paris", "lille"): 350,
    _seg("lille", "brussels"): 200,
    _seg("brussels", "antwerp"): 70,
    _seg("antwerp", "amsterdam"): 60,
    # London -> Paris
    _seg("london", "dover"): 260,
    _seg("dover", "calais"): 30,
    _seg("calais", "amiens"): 280,
    _seg("amiens", "paris"): 240,
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
    try:
        data = GetElevationInput.model_validate(tool_input)
    except ValidationError as e:
        err = e.errors()[0]
        return f"Invalid input for get_elevation_profile: {err['msg']} (field: {err['loc'][0]})"

    start = data.start.strip()
    end = data.end.strip()
    key = _seg(start.lower(), end.lower())

    if key in _SEGMENTS:
        gain = _SEGMENTS[key]
        return f"{start} -> {end}: ~{gain} m elevation gain, terrain is {_rating(gain)}."

    # No data for this pair. Be explicit so the agent doesn't present the
    # heuristic estimate as verified terrain.
    gain = 200
    return (
        f"{start} -> {end}: no specific elevation data for this segment. "
        f"Heuristic estimate ~{gain} m (terrain likely {_rating(gain)}); "
        "tell the user this leg's terrain is approximate."
    )
