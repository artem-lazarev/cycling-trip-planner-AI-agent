DEFINITION = {
    "name": "get_route",
    "description": (
        "Get a cycling route between two points. Returns total distance in km, "
        "estimated number of days at the given daily distance, and an ordered "
        "list of segments (consecutive waypoint pairs) with per-segment "
        "distance. Lookups are direction-agnostic — querying (end, start) "
        "returns the reversed route."
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
                "description": "Target daily distance in km.",
                "default": 80,
            },
        },
        "required": ["start", "end"],
    },
}


# Mock route data for a handful of well-known European cycling corridors.
# Each route is a list of (from_city, to_city, distance_km) segments in
# canonical direction. Reverse-direction lookups flip the segment list.
_ROUTES = {
    ("amsterdam", "copenhagen"): [
        ("Amsterdam", "Bremen", 260),
        ("Bremen", "Hamburg", 125),
        ("Hamburg", "Lübeck", 70),
        ("Lübeck", "Puttgarden", 90),
        ("Puttgarden", "Copenhagen", 235),
    ],
    ("amsterdam", "berlin"): [
        ("Amsterdam", "Osnabrück", 200),
        ("Osnabrück", "Hannover", 160),
        ("Hannover", "Magdeburg", 160),
        ("Magdeburg", "Berlin", 140),
    ],
    ("paris", "amsterdam"): [
        ("Paris", "Lille", 225),
        ("Lille", "Brussels", 115),
        ("Brussels", "Antwerp", 50),
        ("Antwerp", "Amsterdam", 130),
    ],
    ("london", "paris"): [
        ("London", "Dover", 120),
        ("Dover", "Calais", 40),
        ("Calais", "Amiens", 155),
        ("Amiens", "Paris", 155),
    ],
}


def _lookup(start_lc, end_lc):
    if (start_lc, end_lc) in _ROUTES:
        return _ROUTES[(start_lc, end_lc)]
    if (end_lc, start_lc) in _ROUTES:
        return [(b, a, d) for (a, b, d) in reversed(_ROUTES[(end_lc, start_lc)])]
    return None


def known_cities():
    """All waypoint cities across known routes, lowercased."""
    cities = set()
    for segments in _ROUTES.values():
        for a, b, _ in segments:
            cities.add(a.lower())
            cities.add(b.lower())
    return cities


def execute(tool_input):
    start = tool_input.get("start", "").strip()
    end = tool_input.get("end", "").strip()
    daily = float(tool_input.get("daily_distance_km") or 80)

    segments = _lookup(start.lower(), end.lower())

    if segments is None:
        return (
            f"Route {start} -> {end}: not in our database. "
            "No verified distance or waypoint data available. "
            "Tell the user the route isn't well-known and either ask them "
            "to name intermediate cities, or proceed with anonymous day "
            "labels ('Day 1 leg', 'Day 2 leg') — do NOT invent city names."
        )

    distance = sum(d for _, _, d in segments)
    days = max(1, round(distance / daily))
    waypoints = [segments[0][0]] + [b for _, b, _ in segments]
    seg_lines = "; ".join(f"{a}->{b} ({d} km)" for a, b, d in segments)
    note = (
        f"{len(segments)} segments vs ~{days} target days — "
        "if days > segments, plan rest days or split long legs across multiple "
        "riding days (camp/stay at a named waypoint, not a fabricated town). "
        "If days < segments, ride through some waypoints without stopping."
    )
    return (
        f"Route {start} -> {end}: ~{distance} km, "
        f"~{days} days at {daily:.0f} km/day. "
        f"Waypoints: {', '.join(waypoints)}. "
        f"Segments: {seg_lines}. {note}"
    )
