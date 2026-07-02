"""Scopus Search API client for the EE paper-search workflow."""

from __future__ import annotations

from typing import Any

import httpx

from ..config import get_env


DEFAULT_ELSEVIER_API_URL = "https://api.elsevier.com"


def _as_int(value: str, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _ensure_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _error_kind(status_code: int) -> str:
    if status_code == 401:
        return "auth_error"
    if status_code == 403:
        return "entitlement_error"
    if status_code == 429:
        return "rate_limited"
    return "upstream_error"


def _safe_error_response(status_code: int, response_text: str = "") -> dict[str, Any]:
    message = response_text.strip().replace("\n", " ")[:300]
    return {
        "status": _error_kind(status_code),
        "source": "scopus",
        "status_code": status_code,
        "message": message,
        "results": [],
        "errors": [
            {
                "type": _error_kind(status_code),
                "status_code": status_code,
                "message": message,
            }
        ],
    }


class ScopusClient:
    """Small async client for Scopus Search.

    The Elsevier API key is always sent in the X-ELS-APIKey header, never as a
    query parameter, so logs and proxies do not capture credentials in URLs.
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.api_key = (api_key if api_key is not None else get_env("ELSEVIER_API_KEY", "")).strip()
        self.api_url = (
            api_url if api_url is not None else get_env("ELSEVIER_API_URL", DEFAULT_ELSEVIER_API_URL)
        ).rstrip("/")
        self.timeout_seconds = timeout_seconds or _as_int(get_env("ELSEVIER_TIMEOUT_SECONDS", "30"), 30)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def search(
        self,
        query: str,
        max_results: int = 25,
        start: int = 0,
        sort: str | None = None,
        field: str | None = None,
        view: str = "STANDARD",
    ) -> dict[str, Any]:
        query = (query or "").strip()
        if not query:
            return {
                "status": "invalid_request",
                "source": "scopus",
                "query": query,
                "results": [],
                "errors": [{"type": "invalid_request", "message": "query is required"}],
            }

        if not self.is_configured():
            return {
                "status": "not_configured",
                "source": "scopus",
                "query": query,
                "results": [],
                "errors": [
                    {
                        "type": "not_configured",
                        "message": "PAPER_SEARCH_MCP_ELSEVIER_API_KEY or ELSEVIER_API_KEY is not configured.",
                    }
                ],
            }

        count = max(1, min(int(max_results), 25))
        params: dict[str, Any] = {
            "query": query,
            "view": view,
            "start": max(0, int(start)),
            "count": count,
            "httpAccept": "application/json",
        }
        if sort:
            params["sort"] = sort
        if field:
            params["field"] = field

        headers = {"X-ELS-APIKey": self.api_key, "Accept": "application/json"}
        endpoint = f"{self.api_url}/content/search/scopus"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(endpoint, params=params, headers=headers)
        except httpx.HTTPError as exc:
            return {
                "status": "request_error",
                "source": "scopus",
                "query": query,
                "results": [],
                "errors": [{"type": "request_error", "message": str(exc)}],
            }

        if response.status_code >= 400:
            error = _safe_error_response(response.status_code, response.text)
            error["query"] = query
            return error

        try:
            payload = response.json()
        except ValueError:
            return {
                "status": "upstream_error",
                "source": "scopus",
                "query": query,
                "results": [],
                "errors": [{"type": "invalid_json", "message": "Scopus response was not valid JSON."}],
            }

        search_results = payload.get("search-results", {})
        entries = _ensure_list(search_results.get("entry"))
        results = [self._parse_entry(entry) for entry in entries if isinstance(entry, dict)]

        return {
            "status": "ok",
            "source": "scopus",
            "query": query,
            "total_results": _as_int(_clean_text(search_results.get("opensearch:totalResults")), len(results)),
            "returned": len(results),
            "start": _as_int(_clean_text(search_results.get("opensearch:startIndex")), max(0, int(start))),
            "results": results,
            "errors": [],
        }

    def _parse_entry(self, entry: dict[str, Any]) -> dict[str, Any]:
        doi = _clean_text(entry.get("prism:doi"))
        scopus_id = _clean_text(entry.get("dc:identifier")).replace("SCOPUS_ID:", "")
        authors = []
        for author in _ensure_list(entry.get("author")):
            if isinstance(author, dict):
                name = _clean_text(author.get("authname") or author.get("ce:indexed-name") or author.get("surname"))
                if name:
                    authors.append(name)

        cover_date = _clean_text(entry.get("prism:coverDate"))
        year = cover_date[:4] if len(cover_date) >= 4 and cover_date[:4].isdigit() else ""

        link = ""
        for link_item in _ensure_list(entry.get("link")):
            if isinstance(link_item, dict):
                candidate = _clean_text(link_item.get("@href"))
                if candidate:
                    link = candidate
                    break

        return {
            "title": _clean_text(entry.get("dc:title")),
            "eid": _clean_text(entry.get("eid")),
            "scopus_id": scopus_id,
            "doi": doi,
            "publication_name": _clean_text(entry.get("prism:publicationName")),
            "issn": _clean_text(entry.get("prism:issn")),
            "eissn": _clean_text(entry.get("prism:eIssn")),
            "cover_date": cover_date,
            "year": year,
            "authors": authors,
            "citations": _as_int(_clean_text(entry.get("citedby-count")), 0),
            "document_type": _clean_text(entry.get("subtypeDescription") or entry.get("subtype")),
            "open_access": _clean_text(entry.get("openaccess") or entry.get("openaccessFlag")),
            "url": link,
            "source": "scopus",
        }
