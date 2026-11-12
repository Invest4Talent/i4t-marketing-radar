"""Voorlopige marktbrede Google-score op basis van Keyword Planner-export.

Niet verwarren met Search Console: hier meten we geen Go4Jobs-vertoningen.
Deze score is relatief binnen een beperkte themaselectie en geen SEO-ranking.
"""
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKET_FILE = ROOT / "keyword-market-signals.json"

THEME_PATTERNS = {
    "flexi-jobs": r"\\bflexi[ -]?jobs?\\b|\\bflexijob",
    "interimwerk": r"\\binterim\\b|\\buitzend",
    "solliciteren": r"\\bsollicit",
    "cv": r"\\bcv\\b|\\bcurriculum vitae\\b",
    "heftruck": r"\\bheftruck|\\breachtruck",
    "magazijn en logistiek": r"\\bmagazijn|\\blogistiek|\\borderpick",
    "productie": r"\\bproductie|\\boperator\\b",
    "studentenjobs": r"\\bstudentenjob|\\bjobstudent|\\bstudentenarbeid",
}
PATTERNS = {key: re.compile(pattern, re.I) for key, pattern in THEME_PATTERNS.items()}
AI_WEIGHT = 0.80
MARKET_WEIGHT = 0.20
MIN_VOLUME = 100
# In het eerste experiment is 'flexi job' de hoogste werkelijke steekproefwaarde.
# Lognormalisatie beperkt de dominantie van één heel grote zoekterm.
REFERENCE_MAX_VOLUME = 49500
REFERENCE_MIN_VOLUME = 20


def volume_score(volume):
    if volume < MIN_VOLUME:
        return None
    low = math.log1p(REFERENCE_MIN_VOLUME)
    high = math.log1p(REFERENCE_MAX_VOLUME)
    return max(0, min(100, round(100 * (math.log1p(volume) - low) / (high - low))))


def load_market_signals():
    try:
        document = json.loads(MARKET_FILE.read_text(encoding="utf-8"))
        if (document.get("region") != "Vlaanderen, België"
                or document.get("language") != "Nederlands"):
            raise ValueError("verkeerde doelgroep in Keyword Planner-export")
        signals = {}
        for topic, entry in document.get("topics", {}).items():
            if topic not in PATTERNS or not isinstance(entry, dict):
                continue
            volume = entry.get("avg_monthly_searches")
            if not isinstance(volume, int) or isinstance(volume, bool):
                continue
            points = volume_score(volume)
            if points is not None:
                signals[topic] = {"score": points, "volume": volume,
                                  "keyword": str(entry.get("keyword", ""))[:80]}
        print("Keyword Planner:", len(signals), "thema's met voldoende zoekdata.")
        return signals
    except (OSError, ValueError, TypeError) as error:
        print("Keyword Planner niet beschikbaar; gebruik de originele AI-scores:", str(error)[:100])
        return {}


def enrich_opportunities(items, market_signals):
    """Gebruik alleen een expliciete titelmatch; zonder match blijft de AI-score bestaan."""
    found = 0
    for item in items:
        # Vorige GSC-gecombineerde scores en afgeleide data vervangen.
        item.pop("combined_score", None)
        item.pop("search_visibility", None)
        item.pop("market_interest", None)
        score = item.get("content_score")
        if not isinstance(score, dict) or not isinstance(score.get("score"), (int, float)):
            continue
        title = str(item.get("title", ""))
        matches = [(topic, market_signals[topic]) for topic, pattern in PATTERNS.items()
                   if topic in market_signals and pattern.search(title)]
        if not matches:
            continue
        # Bij meerdere thema's gebruiken we de sterkste gemeten match; niet optellen.
        topic, measure = max(matches, key=lambda match: match[1]["volume"])
        ai = max(0, min(100, int(score["score"])))
        combined = round(AI_WEIGHT * ai + MARKET_WEIGHT * measure["score"])
        if score.get("basis") == "alleen kop":
            combined = min(45, combined)
        item["combined_score"] = combined
        item["market_interest"] = {
            "theme": topic,
            "score": measure["score"],
            "avg_monthly_searches": measure["volume"],
            "keyword": measure["keyword"],
            "scope": "Vlaanderen, Nederlands, Google, nov 2025–okt 2026",
            "basis": "Keyword Planner-marktschatting; geen Go4Jobs-vertoningen",
        }
        found += 1
    print("Marktbrede Google-score:", found, "artikels met een onderbouwde titelmatch.")
