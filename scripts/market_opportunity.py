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

# Alleen duidelijke overeenkomsten tussen zoekintentie en artikelonderwerp.
THEME_PATTERNS = {
    "flexi-jobs": r"\bflexi[ -]?jobs?\b|\bflexijob",
    "flexi-regels": r"\bflexi[ -]?job.{0,35}(?:voorwaard|regel|wetgev)",
    "flexi-gepensioneerden": r"(?:flexi[ -]?job.{0,35}gepensioneerd|gepensioneerd.{0,35}flexi)",
    "flexi-weekend": r"flexi[ -]?job.{0,35}weekend",
    "flexi-sectoren": r"flexi[ -]?job.{0,35}sector",
    "flexi-chauffeur": r"flexi[ -]?job.{0,35}chauffeur",
    "flexi-administratie": r"flexi[ -]?job.{0,35}administrat",
    "flexi-zorg": r"flexi[ -]?job.{0,35}zorg",
    "interimkantoren": r"\binterimkantoor|\buitzendkantoor|\binterimbureau",
    "interim-jobs": r"\binterim\b|\buitzend",
    "solliciteren": r"\bsollicit",
    "sollicitatiebrief": r"\bsollicitatiebrief|\bmotivatiebrief",
    "cv-maken": r"\bcv maken|\bcurriculum vitae opstellen",
    "cv-voorbeeld": r"\bcv voorbeeld|\bvoorbeeld cv",
    "heftruck": r"\bheftruck|\breachtruck",
    "magazijnier": r"\bmagazijnier|\bmagazijnmedewerker",
    "logistieke-jobs": r"\blogistieke? (?:job|medewerker|vacatur)|\bjob.{0,12}logistiek",
    "productiejobs": r"\bproductie|\bproductiemedewerk",
    "operator": r"\boperator\b|\bprocesoperator",
    "studentenjobs": r"\bstudentenjob|\bjobstudent",
    "winkeljobs": r"\bwinkelmedewerker|\bwinkelbediende",
    "schoonmaakjobs": r"\bschoonmaakvacatur|\bvacatur.{0,15}schoonmaak",
    "thuiswerkjobs": r"\bthuiswerkvacatur|\bvacatur.{0,15}thuiswerk",
    "personeel-zoeken": r"\bpersoneel (?:gezocht|zoeken)|\b(?:zoek|zoeken) personeel",
}
PATTERNS = {key: re.compile(pattern, re.I) for key, pattern in THEME_PATTERNS.items()}
GSC_THEME = {
    "flexi-jobs": "flexi-jobs", "flexi-regels": "flexi-jobs",
    "flexi-gepensioneerden": "flexi-jobs", "flexi-weekend": "flexi-jobs",
    "flexi-sectoren": "flexi-jobs", "flexi-chauffeur": "flexi-jobs",
    "flexi-administratie": "flexi-jobs", "flexi-zorg": "flexi-jobs",
    "interimkantoren": "interimwerk", "interim-jobs": "interimwerk",
    "solliciteren": "solliciteren", "sollicitatiebrief": "solliciteren",
    "cv-maken": "cv", "cv-voorbeeld": "cv",
    "heftruck": "heftruck", "magazijnier": "magazijn en logistiek",
    "logistieke-jobs": "magazijn en logistiek",
    "productiejobs": "productie", "operator": "productie",
    "studentenjobs": "studentenjobs",
}
AI_WEIGHT = 0.75
GOOGLE_WEIGHT = 0.25
MARKET_WITHIN_GOOGLE = 0.90
GSC_WITHIN_GOOGLE = 0.10
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


def enrich_opportunities(items, market_signals, search_console_signals=None):
    """Gebruik alleen een expliciete titelmatch; zonder match blijft de AI-score bestaan."""
    found = 0
    search_console_signals = search_console_signals or {}
    for item in items:
        # Vorige GSC-gecombineerde scores en afgeleide data vervangen.
        item.pop("combined_score", None)
        item.pop("search_visibility", None)
        item.pop("market_interest", None)
        score = item.get("content_score")
        if not isinstance(score, dict) or not isinstance(score.get("score"), (int, float)):
            continue
        title = str(item.get("title", ""))
        if item.get("category") == "blog":
            title += " " + str(item.get("topic", ""))
        matches = [(topic, market_signals[topic]) for topic, pattern in PATTERNS.items()
                   if topic in market_signals and pattern.search(title)]
        if not matches:
            continue
        # Bij meerdere thema's gebruiken we de sterkste gemeten match; niet optellen.
        topic, measure = max(matches, key=lambda match: match[1]["volume"])
        ai = max(0, min(100, int(score["score"])))
        gsc = search_console_signals.get(GSC_THEME.get(topic))
        # Eigen GSC-zichtbaarheid weegt slechts beperkt mee in de Google-score.
        google_score = (round(MARKET_WITHIN_GOOGLE * measure["score"] +
                              GSC_WITHIN_GOOGLE * gsc) if isinstance(gsc, (int, float))
                        else measure["score"])
        combined = round(AI_WEIGHT * ai + GOOGLE_WEIGHT * google_score)
        if score.get("basis") == "alleen kop":
            combined = min(45, combined)
        item["combined_score"] = combined
        item["market_interest"] = {
            "theme": topic,
            "score": google_score,
            "avg_monthly_searches": measure["volume"],
            "keyword": measure["keyword"],
            "scope": "Vlaanderen, Nederlands, Google, nov 2025–okt 2026",
            "basis": ("90% Keyword Planner / 10% Search Console" if isinstance(gsc, (int, float))
                      else "100% Keyword Planner"),
            "market_score": measure["score"],
        }
        found += 1
    print("Marktbrede Google-score:", found, "artikels met een onderbouwde titelmatch.")
