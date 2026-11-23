"""Tests voor veilige toelating van algemene media in de radar."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from media_sources import (
    fetch_public_media_text, matches_source, relevant_media_title,
)


class MockResponse:
    status_code = 200

    def __init__(self, html, url="https://www.hrsquare.be/nl/artikel"):
        self.text = html
        self.url = url
        self.headers = {"Content-Type": "text/html; charset=utf-8"}

    def raise_for_status(self):
        return None


class MediaSourceTests(unittest.TestCase):
    def test_only_sector_relevant_titles(self):
        self.assertTrue(relevant_media_title("Personeelstekort bij Vlaamse werkgevers"))
        self.assertTrue(relevant_media_title("Bedrijf kondigt collectief ontslag aan"))
        self.assertFalse(relevant_media_title("De beste restaurants van dit weekend"))
        self.assertFalse(relevant_media_title("Voetbalclub wint belangrijke wedstrijd"))

    def test_only_allowed_publisher(self):
        self.assertTrue(matches_source("https://www.hrsquare.be/nl/artikel", "hrsquare.be"))
        self.assertFalse(matches_source("https://hrsquare.be.evil.test/artikel", "hrsquare.be"))
        self.assertFalse(matches_source("https://example.com/artikel", "hrsquare.be"))

    @patch("media_sources.trafilatura.extract")
    @patch("media_sources.requests.get")
    def test_paywall_rejected(self, get, extract):
        get.return_value = MockResponse(
            '<script type="application/ld+json">'
            '{"isAccessibleForFree": false}</script><article>Preview</article>')
        extract.return_value = "Arbeidsmarkt " * 120
        self.assertEqual(fetch_public_media_text("https://www.hrsquare.be/nl/artikel", "hrsquare.be"), "")
        extract.assert_not_called()

    @patch("media_sources.trafilatura.extract")
    @patch("media_sources.requests.get")
    def test_teaser_rejected(self, get, extract):
        get.return_value = MockResponse("<article>Een korte preview</article>")
        extract.return_value = "Dit is een teaser."
        self.assertEqual(fetch_public_media_text("https://www.hrsquare.be/nl/artikel", "hrsquare.be"), "")

    @patch("media_sources.trafilatura.extract")
    @patch("media_sources.requests.get")
    def test_valid_free_article(self, get, extract):
        get.return_value = MockResponse("<article>Volledige tekst</article>")
        extract.return_value = "De arbeidsmarkt in Vlaanderen verandert. " * 30
        self.assertTrue(fetch_public_media_text("https://www.hrsquare.be/nl/artikel", "hrsquare.be"))

    @patch("media_sources.requests.get")
    def test_redirect_to_other_domain_rejected(self, get):
        get.return_value = MockResponse("<article>Tekst</article>", "https://paid.example.com/artikel")
        self.assertEqual(fetch_public_media_text("https://www.hrsquare.be/nl/artikel", "hrsquare.be"), "")


if __name__ == "__main__":
    unittest.main()
