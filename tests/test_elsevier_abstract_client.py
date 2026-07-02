import asyncio
import unittest
from unittest.mock import patch

import httpx

from paper_search_mcp.academic_platforms.elsevier_abstract import ElsevierAbstractClient


class TestElsevierAbstractClient(unittest.TestCase):
    def test_not_configured_returns_error_object(self):
        client = ElsevierAbstractClient(api_key="")

        result = asyncio.run(client.retrieve(eid="2-s2.0-123"))

        self.assertEqual(result["status"], "not_configured")

    def test_retrieve_prefers_eid_and_parses_coredata(self):
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
                        "abstracts-retrieval-response": {
                            "coredata": {
                                "dc:description": "Abstract text",
                                "prism:doi": "10.1000/test",
                                "prism:publicationName": "Applied Energy",
                                "prism:coverDate": "2024-05-01",
                                "citedby-count": "11",
                                "dc:identifier": "SCOPUS_ID:456",
                                "eid": "2-s2.0-123",
                            },
                            "authors": {"author": [{"ce:indexed-name": "Li, B."}]},
                        }
                    },
                )

        with patch("paper_search_mcp.academic_platforms.elsevier_abstract.httpx.AsyncClient", FakeAsyncClient):
            client = ElsevierAbstractClient(api_key="secret-value", api_url="https://api.example.test")
            result = asyncio.run(client.retrieve(eid="2-s2.0-123", doi="10.1000/fallback"))

        self.assertIn("/content/abstract/eid/2-s2.0-123", captured["url"])
        self.assertEqual(captured["headers"]["X-ELS-APIKey"], "secret-value")
        self.assertNotIn("apiKey", captured["params"])
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["abstract"], "Abstract text")
        self.assertEqual(result["year"], "2024")
        self.assertEqual(result["authors"], ["Li, B."])

    def test_batch_keeps_per_item_errors(self):
        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return None

            async def get(self, url, params=None, headers=None):
                return httpx.Response(404, text="not found")

        with patch("paper_search_mcp.academic_platforms.elsevier_abstract.httpx.AsyncClient", FakeAsyncClient):
            client = ElsevierAbstractClient(api_key="secret-value")
            result = asyncio.run(client.retrieve_many([{"eid": "2-s2.0-missing"}]))

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["results"][0]["status"], "upstream_error")


if __name__ == "__main__":
    unittest.main()
