"""Combineer redactionele AI-score met optionele organische GSC-zichtbaarheid.

GSC registreert bestaande zichtbaarheid op go4jobs.be, geen totaal
zoekvolume en geen bewijs dat het thema bij concurrenten niet speelt.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GSC_FILE = ROOT / ".gsc-signals.json"

# Match alleen concrete woorden in de titel; geen verborgen inferentie uit brede samenvattingen.
THEME_PATTERNS = {
    "flexi-jobs": r"\bflexi[ -]?jobs?\b|\bflexijob",
    "interimwerk": r"\binterim\b|\buitzend",
    "solliciteren": r"\bsollicit",
    "cv": r"\bcv\b|\bcurriculum vitae\b",
    "heftruck": r"\bheftruck|\breachtruck",
    "magazijn en logistiek": r"\bmagazijn|\blogistiek|\borderpick",
    "productie": r"\bproductie|\boperator\b",
    "studentenjobs": r"\bstudentenjob|\bjobstudent|\bstudentenarbeid",
    "loon": r"\bloon\b|\bbrutoloon\b|\bnettoloon\b",
    "werkloosheid": r"\bwerkloos|\bwerkzoekend",
}
PATTERNS = {key: re.compile(pattern, re.I) for key, pattern in THEME_PATTERNS.items()}


def load_signals():
    if not GSC_FILE.exists():
        print("GSC-contentkans: geen signaalbestand; gebruik originele AI-scores.")
        return {}
    try:
        data = json.loads(GSC_FILE.read_text(encoding="utf-8"))
        if data.get("site") != "sc-domain:go4jobs.be":
            raise ValueError("onverwachte Search Console-property")
        topics = data.get("topics", {})
        return {key: max(0, min(100, int(value))) for key, value in topics.items()
                if key in PATTERNS and isinstance(value, (int, float))
                and not isinstance(value, bool)}
    except (ValueError, TypeError, OSError) as exc:
        print("GSC-contentkans: signalen ongeldig; originele AI-score blijft behouden:", str(exc)[:90])
        return {}


def enrich_opportunities(items, topic_signals):
    """Reken per workflowrun opnieuw, zonder ooit de AI-bronscore te overschrijven."""
    found = 0
    for item in items:
        item.pop("search_visibility", None)
        item.pop("combined_score", None)
        editorial = item.get("content_score")
        if not isinstance(editorial, dict) or not isinstance(editorial.get("score"), (int, float)):
            continue
        title = str(item.get("title", ""))
        matches = sorted((theme, topic_signals[theme]) for theme, pattern in PATTERNS.items()
                         if theme in topic_signals and pattern.search(title))
        if not matches:
            continue
        # Hoogste themawaarde voorkomt dubbel tellen van één zoekopdracht bij meerdere thema's.
        topic, visibility = max(matches, key=lambda pair: pair[1])
        ai_score = max(0, min(100, int(editorial["score"])))
        combined = round(0.65 * ai_score + 0.35 * visibility)
        # Scores op basis van alleen een kop blijven voorlopig (max. 45).
        if editorial.get("basis") == "alleen kop":
            combined = min(45, combined)
        item["combined_score"] = combined
        item["search_visibility"] = {
            "theme": topic,
            "score": visibility,
            "interpretation": "relatieve organische zichtbaarheid op go4jobs.be; geen totaal zoekvolume",
        }
        found += 1
    print("GSC-contentkans:", found, "artikels met een herkenbaar titelthema.")
