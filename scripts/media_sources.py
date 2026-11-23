"""Veilige selectie van vrij leesbare, sectorrelevante media-artikels.

Google News-zoekresultaten zijn slechts kandidaten. Alleen echt bereikbare
artikels met voldoende eigen, publieke artikeltekst komen in de radar.
"""
import re
from urllib.parse import urlparse

import requests
import trafilatura

# Nieuwsbronnen worden met site:-queries benaderd; Google News-link wordt
# eerst naar het oorspronkelijke artikel gedecodeerd en gecontroleerd.
MEDIA_SOURCES = (
    ("VRT NWS", "vrt.be", "site:vrt.be/vrtnws/nl (arbeidsmarkt OR ontslagen OR werkgelegenheid OR personeelstekort OR flexijobs OR uitzendsector)"),
    ("HLN", "hln.be", "site:hln.be (arbeidsmarkt OR ontslagen OR jobs OR personeelstekort OR uitzendkantoor)"),
    ("De Tijd", "tijd.be", "site:tijd.be (arbeidsmarkt OR personeelstekort OR uitzendarbeid OR ontslagen OR werkgelegenheid)"),
    ("Trends / Kanaal Z", "trends.be", "site:trends.be (arbeidsmarkt OR rekrutering OR ontslagen OR werkgelegenheid OR flexijobs)"),
    ("Made in", "made-in.be", "site:made-in.be (jobs OR personeel OR fabriek OR ontslagen OR rekrutering OR logistiek)"),
    ("HR Square", "hrsquare.be", "site:hrsquare.be/nl (arbeidsmarkt OR vacatures OR rekrutering OR aanwerving OR uitzendarbeid)"),
)
# Een uitdrukkelijke arbeidsmarkt-link: niet alleen de algemene woorden 'werk'
# of 'bedrijf', die vaak over sport, entertainment en consumenten gaan.
SECTOR_RE = re.compile(
    r"\b(?:arbeidsmarkt|uitzend(?:sector|werk|arbeid|kantoor|bureau)|interim|"
    r"flexi[ -]?job|rekrut|aanwerv|personeelstekort|personeelskosten|"
    r"werknemer|werkzoekend|werkgelegenheid|jobcreatie|jobs? (?:verdwijn|schrap|"
    r"creëer|creeer|op de helling)|ontslag|ontslagen|vacatur|"
    r"loon(?:kosten|massa|index)?|staking|herstructurer|fabriekssluiting|"
    r"productie(?:personeel|jobs|vacatures)|logistiek(?:e)? (?:jobs|personeel))",
    re.I,
)
PAYWALL_RE = re.compile(
    r'"isAccessibleForFree"\s*:\s*(?:"false"|false)|'
    r'<meta[^>]+(?:name|property)\s*=\s*["\'](?:article:content_tier|'
    r'content_tier|paywall)["\'][^>]+content\s*=\s*["\'](?:premium|paid|metered|locked)',
    re.I,
)
LOGIN_RE = re.compile(
    r"\b(?:abonneer je om dit artikel te lezen|enkel voor abonnees|"
    r"dit artikel is enkel beschikbaar voor abonnees|"
    r"lees verder met een abonnement|meld je aan om verder te lezen)\b",
    re.I,
)
MAX_MEDIA_PER_SOURCE = 3
MAX_MEDIA_TOTAL = 12


def matches_source(url, expected_domain):
    host = (urlparse(url).hostname or "").lower().rstrip(".")
    return host == expected_domain or host.endswith("." + expected_domain)


def relevant_media_title(title):
    return bool(SECTOR_RE.search(title))


def fetch_public_media_text(url, domain, timeout=14):
    """Geen login, betaalmuur of tekstfragmenten als volledig artikel beschouwen."""
    if urlparse(url).scheme not in ("https", "http"):
        return ""
    if not matches_source(url, domain):
        return ""
    try:
        response = requests.get(url, timeout=timeout, headers={
            "User-Agent": "Mozilla/5.0 (compatible; Go4JobsMarketingRadar/2.0)"
        })
        response.raise_for_status()
        if not matches_source(response.url, domain):
            return ""
        if "html" not in response.headers.get("Content-Type", "").lower():
            return ""
        page = response.text
        if PAYWALL_RE.search(page):
            return ""
        extracted = trafilatura.extract(
            page, include_comments=False, include_tables=False,
            favor_precision=True
        )
        content = re.sub(r"\s+", " ", extracted or "").strip()
        # Minimaal een volwaardig artikel en niet enkel een teaser.
        if len(content) < 750 or LOGIN_RE.search(content[:500]):
            return ""
        if len(content.split()) < 120:
            return ""
        return content[:10000]
    except (requests.RequestException, ValueError):
        return ""
