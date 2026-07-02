# Workflow Examples

## Example 1: Distribution Network Restoration

User request:

```text
Find recent papers on distribution network service restoration with microgrids.
```

Process:

1. Build a broad Scopus query with distribution network, service restoration, microgrid, resilience, and reconfiguration terms.
2. Call `search_scopus` with `max_results=50` through two pages if needed.
3. Call `search_openalex` and `search_semantic` with simpler natural-language queries.
4. Deduplicate by DOI and title.
5. Keep title `strong` and `possible` candidates.
6. Call `get_scopus_abstracts_batch` for Scopus candidates.
7. Call `get_publication_ranks_batch` for known venues.
8. Output include/maybe/exclude with next queries.

## Example 2: Integrated Energy System Fault Recovery

Start with:

```text
TITLE-ABS-KEY(("integrated energy system" OR "multi-energy system") AND (fault OR outage OR recovery OR restoration) AND (optimization OR dispatch OR resilience))
```

Narrow if results drift into generic energy planning:

```text
TITLE(("integrated energy system" OR "multi-energy system") AND (fault OR recovery OR restoration))
```
