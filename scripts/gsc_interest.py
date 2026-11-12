"""Lees geaggregeerde Search Console-zichtbaarheid zonder zoekopdrachten te publiceren.

GSC toont alleen zoekopdrachten waarvoor go4jobs.be al vertoningen had.
De themasignalen zijn daarom géén algemeen zoekvolume.
"""
import datetime as dt
import json
import math
import os
import re
from pathlib import Path

import google.auth
from google.auth.transport.requests import AuthorizedSession

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".gsc-signals.json"
SITE = os.getenv("GSC_SITE_URL", "sc-domain:go4jobs.be")
SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"

# Beperkte inhoudelijke thema's, geen individuele zoekopdrachten in de output.
THEMES = {
    "flexi-jobs": r"\bflexi[ -]?jobs?\b|\bflexijob",
    "interimwerk": r"\binterim\b|\buitzend",
    "solliciteren": r"\bsollicit|\bsolliciteren",
    "cv": r"\bcv\b|\bcurriculum vitae\b",
    "heftruck": r"\bheftruck|\breachtruck",
    "magazijn en logistiek": r"\bmagazijn|\blogistiek|\borderpick",
    "productie": r"\bproductie|\boperator\b",
    "studentenjobs": r"\bstudentenjob|\bjobstudent|\bstudentenarbeid",
    "loon": r"\bloon\b|\bbrutoloon\b|\bnettoloon\b",
    "werkloosheid": r"\bwerkloos|\bwerkzoekend",
}
PATTERNS = {name: re.compile(pattern, re.I) for name, pattern in THEMES.items()}


def fetch_signals():
    credentials, _ = google.auth.default(scopes=[SCOPE])
    session = AuthorizedSession(credentials)
    # Search Console-gegevens hebben doorgaans enkele dagen verwerkingsvertraging.
    end = dt.date.today() - dt.timedelta(days=3)
    start = end - dt.timedelta(days=27)
    url = ("https://searchconsole.googleapis.com/webmasters/v3/sites/"
           + __import__("urllib.parse", fromlist=["quote"]).quote(SITE, safe="")
           + "/searchAnalytics/query")
    response = session.post(url, json={
        "startDate": start.isoformat(), "endDate": end.isoformat(),
        "dimensions": ["query"], "rowLimit": 25000, "startRow": 0,
        "dataState": "final",
    }, timeout=40)
    response.raise_for_status()
    totals = {topic: {"impressions": 0, "queries": 0} for topic in THEMES}
    for row in response.json().get("rows", []):
        query = str((row.get("keys") or [""])[0]).lower()
        impressions = max(0, int(row.get("impressions", 0)))
        if not query or not impressions:
            continue
        for topic, pattern in PATTERNS.items():
            if pattern.search(query):
                totals[topic]["impressions"] += impressions
                totals[topic]["queries"] += 1
    # Minimaal 3 verschillende queryrijen én 100 vertoningen per thema
    # om kleine, mogelijk identificeerbare clusters niet te tonen.
    signals = {}
    for topic, data in totals.items():
        if data["queries"] >= 3 and data["impressions"] >= 100:
            # Signaal is relatieve bestaande zichtbaarheid, geen zoekvolume.
            signals[topic] = min(100, round(100 * math.log1p(data["impressions"]) /
                                            math.log1p(3000)))
    return {"period": [start.isoformat(), end.isoformat()],
            "site": SITE, "topics": signals,
            "source": "Google Search Console: bestaande organische zichtbaarheid"}


def main():
    result = fetch_signals()
    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print("GSC: signalen voor", len(result["topics"]), "thema's opgehaald;",
          "geen individuele zoekopdrachten opgeslagen.")


if __name__ == "__main__":
    main()
