from typing import Literal

from pydantic import BaseModel, Field, ValidationError

from . import get_route


class FindAccommodationInput(BaseModel):
    location: str = Field(min_length=1)
    accommodation_type: Literal["camping", "hostel", "hotel"]
    count: int = Field(default=2, ge=1, le=3)


DEFINITION = {
    "name": "find_accommodation",
    "description": (
        "Find places to stay near a given waypoint city. Supports camping, "
        "hostel, or hotel. Returns a short list of mock listings with name "
        "and approximate price per night. Only verified waypoint cities are "
        "accepted — querying an unverified town returns an error."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "Waypoint city to search near, e.g. 'Hamburg'",
            },
            "accommodation_type": {
                "type": "string",
                "enum": ["camping", "hostel", "hotel"],
                "description": "Type of accommodation to look for",
            },
            "count": {
                "type": "integer",
                "description": "How many listings to return.",
                "minimum": 1,
                "maximum": 3,
                "default": 2,
            },
        },
        "required": ["location", "accommodation_type"],
    },
}


# Per-type price ranges and naming patterns. Keeps the mock realistic enough
# that the agent can reason about budget and preference trade-offs.
_PRICE = {
    "camping": (12, 22),
    "hostel": (25, 45),
    "hotel": (70, 130),
}

_NAME_PATTERNS = {
    "camping": ["Camping {loc}", "{loc} Riverside Camp", "Naturpark {loc}"],
    "hostel": ["{loc} City Hostel", "Backpackers {loc}", "Hostel Old Town {loc}"],
    "hotel": ["Hotel {loc} Centrum", "{loc} Comfort Inn", "Grand Hotel {loc}"],
}


def execute(tool_input):
    try:
        data = FindAccommodationInput.model_validate(tool_input)
    except ValidationError as e:
        err = e.errors()[0]
        return f"Invalid input for find_accommodation: {err['msg']} (field: {err['loc'][0]})"

    location = data.location.strip()
    acc_type = data.accommodation_type
    count = data.count

    if location.lower() not in get_route.known_cities():
        # Don't fabricate listings for unverified towns. Force the agent to
        # pick a named waypoint instead of inventing "rural Schleswig" etc.
        return (
            f"No verified listings for '{location}' — it isn't a known waypoint. "
            "Pick a named waypoint city (use get_route to see valid options) "
            "and do NOT present invented accommodation names to the user."
        )

    low, high = _PRICE[acc_type]
    patterns = _NAME_PATTERNS[acc_type]
    mid = (low + high) // 2

    listings = []
    for i in range(count):
        name = patterns[i % len(patterns)].format(loc=location)
        # Slight price variation across listings so they don't all look identical.
        price = low if i == 0 else (mid if i == 1 else high)
        listings.append(f"{name} ({acc_type}, ~€{price}/night)")

    return f"Accommodation near {location}: " + "; ".join(listings) + "."
