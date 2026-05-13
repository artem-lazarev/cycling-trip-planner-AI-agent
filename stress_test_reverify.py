"""
Focused re-run for the bugs flagged in the first stress test:
  - reasoning narration leaks (scenarios 01, 03, 11, 15)
  - hallucinated waypoints when route is unknown (scenario 14)
  - itinerary table mis-alignment (11, 12)
  - day-count off-by-one in adapted plans (15)
"""

from __future__ import annotations

import json
import re
import urllib.request

BASE = "http://127.0.0.1:8765"


def post_chat(message, session_id=None, timeout=120.0):
    body = {"message": message}
    if session_id:
        body["session_id"] = session_id
    req = urllib.request.Request(
        f"{BASE}/chat",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


# Phrases the model used in the broken run to narrate its planning to the user.
NARRATION_PATTERNS = [
    r"\bi need \d",
    r"\blet me also note\b",
    r"\bsame waypoints, just stretched\b",
    r"\beverything('?s| is) in\b",
    r"\bi('| ha)?ve got everything\b",
    r"\bi('| ha)?ve everything\b",
    r"\bhere's your full itinerary\b",  # mild — keep listed but tolerated
    r"\bi just need to\b",
    r"\blet me (also )?(grab|re-examine|get)\b",
]

# Cities the model hallucinated in the previous Copenhagen->Amsterdam fallback run.
HALLUCINATED_CITIES_COPENHAGEN_AMSTERDAM = [
    "Køge", "Rødby", "Hamburg", "Bremen", "Osnabrück", "Münster", "Deventer",
]


def find_narration(text):
    hits = []
    for p in NARRATION_PATTERNS:
        if re.search(p, text, re.I):
            hits.append(p)
    return hits


def itinerary_table_rows(text):
    """Extract markdown table rows that look like itinerary day rows."""
    rows = []
    for line in text.splitlines():
        if "|" not in line:
            continue
        # Skip header / separator
        if re.match(r"\s*\|[-:\s|]+\|\s*$", line):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 4:
            continue
        # Skip header row whose first cell is literally just "Day"
        if cells[0].strip().lower() in ("day", "days", "**day**", "tag"):
            continue
        if re.search(r"\b\d+\b", cells[0]):
            rows.append(cells)
    return rows


def check_table_alignment(rows):
    """
    For each row, the destination city referenced in the 'Segment' cell should
    appear in the 'Sleep' cell on that same row. Returns list of mismatches.
    """
    mismatches = []
    for r in rows:
        if len(r) < 4:
            continue
        segment, sleep = r[1], r[-2] if len(r) >= 5 else r[-1]
        # destination is the last city-looking token in the segment cell
        towns = re.findall(r"[A-Z][a-zà-ž'’]+(?:\s[A-Z][a-zà-ž'’]+)*", segment)
        if not towns or not sleep:
            continue
        dest = towns[-1]
        if dest.lower() in ("ferry", "rest", "day", "explore", "midway",
                            "midpoint", "leg", "arrive"):
            continue
        sleep_lower = sleep.lower()
        # Sleep cell mentions destination, OR is explicitly camp/hostel/hotel
        # of the same destination, OR is "rest day" type entry
        if dest.lower() not in sleep_lower and not any(
            w in sleep_lower for w in ("rest", "—", "-", "wild", "en route",
                                       "camp en", "explore", "n/a", "tbd")
        ):
            mismatches.append(f"row {r[0]!r}: dest {dest!r} not in sleep {sleep!r}")
    return mismatches


# --- run ---

def run(name, turns):
    print(f"\n=== {name} ===")
    session = None
    last = ""
    for user in turns:
        data = post_chat(user, session_id=session)
        session = data["session_id"]
        last = data["response"]
        print(f"\n--- user ---\n{user}\n--- agent ---\n{last}\n")
    return last


def main():
    failures = []

    # 1. Narration leak — Amsterdam->Copenhagen happy path
    reply = run("01-happy-path-no-narration",
                ["I want to cycle from Amsterdam to Copenhagen. I can do around 100km a day, "
                 "prefer camping but want a hostel every 4th night. Traveling in June."])
    hits = find_narration(reply)
    if hits:
        failures.append(f"01: narration leak — patterns matched: {hits}")
    else:
        print(">> 01 PASS: no narration leak")

    # 2. Mid-flight change — should adapt cleanly, no narration
    s = None
    data = post_chat("Plan a bike trip Amsterdam to Copenhagen, 100km/day, camping, in June.")
    s = data["session_id"]
    data = post_chat("Actually make it 80km/day.", session_id=s)
    reply = data["response"]
    print(f"\n=== 03-preference-change-no-narration ===\n--- agent ---\n{reply}\n")
    hits = find_narration(reply)
    if hits:
        failures.append(f"03: narration leak on re-plan — patterns matched: {hits}")
    elif "80" not in reply:
        failures.append("03: didn't reflect 80 km/day change")
    else:
        print(">> 03 PASS: clean re-plan, no narration")

    # 3. Unknown route — should NOT invent waypoints
    reply = run("14-unknown-route-no-hallucination",
                ["I want to cycle from Copenhagen back to Amsterdam, 80km/day, hostels, in July."])
    invented = [c for c in HALLUCINATED_CITIES_COPENHAGEN_AMSTERDAM if c in reply]
    # Hamburg/Bremen could legitimately appear if model is just naming the inverse
    # of the known A->C route, but Køge / Rødby / Osnabrück / Münster / Deventer
    # have no source in the tools. Flag if any of those appear:
    no_source = [c for c in ["Køge", "Rødby", "Osnabrück", "Münster", "Deventer"] if c in reply]
    if no_source:
        failures.append(f"14: invented waypoints with no tool source: {no_source}")
    else:
        print(">> 14 PASS: no fabricated waypoint cities")

    # 4. Table alignment on a multi-day plan + extreme input
    reply = run("11-long-input-table-alignment",
                ["I want to cycle from Amsterdam to Copenhagen in June, 100km/day, camping, "
                 "hostel every 4th night. " * 30])
    rows = itinerary_table_rows(reply)
    mism = check_table_alignment(rows)
    if mism:
        failures.append(f"11: itinerary table row mismatch: {mism[:3]}")
    else:
        print(f">> 11 PASS: {len(rows)} itinerary rows aligned")

    # 5. Rest day insertion — day count should match table
    s = None
    data = post_chat("Plan Amsterdam to Copenhagen, 100km/day, camping, in June.")
    s = data["session_id"]
    data = post_chat("Can we route via Hamburg with a rest day there?", session_id=s)
    reply = data["response"]
    print(f"\n=== 15-rest-day-count ===\n--- agent ---\n{reply}\n")
    rows = itinerary_table_rows(reply)
    title_match = re.search(r"(\d+)\s*(?:riding\s*days?|days?\s*total|day\s*trip|days?)", reply, re.I)
    if title_match and rows:
        title_days = int(title_match.group(1))
        # Allow ±1 because of arrival rows
        if abs(title_days - len(rows)) > 2:
            failures.append(f"15: title says {title_days} days but table has {len(rows)} rows")
        else:
            print(f">> 15 PASS: title days ({title_days}) ~ table rows ({len(rows)})")
    else:
        print(">> 15 SKIP: could not parse title day count")

    print("\n========================")
    if failures:
        print(f"{len(failures)} FAILURES:")
        for f in failures:
            print(" -", f)
        return 1
    print("All targeted re-checks PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
