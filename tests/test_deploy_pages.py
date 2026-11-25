"""Controleer artifacts en API-veiligheidsregels zonder echte GitHub-aanroepen."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from deploy_pages import find_artifact


class PagesDeploymentTests(unittest.TestCase):
    @patch("deploy_pages.api")
    def test_uses_verified_current_run_artifact(self, api):
        api.return_value = {"artifacts": [
            {"id": 14909660476, "name": "github-pages",
             "expired": False, "workflow_run": {"id": 1234}},
        ]}
        self.assertEqual(find_artifact("https://api.github.com", "test/repo", "1234", "token"),
                         14909660476)

    @patch("deploy_pages.time.sleep")
    @patch("deploy_pages.api")
    def test_retries_until_artifact_is_registered(self, api, sleep):
        api.side_effect = [
            {"artifacts": []},
            {"artifacts": []},
            {"artifacts": [
                {"id": 15008300079, "name": "github-pages",
                 "expired": False, "workflow_run": {"id": 45583432825}}
            ]},
        ]
        result = find_artifact("https://api.github.com", "test/repo",
                               "45583432825", "token", attempts=4, delay=1)
        self.assertEqual(result, 15008300079)
        self.assertEqual(api.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    @patch("deploy_pages.time.sleep")
    @patch("deploy_pages.api")
    def test_rejects_duplicate_artifact_ids(self, api, sleep):
        api.return_value = {"artifacts": [
            {"id": 1, "name": "github-pages", "expired": False},
            {"id": 2, "name": "github-pages", "expired": False},
        ]}
        with self.assertRaisesRegex(RuntimeError, "Meer dan één"):
            find_artifact("https://api.github.com", "test/repo", "1234", "token")
        sleep.assert_not_called()

    @patch("deploy_pages.api")
    def test_rejects_missing_artifact(self, api):
        api.return_value = {"artifacts": []}
        with self.assertRaises(RuntimeError):
            find_artifact("https://api.github.com", "test/repo", "1234", "token", attempts=1)

    @patch("deploy_pages.api")
    def test_rejects_wrong_workflow_run(self, api):
        api.return_value = {"artifacts": [
            {"id": 14909660476, "name": "github-pages",
             "expired": False, "workflow_run": {"id": 9999}},
        ]}
        with self.assertRaises(RuntimeError):
            find_artifact("https://api.github.com", "test/repo", "1234", "token")


if __name__ == "__main__":
    unittest.main()
