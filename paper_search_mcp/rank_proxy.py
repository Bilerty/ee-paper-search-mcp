"""Client for the paper-rank-proxy HTTP service."""

from __future__ import annotations

from typing import Any

import httpx

from .config import get_env
from .academic_platforms.scopus import _as_int


def _rank_error_kind(status_code: int) -> str:
    if status_code == 401:
        return "missing_auth"
    if status_code == 403:
        return "auth_error"
    if status_code == 413:
        return "batch_too_large"
    if status_code == 422:
        return "validation_error"
    if status_code == 429:
        return "rate_limited"
    return "upstream_error"


def _safe_response_text(response: httpx.Response) -> str:
    return response.text.strip().replace("\n", " ")[:300]


class JournalRankClient:
    """HTTP client for the deployed journal rank proxy.

    This client only knows the rank proxy URL and bearer token. It never accepts
    or forwards the EasyScholar SecretKey.
    """

    def __init__(
        self,
        proxy_url: str | None = None,
        token: str | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        configured_proxy_url = get_env("RANK_PROXY_URL", "").strip()
        raw_proxy_url = proxy_url if proxy_url is not None else configured_proxy_url
        self.proxy_url_configured = bool(raw_proxy_url and str(raw_proxy_url).strip())
        self.proxy_url = (raw_proxy_url or "").rstrip("/")
        self.token = (token if token is not None else get_env("RANK_PROXY_TOKEN", "")).strip()
        self.timeout_seconds = timeout_seconds or _as_int(get_env("RANK_PROXY_TIMEOUT_SECONDS", "20"), 20)

    def is_configured(self) -> bool:
        return bool(self.proxy_url_configured and self.token)

    async def check_health(self) -> dict[str, Any]:
        if not self.proxy_url_configured:
            return {
                "status": "not_configured",
                "detail": "PAPER_SEARCH_MCP_RANK_PROXY_URL is not explicitly configured.",
            }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(f"{self.proxy_url}/health")
        except httpx.HTTPError as exc:
            return {"status": "request_error", "detail": str(exc)}

        if response.status_code >= 400:
            return {
                "status": _rank_error_kind(response.status_code),
                "status_code": response.status_code,
                "detail": _safe_response_text(response),
            }

        try:
            payload = response.json()
        except ValueError:
            return {"status": "upstream_error", "detail": "health response was not valid JSON"}

        if isinstance(payload, dict) and payload.get("status") == "ok":
            return {"status": "ok"}

        return {"status": "upstream_error", "detail": "health response did not report ok"}

    async def get_rank(self, publication_name: str, force_refresh: bool = False) -> dict[str, Any]:
        publication_name = (publication_name or "").strip()
        if not publication_name:
            return {
                "status": "skipped_no_publication_name",
                "publication_name": publication_name,
                "errors": [{"type": "skipped_no_publication_name", "message": "publication_name is required"}],
            }

        if not self.is_configured():
            return {
                "status": "not_configured",
                "publication_name": publication_name,
                "errors": [
                    {
                        "type": "not_configured",
                        "message": "PAPER_SEARCH_MCP_RANK_PROXY_URL and PAPER_SEARCH_MCP_RANK_PROXY_TOKEN are required.",
                    }
                ],
            }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(
                    f"{self.proxy_url}/rank",
                    params={"publication_name": publication_name, "force_refresh": bool(force_refresh)},
                    headers=self._headers(),
                )
        except httpx.HTTPError as exc:
            return {
                "status": "request_error",
                "publication_name": publication_name,
                "errors": [{"type": "request_error", "message": str(exc)}],
            }

        return self._parse_response(response, publication_name=publication_name)

    async def get_ranks_batch(
        self,
        publication_names: list[str],
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        names = [str(name).strip() for name in publication_names or [] if str(name).strip()]
        if not names:
            return {"status": "ok", "items": [], "errors": []}

        if not self.is_configured():
            return {
                "status": "not_configured",
                "items": [
                    {
                        "status": "not_configured",
                        "publication_name": name,
                        "errors": [{"type": "not_configured", "message": "rank proxy is not configured"}],
                    }
                    for name in names
                ],
                "errors": [{"type": "not_configured", "message": "rank proxy is not configured"}],
            }

        unique_names = list(dict.fromkeys(names))
        payload = {
            "items": [{"publication_name": name} for name in unique_names],
            "force_refresh": bool(force_refresh),
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.proxy_url}/rank/batch",
                    json=payload,
                    headers=self._headers(),
                )
        except httpx.HTTPError as exc:
            return {
                "status": "request_error",
                "items": [
                    {
                        "status": "request_error",
                        "publication_name": name,
                        "errors": [{"type": "request_error", "message": str(exc)}],
                    }
                    for name in names
                ],
                "errors": [{"type": "request_error", "message": str(exc)}],
            }

        if response.status_code >= 400:
            kind = _rank_error_kind(response.status_code)
            message = _safe_response_text(response)
            return {
                "status": kind,
                "items": [
                    {
                        "status": kind,
                        "publication_name": name,
                        "errors": [{"type": kind, "status_code": response.status_code, "message": message}],
                    }
                    for name in names
                ],
                "errors": [{"type": kind, "status_code": response.status_code, "message": message}],
            }

        try:
            upstream = response.json()
        except ValueError:
            return {
                "status": "upstream_error",
                "items": [
                    {
                        "status": "upstream_error",
                        "publication_name": name,
                        "errors": [{"type": "invalid_json", "message": "rank proxy response was not valid JSON"}],
                    }
                    for name in names
                ],
                "errors": [{"type": "invalid_json", "message": "rank proxy response was not valid JSON"}],
            }

        by_name = {
            (item.get("publication_name") or "").strip().lower(): item
            for item in upstream.get("items", [])
            if isinstance(item, dict)
        }
        ordered_items = []
        for name in names:
            item = by_name.get(name.lower())
            if item is None:
                item = {
                    "status": "upstream_error",
                    "publication_name": name,
                    "errors": [{"type": "missing_result", "message": "rank proxy did not return this item"}],
                }
            ordered_items.append(item)

        return {"status": "ok", "items": ordered_items, "errors": []}

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}

    def _parse_response(self, response: httpx.Response, *, publication_name: str) -> dict[str, Any]:
        if response.status_code >= 400:
            kind = _rank_error_kind(response.status_code)
            return {
                "status": kind,
                "publication_name": publication_name,
                "errors": [
                    {
                        "type": kind,
                        "status_code": response.status_code,
                        "message": _safe_response_text(response),
                    }
                ],
            }

        try:
            item = response.json()
        except ValueError:
            return {
                "status": "upstream_error",
                "publication_name": publication_name,
                "errors": [{"type": "invalid_json", "message": "rank proxy response was not valid JSON"}],
            }

        if isinstance(item, dict):
            item.setdefault("errors", [])
            return item

        return {
            "status": "upstream_error",
            "publication_name": publication_name,
            "errors": [{"type": "invalid_payload", "message": "rank proxy response was not an object"}],
        }
