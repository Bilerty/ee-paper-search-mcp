import asyncio
import unittest
from unittest.mock import patch

import httpx

from paper_search_mcp.academic_platforms.scopus import ScopusClient


class TestScopusClient(unittest.TestCase):
    def test_not_configured_returns_error_object(self):
        client = ScopusClient(api_key="")

        result = asyncio.run(client.search("TITLE(test)"))

        self.assertEqual(result["status"], "not_configured")
        self.assertEqual(result["results"], [])

    def test_search_uses_header_not_query_parameter(self):
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
                        "search-results": {
                            "opensearch:totalResults": "1",
                            "opensearch:startIndex": "0",
                            "entry": [
                                {
                                    "dc:title": "Power system restoration",
                                    "eid": "2-s2.0-123",
                                    "dc:identifier": "SCOPUS_ID:123",
                                    "prism:doi": "10.1000/test",
                                    "prism:publicationName": "IEEE Transactions on Power Systems",
                                    "prism:coverDate": "2025-01-01",
                                    "citedby-count": "7",
                                }
                            ],
                        }
                    },
                )

        with patch("paper_search_mcp.academic_platforms.scopus.httpx.AsyncClient", FakeAsyncClient):
            client = ScopusClient(api_key="secret-value", api_url="https://api.example.test")
            result = asyncio.run(client.search("TITLE(test)", max_results=50))

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["returned"], 1)
        self.assertEqual(captured["headers"]["X-ELS-APIKey"], "secret-value")
        self.assertNotIn("apiKey", captured["params"])
        self.assertEqual(captured["params"]["count"], 25)

    def test_401_is_auth_error(self):
        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def get(self, url, params=None, headers=None):
                return httpx.Response(401, text="bad key")

        with patch("paper_search_mcp.academic_platforms.scopus.httpx.AsyncClient", FakeAsyncClient):
            client = ScopusClient(api_key="secret-value")
            result = asyncio.run(client.search("TITLE(test)"))

        self.assertEqual(result["status"], "auth_error")
        self.assertEqual(result["errors"][0]["status_code"], 401)


if __name__ == "__main__":
    unittest.main()
