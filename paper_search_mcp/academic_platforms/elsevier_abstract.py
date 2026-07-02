"""Elsevier Abstract Retrieval API client."""

from __future__ import annotations

import asyncio
from typing import Any
from urllib.parse import quote

import httpx

from ..config import get_env
from .scopus import DEFAULT_ELSEVIER_API_URL, _as_int, _clean_text, _ensure_list, _safe_error_response


def _recursive_find_text(value: Any, preferred_keys: tuple[str, ...]) -> str:
    if isinstance(value, dict):
        for key in preferred_keys:
            if key in value:
                text = _recursive_find_text(value[key], preferred_keys)
                if text:
                    return text
        if "$" in value and isinstance(value["$"], str):
            return value["$"].strip()
        for child in value.values():
            text = _recursive_find_text(child, preferred_keys)
            if text:
                return text
    elif isinstance(value, list):
        parts = [_recursive_find_text(item, preferred_keys) for item in value]
        parts = [part for part in parts if part]
        if parts:
            return " ".join(parts).strip()
    elif isinstance(value, str):
        return value.strip()
    return ""


def _extract_author_names(response: dict[str, Any]) -> list[str]:
    authors: list[str] = []
    author_section = response.get("authors", {})
    for author in _ensure_list(author_section.get("author") if isinstance(author_section, dict) else author_section):
        if not isinstance(author, dict):
            continue
        name = _clean_text(
            author.get("ce:indexed-name")
            or author.get("preferred-name", {}).get("ce:indexed-name")
            or author.get("ce:surname")
        )
        if name:
            authors.append(name)
    return authors


def _extract_subject_areas(response: dict[str, Any]) -> list[str]:
    areas: list[str] = []
    subject_section = response.get("subject-areas", {})
    for area in _ensure_list(subject_section.get("subject-area") if isinstance(subject_section, dict) else subject_section):
        if isinstance(area, dict):
            text = _clean_text(area.get("$") or area.get("@abbrev") or area.get("@code"))
            if text:
                areas.append(text)
    return areas


def _extract_keywords(response: dict[str, Any]) -> list[str]:
    keywords: list[str] = []
    authkeywords = response.get("authkeywords", {})
    for keyword in _ensure_list(authkeywords.get("author-keyword") if isinstance(authkeywords, dict) else authkeywords):
        text = _recursive_find_text(keyword, ("$text", "text", "$"))
        if text:
            keywords.append(text)
    return keywords


def _extract_affiliations(response: dict[str, Any]) -> list[str]:
    affiliations: list[str] = []
    for affiliation in _ensure_list(response.get("affiliation")):
        if not isinstance(affiliation, dict):
            continue
        name = _clean_text(affiliation.get("affilname") or affiliation.get("affiliation-name"))
        city = _clean_text(affiliation.get("affiliation-city"))
        country = _clean_text(affiliation.get("affiliation-country"))
        parts = [part for part in (name, city, country) if part]
        if parts:
            affiliations.append(", ".join(parts))
    return affiliations


