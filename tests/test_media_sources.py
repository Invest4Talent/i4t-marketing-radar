"""Tests voor veilige toelating van algemene media in de radar."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from media_sources import (
    fetch_public_media_text, matches_source, relevant_media_title,
    relevant_media_article,
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

    def test_public_sector_personnel_excluded(self):
        self.assertFalse(relevant_media_article(
            'Brugge schrapt 81 jobs bij stadspersoneel en 16 jobs bij OCMW'))
        self.assertFalse(relevant_media_article(
            'Politiezone Rode kampt met zwaar personeelstekort: 20 inspecteurs te weinig'))
        self.assertFalse(relevant_media_article(
            'Kortrijk schrapt 120 jobs en bespaart 50 miljoen euro: geen extra belastingen'))

    def test_commercial_and_marketwide_stories_kept(self):
        self.assertTrue(relevant_media_article(
            'Weinig animo voor flexi-jobs in nieuwe sectoren'))
        self.assertTrue(relevant_media_article(
            'Aantal vacatures op laagste niveau in tien jaar tijd'))
        self.assertTrue(relevant_media_article(
            'Limburgse bedrijven nemen ontslagen werknemers over van Vynova'))
        self.assertTrue(relevant_media_article(
            'Vynova ontslaat werknemers', 'Het chemiebedrijf sluit een productielijn.'))
        self.assertTrue(relevant_media_article(
            'Nieuwe arbeidsmarktmaatregelen voor werkgevers'))
        self.assertFalse(relevant_media_article(
            'Voetbalteam ontslaat trainer'))

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
