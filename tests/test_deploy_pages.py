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

    @patch("deploy_pages.api")
    def test_rejects_missing_artifact(self, api):
        api.return_value = {"artifacts": []}
        with self.assertRaises(RuntimeError):
            find_artifact("https://api.github.com", "test/repo", "1234", "token")

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
