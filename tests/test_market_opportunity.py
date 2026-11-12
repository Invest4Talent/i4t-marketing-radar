"""Regression-tests voor inhoudelijke Keyword Planner-koppeling."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from market_opportunity import enrich_opportunities, load_market_signals


class MarketOpportunityTests(unittest.TestCase):
    def setUp(self):
        self.signals = load_market_signals()

    def make_item(self, title, topic="", category="sector", points=70):
        return {"title": title, "topic": topic, "category": category,
                "content_score": {"score": points, "basis": "geanalyseerde brontekst"}}

    def test_no_generic_jobbeurs_match(self):
        item = self.make_item("Succesvolle jobbeurs brengt werkgevers en werkzoekenden samen")
        enrich_opportunities([item], self.signals)
        self.assertNotIn("market_interest", item)
        self.assertNotIn("combined_score", item)

    def test_concrete_interim_match(self):
        item = self.make_item("Uitzendactiviteit daalt op jaarbasis")
        enrich_opportunities([item], self.signals, {"interimwerk": 80})
        self.assertEqual(item["market_interest"]["theme"], "interim-jobs")
        self.assertEqual(item["market_interest"]["basis"], "90% Keyword Planner / 10% Search Console")
        self.assertEqual(item["combined_score"], round(.75 * 70 + .25 * item["market_interest"]["score"]))

    def test_no_double_count_and_preserve_ai_without_match(self):
        item = self.make_item("Jobwissel: is het tijd voor een nieuwe job?")
        enrich_opportunities([item], self.signals)
        self.assertNotIn("market_interest", item)
        self.assertEqual(item["content_score"]["score"], 70)

    def test_flexi_blog_uses_topic(self):
        item = self.make_item("Blog met oude jaartallen", "Actualiseer flexi-jobs voor 2026",
                              category="blog")
        enrich_opportunities([item], self.signals)
        self.assertIn("market_interest", item)
        self.assertEqual(item["market_interest"]["theme"], "flexi-jobs")


if __name__ == "__main__":
    unittest.main()