class ElsevierAbstractClient:
    """Client for Elsevier Abstract Retrieval.

    Lookup priority is controlled by callers: EID should be preferred, then DOI,
    then Scopus ID. The API key is sent in the X-ELS-APIKey header.
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str | None = None,
        timeout_seconds: int | None = None,
        concurrency: int | None = None,
    ) -> None:
        self.api_key = (api_key if api_key is not None else get_env("ELSEVIER_API_KEY", "")).strip()
        self.api_url = (
            api_url if api_url is not None else get_env("ELSEVIER_API_URL", DEFAULT_ELSEVIER_API_URL)
        ).rstrip("/")
        self.timeout_seconds = timeout_seconds or _as_int(get_env("ELSEVIER_TIMEOUT_SECONDS", "30"), 30)
        self.concurrency = concurrency or _as_int(get_env("ELSEVIER_CONCURRENCY", "3"), 3)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def retrieve(
        self,
        *,
        eid: str | None = None,
        doi: str | None = None,
        scopus_id: str | None = None,
        view: str | None = None,
    ) -> dict[str, Any]:
        identifier = self._select_identifier(eid=eid, doi=doi, scopus_id=scopus_id)
        if identifier is None:
            return {
                "status": "invalid_request",
                "source": "elsevier_abstract",
                "errors": [{"type": "invalid_request", "message": "eid, doi, or scopus_id is required"}],
            }

        if not self.is_configured():
            return {
                "status": "not_configured",
                "source": "elsevier_abstract",
                "lookup": identifier,
                "errors": [
                    {
                        "type": "not_configured",
                        "message": "PAPER_SEARCH_MCP_ELSEVIER_API_KEY or ELSEVIER_API_KEY is not configured.",
                    }
                ],
            }

        endpoint = f"{self.api_url}/content/abstract/{identifier['type']}/{quote(identifier['value'], safe='')}"
        params = {
            "view": view or get_env("ELSEVIER_ABSTRACT_VIEW", "META_ABS"),
            "httpAccept": "application/json",
        }
        headers = {"X-ELS-APIKey": self.api_key, "Accept": "application/json"}

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(endpoint, params=params, headers=headers)
        except httpx.HTTPError as exc:
            return {
                "status": "request_error",
                "source": "elsevier_abstract",
                "lookup": identifier,
                "errors": [{"type": "request_error", "message": str(exc)}],
            }

        if response.status_code >= 400:
            error = _safe_error_response(response.status_code, response.text)
            error["source"] = "elsevier_abstract"
            error["lookup"] = identifier
            return error

        try:
            payload = response.json()
        except ValueError:
            return {
                "status": "upstream_error",
                "source": "elsevier_abstract",
                "lookup": identifier,
                "errors": [{"type": "invalid_json", "message": "Abstract response was not valid JSON."}],
            }

        parsed = self._parse_payload(payload)
        parsed["lookup"] = identifier
        return parsed

    async def retrieve_many(
        self,
        items: list[dict[str, Any]],
        *,
        view: str | None = None,
        max_items: int = 20,
    ) -> dict[str, Any]:
        selected = list(items or [])[: max(0, int(max_items))]
        semaphore = asyncio.Semaphore(max(1, self.concurrency))

        async def run_one(item: dict[str, Any]) -> dict[str, Any]:
            async with semaphore:
                result = await self.retrieve(
                    eid=item.get("eid"),
                    doi=item.get("doi"),
                    scopus_id=item.get("scopus_id"),
                    view=view,
                )
                result["input"] = item
                return result

        results = await asyncio.gather(*(run_one(item) for item in selected))
        return {
            "status": "ok",
            "source": "elsevier_abstract",
            "requested": len(items or []),
            "returned": len(results),
            "results": results,
        }

    def _select_identifier(
        self,
        *,
        eid: str | None = None,
        doi: str | None = None,
        scopus_id: str | None = None,
    ) -> dict[str, str] | None:
        if eid and str(eid).strip():
            return {"type": "eid", "value": str(eid).strip()}
        if doi and str(doi).strip():
            return {"type": "doi", "value": str(doi).strip()}
        if scopus_id and str(scopus_id).strip():
            return {"type": "scopus_id", "value": str(scopus_id).strip()}
        return None

    def _parse_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = payload.get("abstracts-retrieval-response", payload)
        coredata = response.get("coredata", {}) if isinstance(response, dict) else {}

        abstract = _clean_text(coredata.get("dc:description"))
        if not abstract:
            abstract = _recursive_find_text(response.get("item", {}), ("abstracts", "abstract", "para", "$"))

        cover_date = _clean_text(coredata.get("prism:coverDate"))
        year = cover_date[:4] if len(cover_date) >= 4 and cover_date[:4].isdigit() else ""
        scopus_id = _clean_text(coredata.get("dc:identifier")).replace("SCOPUS_ID:", "")

        return {
            "status": "ok",
            "source": "elsevier_abstract",
            "abstract": abstract,
            "keywords": _extract_keywords(response),
            "authors": _extract_author_names(response),
            "affiliations": _extract_affiliations(response),
            "doi": _clean_text(coredata.get("prism:doi")),
            "publication_name": _clean_text(coredata.get("prism:publicationName")),
            "issn": _clean_text(coredata.get("prism:issn")),
            "eissn": _clean_text(coredata.get("prism:eIssn")),
            "cover_date": cover_date,
            "year": year,
            "citedby_count": _as_int(_clean_text(coredata.get("citedby-count")), 0),
            "subject_areas": _extract_subject_areas(response),
            "eid": _clean_text(coredata.get("eid")),
            "scopus_id": scopus_id,
            "errors": [],
        }
