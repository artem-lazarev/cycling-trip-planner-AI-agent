DEFINITION = {
    "name": "get_route",
    "description": (
        "Get a cycling route between two points. Returns total distance in km, "
        "estimated number of days at the given daily distance, and an ordered "
        "list of waypoint cities along the route."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "start": {
                "type": "string",
                "description": "Start city, e.g. 'Amsterdam'",
            },
            "end": {
                "type": "string",
                "description": "End city, e.g. 'Copenhagen'",
            },
            "daily_distance_km": {
                "type": "number",
                "description": "Target daily distance in km. Defaults to 80.",
            },
        },
        "required": ["start", "end"],
    },
}


# Mock route data for a handful of well-known European cycling corridors.
# Total distance is approximate road-cycling distance, not great-circle.
_ROUTES = {
    ("amsterdam", "copenhagen"): {
        "distance_km": 780,
        "waypoints": ["Amsterdam", "Bremen", "Hamburg", "Lübeck", "Puttgarden", "Copenhagen"],
    },
    ("amsterdam", "berlin"): {
        "distance_km": 660,
        "waypoints": ["Amsterdam", "Osnabrück", "Hannover", "Magdeburg", "Berlin"],
    },
    ("paris", "amsterdam"): {
        "distance_km": 520,
        "waypoints": ["Paris", "Lille", "Brussels", "Antwerp", "Amsterdam"],
    },
    ("london", "paris"): {
        "distance_km": 470,
        "waypoints": ["London", "Dover", "Calais", "Amiens", "Paris"],
    },
}


def execute(tool_input):
    start = tool_input.get("start", "").strip()
    end = tool_input.get("end", "").strip()
    daily = float(tool_input.get("daily_distance_km") or 80)

    key = (start.lower(), end.lower())
    route = _ROUTES.get(key)

    if route is None:
        # Generic fallback: invent a plausible distance and a sparse waypoint list.
        distance = 600
        waypoints = [start, "midpoint town", end]
    else:
        distance = route["distance_km"]
        waypoints = route["waypoints"]

    days = max(1, round(distance / daily))
    return (
        f"Route {start} -> {end}: ~{distance} km, "
        f"~{days} days at {daily:.0f} km/day. "
        f"Waypoints: {', '.join(waypoints)}."
    )
