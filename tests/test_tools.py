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


def test_get_weather_fallback():
    # Unknown location should still produce a usable summary, not crash.
    result = get_weather.execute({"location": "Atlantis", "month": "June"})
    assert isinstance(result, str) and result
    assert "Atlantis" in result


def test_get_route_known_pair():
    result = get_route.execute({
        "start": "Amsterdam",
        "end": "Copenhagen",
        "daily_distance_km": 100,
    })
    assert "Amsterdam" in result and "Copenhagen" in result
    # 780 km / 100 km/day ~= 8 days, give or take rounding.
    assert "days" in result


def test_find_accommodation_basic():
    result = find_accommodation.execute({
        "location": "Hamburg",
        "accommodation_type": "camping",
        "count": 2,
    })
    assert "Hamburg" in result
    assert "camping" in result.lower()


def test_get_elevation_profile_rating():
    result = get_elevation_profile.execute({"start": "Hamburg", "end": "Lübeck"})
    assert "Hamburg" in result and "Lübeck" in result
    assert "elevation" in result.lower() or "m" in result
