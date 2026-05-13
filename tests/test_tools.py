from tools import ALL_TOOLS, get_weather, get_route, find_accommodation, get_elevation_profile


def test_all_tools_registered():
    assert len(ALL_TOOLS) == 4
    for tool in ALL_TOOLS:
        assert "name" in tool.DEFINITION
        assert "input_schema" in tool.DEFINITION
        assert callable(tool.execute)


def test_get_weather_known_pair():
    result = get_weather.execute({"location": "Amsterdam", "month": "June"})
    assert isinstance(result, str) and result
    assert "Amsterdam" in result
    assert "June" in result


def test_get_weather_fallback_is_explicit():
    # Unknown location should produce a usable summary AND flag it as generic.
    result = get_weather.execute({"location": "Atlantis", "month": "June"})
    assert "Atlantis" in result
    assert "no specific data" in result.lower() or "generic" in result.lower()


def test_get_route_known_pair():
    result = get_route.execute({
        "start": "Amsterdam",
        "end": "Copenhagen",
        "daily_distance_km": 100,
    })
    assert "Amsterdam" in result and "Copenhagen" in result
    assert "days" in result
    # Per-segment distances should now be exposed.
    assert "Segments:" in result
    assert "Bremen" in result


def test_get_route_is_direction_agnostic():
    forward = get_route.execute({"start": "Amsterdam", "end": "Copenhagen"})
    reverse = get_route.execute({"start": "Copenhagen", "end": "Amsterdam"})
    # Reverse direction must return a real route (not the "not in database" message).
    assert "not in our database" not in reverse
    # Both should reference the same waypoint cities.
    for city in ("Bremen", "Hamburg", "Lübeck"):
        assert city in forward and city in reverse


def test_find_accommodation_basic():
    result = find_accommodation.execute({
        "location": "Hamburg",
        "accommodation_type": "camping",
        "count": 2,
    })
    assert "Hamburg" in result
    assert "camping" in result.lower()


def test_find_accommodation_rejects_unknown_location():
    result = find_accommodation.execute({
        "location": "rural Schleswig",
        "accommodation_type": "camping",
    })
    assert "no verified" in result.lower() or "not a known waypoint" in result.lower()


def test_get_elevation_profile_rating():
    result = get_elevation_profile.execute({"start": "Hamburg", "end": "Lübeck"})
    assert "Hamburg" in result and "Lübeck" in result
    assert "elevation" in result.lower() or "m" in result


def test_get_elevation_profile_is_direction_agnostic():
    forward = get_elevation_profile.execute({"start": "Hamburg", "end": "Lübeck"})
    reverse = get_elevation_profile.execute({"start": "Lübeck", "end": "Hamburg"})
    # Same gain regardless of direction.
    assert "110" in forward and "110" in reverse


def test_get_elevation_profile_covers_all_route_segments():
    # Every consecutive waypoint pair in get_route must resolve to real data,
    # not the heuristic fallback.
    for segments in get_route._ROUTES.values():
        for a, b, _ in segments:
            result = get_elevation_profile.execute({"start": a, "end": b})
            assert "no specific elevation data" not in result, (
                f"missing elevation data for {a} -> {b}"
            )


def test_get_elevation_profile_unknown_segment_is_explicit():
    result = get_elevation_profile.execute({"start": "Atlantis", "end": "Mu"})
    assert "no specific elevation data" in result.lower()


def _load_scratch_re():
    # agent.agent imports `prompts` via the runtime PYTHONPATH=src:src/agent,
    # which isn't set in the test harness. Load just the regex from source.
    import re
    import pathlib
    src = pathlib.Path(__file__).resolve().parents[1] / "src/agent/agent.py"
    text = src.read_text()
    match = re.search(r'r"(<scratch>.*?\(\?:</scratch>\|\$\)\\s\*)"', text)
    assert match, "scratch regex pattern not found in agent.py"
    return re.compile(match.group(1), re.DOTALL | re.IGNORECASE)


def test_scratch_strip_handles_unclosed_tag():
    scratch_re = _load_scratch_re()
    text = "Here is your plan.\n<scratch>thinking about days... ran out of"
    assert scratch_re.sub("", text).strip() == "Here is your plan."


def test_scratch_strip_handles_closed_tag():
    scratch_re = _load_scratch_re()
    text = "<scratch>reasoning</scratch>Final answer."
    assert scratch_re.sub("", text).strip() == "Final answer."
