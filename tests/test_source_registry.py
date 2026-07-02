import unittest

from paper_search_mcp.source_registry import list_literature_source_status


class StubClient:
    def __init__(self, configured):
        self._configured = configured

    def is_configured(self):
        return self._configured


class TestSourceRegistry(unittest.TestCase):
    def test_lists_reserved_future_sources(self):
        result = list_literature_source_status(
            scopus_client=StubClient(True),
            abstract_client=StubClient(True),
            rank_client=StubClient(False),
        )

        by_source = {item["source"]: item for item in result["sources"]}
        self.assertTrue(by_source["scopus"]["enabled_by_default"])
        self.assertTrue(by_source["elsevier_abstract"]["configured"])
        self.assertFalse(by_source["rank_proxy"]["configured"])
        self.assertFalse(by_source["ieee"]["enabled_by_default"])
        self.assertFalse(by_source["sciencedirect"]["enabled_by_default"])
        self.assertFalse(by_source["web_of_science"]["enabled_by_default"])


if __name__ == "__main__":
    unittest.main()
