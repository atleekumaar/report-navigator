"""
question_parser.py — Parse natural-language questions into structured queries.

This module maps free-text questions about road-accident statistics into a
canonical ``ParsedQuestion`` with entity, metric, and context fields so the
solver can do a direct table lookup.

No LLM is needed — we rely on keyword patterns that generalise across years.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


# ---------------------------------------------------------------------------
# Parsed result
# ---------------------------------------------------------------------------

@dataclass
class ParsedQuestion:
    """Machine-readable representation of a statistical question."""
    raw: str
    entity: str = ""             # city / state / category name
    entity_type: str = ""        # "city", "state", "national", "category"
    metric: str = ""             # "killed", "injured", "accidents"
    sub_category: str = ""       # e.g. "pedestrian", "two-wheeler", "over-speeding"
    year: str = "2023"
    is_unanswerable: bool = False
    table_types: List[str] = field(default_factory=list)  # candidate table types to query


# ---------------------------------------------------------------------------
# City / State lists (for entity resolution — enriched at runtime from PDF)
# ---------------------------------------------------------------------------

# Known million-plus cities in India (lowercased)
_KNOWN_CITIES = {
    "agra", "ahmedabad", "allahabad", "prayagraj", "amritsar", "asansol",
    "durgapur", "aurangabad", "bengaluru", "bangalore", "bhopal", "chennai",
    "coimbatore", "delhi", "dhanbad", "durg", "bhilai", "faridabad",
    "ghaziabad", "gwalior", "hyderabad", "indore", "jabalpur", "jaipur",
    "jamshedpur", "jodhpur", "kanpur", "kochi", "kollam", "kolkata",
    "kozhikode", "lucknow", "ludhiana", "madurai", "malappuram",
    "meerut", "mumbai", "nagpur", "nashik", "patna", "pune", "raipur",
    "rajkot", "ranchi", "salem", "srinagar", "surat", "thiruvananthapuram",
    "tiruchirappalli", "tiruchirapalli", "tiruppur", "vadodara", "vadodra",
    "varanasi", "vasai", "virar", "vijayawada", "vijaywada",
    "visakhapatnam", "vizag",
}

_KNOWN_STATES = {
    "andhra pradesh", "arunachal pradesh", "assam", "bihar", "chhattisgarh",
    "goa", "gujarat", "haryana", "himachal pradesh", "jharkhand",
    "karnataka", "kerala", "madhya pradesh", "maharashtra", "manipur",
    "meghalaya", "mizoram", "nagaland", "odisha", "punjab", "rajasthan",
    "sikkim", "tamil nadu", "telangana", "tripura", "uttar pradesh",
    "uttarakhand", "west bengal",
    "andaman", "chandigarh", "dadra", "nagar haveli", "daman", "diu",
    "delhi", "jammu", "kashmir", "ladakh", "lakshadweep", "puducherry",
}


# ---------------------------------------------------------------------------
# Sub-category keywords
# ---------------------------------------------------------------------------

_SUB_CAT_MAP = {
    "pedestrian":       "pedestrian",
    "pedestrians":      "pedestrian",
    "two-wheeler":      "two-wheeler",
    "two wheeler":      "two-wheeler",
    "two-wheelers":     "two-wheeler",
    "two wheelers":     "two-wheeler",
    "bicycle":          "bicycle",
    "bicycles":         "bicycle",
    "car":              "car",
    "cars":             "car",
    "taxi":             "car",
    "taxis":            "car",
    "vans":             "car",
    "lmvs":             "car",
    "bus":              "bus",
    "buses":            "bus",
    "truck":            "truck",
    "trucks":           "truck",
    "auto-rickshaw":    "auto-rickshaw",
    "auto rickshaw":    "auto-rickshaw",
    "over-speeding":    "over-speeding",
    "overspeeding":     "over-speeding",
    "drunken":          "drunken-driving",
    "drunken driving":  "drunken-driving",
    "drunk":            "drunken-driving",
    "wrong side":       "wrong-side",
    "hit and run":      "hit-and-run",
    "hit-and-run":      "hit-and-run",
    "run off road":     "run-off-road",
    "head on":          "head-on",
    "head-on":          "head-on",
    "others":           "others",
}


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse_question(question: str) -> ParsedQuestion:
    """Parse a free-text question into a structured query."""
    q = question.strip()
    ql = q.lower()
    pq = ParsedQuestion(raw=q)

    # ---- year ----
    m = re.search(r'\b(20\d{2})\b', q)
    pq.year = m.group(1) if m else "2023"

    # ---- metric ----
    if re.search(r'\bkilled\b|\bdeaths?\b|\bfatalit', ql):
        pq.metric = "killed"
    elif re.search(r'\binjured\b|\binjur', ql):
        pq.metric = "injured"
    elif re.search(r'\baccidents?\b|\breported\b|\boccurred\b', ql):
        pq.metric = "accidents"
    else:
        pq.metric = "killed"  # default for road-accident reports

    # ---- sub-category ----
    for phrase, cat in sorted(_SUB_CAT_MAP.items(), key=lambda x: -len(x[0])):
        if phrase in ql:
            pq.sub_category = cat
            break

    # ---- entity extraction ----
    # Strategy: check known cities/states, then fall back to NER-like heuristics

    # Check for city names
    found_city = ""
    for city in sorted(_KNOWN_CITIES, key=len, reverse=True):
        if city in ql:
            found_city = city
            break

    # Check for state names
    found_state = ""
    for state in sorted(_KNOWN_STATES, key=len, reverse=True):
        if state in ql:
            found_state = state
            break

    # Check for "all India" / national-level
    is_national = bool(re.search(r'\ball[\s\-]?india\b|\bnational\b|\bcountry\b', ql))

    # Decide entity type
    if "million" in ql and "plus" in ql and found_city:
        pq.entity = found_city
        pq.entity_type = "city"
    elif found_city and not found_state:
        pq.entity = found_city
        pq.entity_type = "city"
    elif found_state and not found_city:
        pq.entity = found_state
        pq.entity_type = "state"
    elif found_city and found_state:
        # "city" if question says "city" explicitly or "million"
        if "city" in ql or "million" in ql:
            pq.entity = found_city
            pq.entity_type = "city"
        else:
            # Prefer the longer match
            pq.entity = found_city if len(found_city) >= len(found_state) else found_state
            pq.entity_type = "city" if pq.entity == found_city else "state"
    elif is_national:
        pq.entity = "India"
        pq.entity_type = "national"
    else:
        # Try to extract entity from the question via NER patterns
        # "in <Entity> in 2023" or "in <Entity> city"
        m = re.search(r'\bin\s+([A-Z][a-zA-Z\s&\(\)]+?)(?:\s+(?:city|state|in|during|(?:20\d{2})))', q)
        if m:
            ent = m.group(1).strip().rstrip('()')
            pq.entity = ent.lower()
            # Guess type
            if any(c in ent.lower() for c in _KNOWN_CITIES):
                pq.entity_type = "city"
            elif any(s in ent.lower() for s in _KNOWN_STATES):
                pq.entity_type = "state"
            else:
                pq.entity_type = "city"  # default guess

    # ---- determine candidate table types ----
    if pq.entity_type == "city":
        if pq.sub_category in ("pedestrian", "two-wheeler", "bicycle"):
            pq.table_types = ["city_road_users", "city_summary"]
        elif pq.sub_category in ("over-speeding", "drunken-driving", "wrong-side"):
            pq.table_types = ["city_violations", "city_summary"]
        else:
            pq.table_types = ["city_summary", "city_road_users", "city_violations"]
    elif pq.entity_type == "state":
        if pq.metric == "killed":
            pq.table_types = ["state_killed", "state_accidents"]
        elif pq.metric == "accidents":
            pq.table_types = ["state_accidents", "state_killed"]
        elif pq.metric == "injured":
            pq.table_types = ["state_injured", "state_accidents"]
        else:
            pq.table_types = ["state_killed", "state_accidents", "state_injured"]
    elif pq.entity_type == "national":
        if pq.sub_category in ("over-speeding", "drunken-driving", "wrong-side"):
            pq.table_types = ["violation_national"]
        elif pq.sub_category in ("pedestrian", "two-wheeler", "bicycle", "car", "bus", "truck"):
            pq.table_types = ["road_user_national"]
        elif pq.sub_category in ("hit-and-run", "run-off-road", "head-on", "others"):
            pq.table_types = ["collision_type"]
        else:
            pq.table_types = ["violation_national", "road_user_national", "collision_type"]
    else:
        # Unknown — try everything
        pq.table_types = [
            "city_summary", "state_killed", "state_accidents",
            "violation_national", "road_user_national", "collision_type",
            "city_road_users", "city_violations",
        ]

    # ---- unanswerable heuristics ----
    # Entities not in any known list and not parseable → might be unanswerable
    if not pq.entity and not is_national:
        pq.is_unanswerable = True

    return pq

