# Result Schema

Use this schema when the user wants a structured output.

## Table Columns

| Decision | Title | Year | Journal | Rank | Citations | Why |
| --- | --- | --- | --- | --- | ---: | --- |
| include/maybe/exclude | Paper title | Publication year | Venue | Rank annotation | Citation count | Short evidence-based reason |

## JSON Shape

```json
{
  "query": "...",
  "sources_used": ["scopus", "openalex"],
  "skipped_sources": [{"source": "unpaywall", "reason": "not_configured"}],
  "papers": [
    {
      "decision": "include",
      "title": "...",
      "authors": ["..."],
      "year": 2026,
      "doi": "...",
      "eid": "...",
      "publication_name": "...",
      "abstract": "...",
      "title_match": "strong",
      "abstract_match": "confirmed",
      "journal_rank": {},
      "citations": 0,
      "source_records": ["scopus"],
      "reasons": ["..."]
    }
  ],
  "next_queries": ["..."]
}
```

## Rank Display

Prefer compact rank strings in tables:

```text
SCI Q1 / CAS 1区 / EI
```

If rank is missing or proxy fails, show `rank unavailable` and keep the candidate.
