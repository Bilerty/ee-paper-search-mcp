import asyncio
import unittest
from unittest.mock import patch

import httpx

from paper_search_mcp.rank_proxy import JournalRankClient


class TestJournalRankClient(unittest.TestCase):
    def test_not_configured_returns_error_object(self):
        client = JournalRankClient(proxy_url="https://rank.example.test", token="")

        result = asyncio.run(client.get_rank("Applied Energy"))

        self.assertEqual(result["status"], "not_configured")

    def test_get_rank_uses_bearer_token_and_publication_name(self):
        captured = {}

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def get(self, url, params=None, headers=None):
                captured["url"] = url
                captured["params"] = params
                captured["headers"] = headers
                return httpx.Response(
                    200,
                    json={
                        "publication_name": "Applied Energy",
                        "status": "ok",
                        "cache_hit": True,
                        "journal_rank": {"official_rank_all": {"sci": "Q1"}},
                    },
                )

        with patch("paper_search_mcp.rank_proxy.httpx.AsyncClient", FakeAsyncClient):
            client = JournalRankClient(proxy_url="https://rank.example.test", token="rank-token")
            result = asyncio.run(client.get_rank("Applied Energy"))

        self.assertEqual(captured["headers"]["Authorization"], "Bearer rank-token")
        self.assertEqual(captured["params"]["publication_name"], "Applied Energy")
        self.assertEqual(result["status"], "ok")

    def test_batch_payload_matches_proxy_contract_and_preserves_input_order(self):
        captured = {}

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def post(self, url, json=None, headers=None):
                captured["json"] = json
                captured["headers"] = headers
                return httpx.Response(
                    200,
                    json={
                        "items": [
                            {"publication_name": "A", "status": "ok", "cache_hit": True},
                            {"publication_name": "B", "status": "ok", "cache_hit": False},
                        ]
                    },
                )

        with patch("paper_search_mcp.rank_proxy.httpx.AsyncClient", FakeAsyncClient):
            client = JournalRankClient(proxy_url="https://rank.example.test", token="rank-token")
            result = asyncio.run(client.get_ranks_batch(["A", "B", "A"], force_refresh=True))

        self.assertEqual(
            captured["json"],
            {"items": [{"publication_name": "A"}, {"publication_name": "B"}], "force_refresh": True},
        )
        self.assertEqual([item["publication_name"] for item in result["items"]], ["A", "B", "A"])

    def test_health_requires_explicit_proxy_url(self):
        client = JournalRankClient(proxy_url="", token="rank-token")

        result = asyncio.run(client.check_health())

        self.assertEqual(result["status"], "not_configured")
        self.assertFalse(client.proxy_url_configured)

    def test_health_reports_ok(self):
        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def get(self, url):
                return httpx.Response(200, json={"status": "ok"})

        with patch("paper_search_mcp.rank_proxy.httpx.AsyncClient", FakeAsyncClient):
            client = JournalRankClient(proxy_url="https://rank.example.test", token="rank-token")
            result = asyncio.run(client.check_health())

        self.assertTrue(client.proxy_url_configured)
        self.assertEqual(result["status"], "ok")


if __name__ == "__main__":
    unittest.main()
