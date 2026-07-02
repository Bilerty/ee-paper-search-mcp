"""Source capability registry for the EE paper-search Skill."""

from __future__ import annotations

from typing import Any

from .config import get_env
from .academic_platforms.elsevier_abstract import ElsevierAbstractClient
from .academic_platforms.scopus import ScopusClient
from .rank_proxy import JournalRankClient


def _has_env(name: str) -> bool:
    return bool(get_env(name, "").strip())


def list_literature_source_status(
    *,
    scopus_client: ScopusClient | None = None,
    abstract_client: ElsevierAbstractClient | None = None,
    rank_client: JournalRankClient | None = None,
) -> dict[str, Any]:
    scopus_client = scopus_client or ScopusClient()
    abstract_client = abstract_client or ElsevierAbstractClient()
    rank_client = rank_client or JournalRankClient()

    sources = [
        {
            "source": "scopus",
            "configured": scopus_client.is_configured(),
            "enabled_by_default": True,
            "requires_key": True,
            "capabilities": ["search"],
            "notes": "Primary retrieval source for the EE workflow.",
        },
        {
            "source": "elsevier_abstract",
            "configured": abstract_client.is_configured(),
            "enabled_by_default": True,
            "requires_key": True,
            "capabilities": ["abstract_retrieval"],
            "notes": "Use for Scopus candidates after title triage.",
        },
        {
            "source": "openalex",
            "configured": True,
            "enabled_by_default": True,
            "requires_key": False,
            "capabilities": ["search", "metadata"],
            "notes": "Open metadata recall and DOI/journal/citation cross-check.",
        },
        {
            "source": "crossref",
            "configured": True,
            "enabled_by_default": True,
            "requires_key": False,
            "capabilities": ["search", "doi_metadata"],
            "notes": "DOI, publication venue, publisher, and bibliographic backfill.",
        },
        {
            "source": "semantic",
            "configured": True,
            "enabled_by_default": True,
            "requires_key": False,
            "capabilities": ["search", "abstract", "citation_metadata"],
            "notes": "Supplementary citation, abstract, and field metadata.",
        },
        {
            "source": "unpaywall",
            "configured": _has_env("UNPAYWALL_EMAIL"),
            "enabled_by_default": True,
            "requires_key": True,
            "capabilities": ["oa_status", "oa_url"],
            "notes": "DOI-centric open-access lookup; not a keyword search source.",
        },
        {
            "source": "rank_proxy",
            "configured": rank_client.is_configured(),
            "enabled_by_default": True,
            "requires_key": True,
            "capabilities": ["journal_rank"],
            "notes": "Calls paper-rank-proxy; does not use EasyScholar SecretKey locally.",
        },
        {
            "source": "ieee",
            "configured": _has_env("IEEE_API_KEY"),
            "enabled_by_default": False,
            "requires_key": True,
            "capabilities": [],
            "notes": "Reserved until IEEE API key is approved and connector is tested.",
        },
        {
            "source": "sciencedirect",
            "configured": False,
            "enabled_by_default": False,
            "requires_key": True,
            "capabilities": [],
            "notes": "Reserved for future design; Scopus remains the Elsevier search source.",
        },
        {
            "source": "web_of_science",
            "configured": False,
            "enabled_by_default": False,
            "requires_key": True,
            "capabilities": [],
            "notes": "Reserved for future API access and connector design.",
        },
    ]

    return {"sources": sources}
