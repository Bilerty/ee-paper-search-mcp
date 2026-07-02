# tests/test_server.py
import unittest
import asyncio
import os
import tempfile
from pathlib import Path
from paper_search_mcp import server

class TestPaperSearchServer(unittest.TestCase):
    def _search_arxiv_or_skip(self, max_results: int):
        result = asyncio.run(server.search_arxiv("machine learning", max_results=max_results))
        self.assertIsInstance(result, list, "Result should be a list")
        if not result:
            self.skipTest("arXiv API is unavailable, rate-limited, or returned no results")
        self.assertLessEqual(len(result), max_results)
        return result

    def test_all_sources_include_new_platforms(self):
        self.assertIn("dblp", server.ALL_SOURCES)
        self.assertIn("openaire", server.ALL_SOURCES)
        self.assertIn("citeseerx", server.ALL_SOURCES)
        self.assertIn("doaj", server.ALL_SOURCES)
        self.assertIn("base", server.ALL_SOURCES)
        self.assertIn("zenodo", server.ALL_SOURCES)
        self.assertIn("hal", server.ALL_SOURCES)
        self.assertIn("ssrn", server.ALL_SOURCES)
        self.assertIn("unpaywall", server.ALL_SOURCES)

    def test_parse_sources_with_new_platforms(self):
        parsed = server._parse_sources("dblp,doaj,base,zenodo,hal,ssrn,unpaywall,invalid")
        self.assertEqual(parsed, ["dblp", "doaj", "base", "zenodo", "hal", "ssrn", "unpaywall"])

    def test_search_arxiv(self):
        """Test the search_arxiv tool returns arXiv-style paper records."""
        result = self._search_arxiv_or_skip(max_results=10)
        for paper in result:
            self.assertIn('title', paper, "Each result should contain a title")
            self.assertIn('paper_id', paper, "Each result should contain a paper_id")

    def test_download_arxiv_from_search(self):
        """Test downloading an arXiv paper based on a search result."""
        if os.getenv("PAPER_SEARCH_MCP_RUN_LIVE_DOWNLOAD_TESTS") != "1":
            self.skipTest("Set PAPER_SEARCH_MCP_RUN_LIVE_DOWNLOAD_TESTS=1 to run live download tests")

        search_results = self._search_arxiv_or_skip(max_results=1)

        with tempfile.TemporaryDirectory() as save_path:
            paper_id = search_results[0]['paper_id']
            result = asyncio.run(server.download_arxiv(paper_id, save_path))
            self.assertIsInstance(result, str, f"Result for {paper_id} should be a file path")
            self.assertTrue(result.endswith(".pdf"), f"Result for {paper_id} should be a PDF file path")
            self.assertTrue(
                Path(result).is_relative_to(Path(save_path)),
                f"PDF file for {paper_id} should be written to the temporary directory",
            )
            self.assertTrue(Path(result).exists(), f"PDF file for {paper_id} should exist on disk")

if __name__ == "__main__":
    unittest.main()
