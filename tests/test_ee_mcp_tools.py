import asyncio
import unittest
from unittest.mock import patch

from paper_search_mcp import server


class TestEEMcpTools(unittest.TestCase):
    def test_search_scopus_delegates_to_client(self):
        class StubScopusClient:
            async def search(self, **kwargs):
                return {"status": "ok", "kwargs": kwargs}

        with patch.object(server, "scopus_client", StubScopusClient()):
            result = asyncio.run(server.search_scopus("TITLE(test)", max_results=3))

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["kwargs"]["query"], "TITLE(test)")

    def test_get_publication_ranks_batch_delegates_to_client(self):
        class StubRankClient:
            async def get_ranks_batch(self, publication_names, force_refresh=False):
                return {"status": "ok", "items": publication_names, "force_refresh": force_refresh}

        with patch.object(server, "journal_rank_client", StubRankClient()):
            result = asyncio.run(server.get_publication_ranks_batch(["A"], force_refresh=True))

        self.assertEqual(result["items"], ["A"])
        self.assertTrue(result["force_refresh"])

    def test_config_diagnostics_are_redacted(self):
        class StubScopusClient:
            def is_configured(self):
                return True

        class StubAbstractClient:
            def is_configured(self):
                return True

        class StubRankClient:
            proxy_url_configured = False
            token = ""

            def is_configured(self):
                return False

            async def check_health(self):
                return {"status": "not_configured", "detail": "missing explicit url"}

        with (
            patch.object(server, "scopus_client", StubScopusClient()),
            patch.object(server, "elsevier_abstract_client", StubAbstractClient()),
            patch.object(server, "journal_rank_client", StubRankClient()),
        ):
            result = asyncio.run(server.check_ee_paper_search_config())

        self.assertIn("elsevier_api_key_configured", result)
        self.assertFalse(result["rank_proxy_url_configured"])
        self.assertFalse(result["rank_proxy_token_configured"])
        self.assertEqual(result["rank_proxy_health"], "not_configured")
        self.assertIn("rank_proxy_health_detail", result)
        self.assertNotIn("token", str(result).lower().replace("rank_proxy_token_configured", ""))

    def test_config_diagnostics_report_rank_proxy_health_ok(self):
        class StubScopusClient:
            def is_configured(self):
                return True

        class StubAbstractClient:
            def is_configured(self):
                return True

        class StubRankClient:
            proxy_url_configured = True
            token = "redacted"

            def is_configured(self):
                return True

            async def check_health(self):
                return {"status": "ok"}

        with (
            patch.object(server, "scopus_client", StubScopusClient()),
            patch.object(server, "elsevier_abstract_client", StubAbstractClient()),
            patch.object(server, "journal_rank_client", StubRankClient()),
        ):
            result = asyncio.run(server.check_ee_paper_search_config())

        self.assertTrue(result["rank_proxy_url_configured"])
        self.assertTrue(result["rank_proxy_token_configured"])
        self.assertEqual(result["rank_proxy_health"], "ok")
        self.assertNotIn("rank_proxy_health_detail", result)


if __name__ == "__main__":
    unittest.main()
