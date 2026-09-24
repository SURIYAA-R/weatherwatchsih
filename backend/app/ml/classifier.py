"""
Event Classifier — Rule-based NLP keyword classifier.

Maps free-text weather report descriptions to one of the recognised
event categories with a 0–1 confidence score.

Design: deterministic, offline, no external API dependency.
"""
import re
from typing import Tuple

# Keyword sets per category (order matters: more specific first)
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "cyclone": [
        "cyclone", "hurricane", "typhoon", "storm surge", "landfall",
        "wind speed", "eye of storm", "depression", "low pressure"
    ],
    "flood": [
        "flood", "inundation", "waterlogged", "submerged", "overflow",
        "flash flood", "river breach", "dam burst", "heavy waterlogging"
    ],
    "heatwave": [
        "heatwave", "heat wave", "extreme heat", "scorching", "heat stroke",
        "temperature above 40", "temperature above 45", "heat index"
    ],
    "hailstorm": [
        "hail", "hailstorm", "hailstone", "ice pellet", "golf ball size"
    ],
    "thunderstorm": [
        "thunder", "thunderstorm", "lightning", "thunder and lightning",
        "squall", "gusty wind", "strong wind"
    ],
    "fog": [
        "fog", "foggy", "dense fog", "visibility zero", "low visibility",
        "smog", "haze"
    ],
    "drought": [
        "drought", "dry spell", "no rain", "water scarcity", "crop failure",
        "parched", "groundwater depleted"
    ],
    "rain": [
        "rain", "rainfall", "downpour", "drizzle", "heavy rain",
        "moderate rain", "showers", "precipitation", "cloudburst"
    ],
}

# Weight per keyword hit (first match gives base + bonus per extra hit)
BASE_CONFIDENCE = 0.60
PER_EXTRA_HIT = 0.08
MAX_CONFIDENCE = 0.97


def classify_event(text: str) -> Tuple[str, float]:
    """
    Returns (category, confidence) for the given free-text description.
    Falls back to ("unknown", 0.10) if nothing matches.
    """
    text_lower = text.lower()
    scores: dict[str, float] = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        hits = sum(1 for kw in keywords if re.search(r"\b" + re.escape(kw) + r"\b", text_lower))
        if hits > 0:
            conf = min(BASE_CONFIDENCE + (hits - 1) * PER_EXTRA_HIT, MAX_CONFIDENCE)
            scores[category] = conf

    if not scores:
        return "unknown", 0.10

    best = max(scores, key=lambda k: scores[k])
    return best, round(scores[best], 3)


def keyword_match_score(claimed_category: str, text: str) -> float:
    """
    Returns 0–1 score indicating how well the text matches the claimed category.
    Used in Step 2 of the credibility scoring pipeline.
    """
    classified, conf = classify_event(text)
    if classified == claimed_category:
        return conf
    # Partial credit if a related category matched
    related = {
        "flood": ["rain", "cyclone"],
        "cyclone": ["thunderstorm", "rain"],
        "thunderstorm": ["cyclone", "rain"],
        "rain": ["flood", "thunderstorm"],
        "heatwave": ["drought"],
        "drought": ["heatwave"],
        "fog": [],
        "hailstorm": ["thunderstorm"],
    }
    if classified in related.get(claimed_category, []):
        return conf * 0.5
    return 0.0
