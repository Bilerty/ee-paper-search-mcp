---
name: ee-paper-search
description: Multi-source electrical engineering literature search workflow for Codex. Use when searching, screening, enriching, ranking, or summarizing academic papers in electrical engineering across Scopus, OpenAlex, Crossref, Semantic Scholar, Unpaywall, and future sources such as IEEE Xplore, with optional Elsevier Abstract Retrieval and paper-rank-proxy journal rank annotation.
---

# EE Paper Search

Use this skill to plan and execute electrical engineering literature searches with an MCP backend. Keep judgment in Codex: build queries, compare titles and abstracts, decide include/maybe/exclude, and use the MCP only for retrieval, enrichment, and journal rank annotation.

## Enabled Sources

Only call checked sources by default.

- [x] Scopus
  - Role: primary retrieval source for peer-reviewed journal and conference literature.
  - Use: call `search_scopus`; use `get_scopus_abstracts_batch` after title triage.
  - Requires: `PAPER_SEARCH_MCP_ELSEVIER_API_KEY`.

- [x] OpenAlex
  - Role: broad open metadata recall and DOI/journal/citation cross-check.
  - Use: call `search_openalex` or `search_papers` with `sources=openalex`.
  - Requires: no key for baseline use.

- [x] Crossref
  - Role: DOI, publication venue, publisher, and bibliographic metadata backfill.
  - Use: call `search_crossref` or DOI lookup when Scopus metadata is incomplete.
  - Requires: no key.

- [x] Semantic Scholar
  - Role: citation count, abstract/field supplement, and related-paper style recall.
  - Use: call `search_semantic`; treat results as supplementary rather than canonical.
  - Requires: optional `PAPER_SEARCH_MCP_SEMANTIC_SCHOLAR_API_KEY`.

- [x] Unpaywall
  - Role: DOI-centric open-access status and OA URL resolution.
  - Use: call only when DOI exists; do not use as keyword search.
  - Requires: `PAPER_SEARCH_MCP_UNPAYWALL_EMAIL`.

- [ ] IEEE Xplore
  - Role: future electrical engineering source, especially IEEE journals and conferences.
  - Use: keep disabled until API key is approved and connector is implemented/tested.
  - Requires: future `PAPER_SEARCH_MCP_IEEE_API_KEY`.

- [ ] ScienceDirect Search
  - Role: future Elsevier full-text/search expansion if needed.
  - Use: disabled in this phase; Scopus Search remains the Elsevier-side retrieval source.

- [ ] Web of Science
  - Role: future citation-index source.
  - Use: disabled in this phase.

## Workflow

1. Clarify the research object, scenario, method terms, exclusion terms, year range, and desired output size.
2. Read this checked source list. Call `list_literature_sources` or `check_ee_paper_search_config` if configuration is uncertain.
3. Build a broad Scopus query and simpler natural-language queries for checked open sources. See `references/scopus-query-guide.md` and `references/open-source-query-guide.md` when query design matters.
4. Retrieve candidates from checked, configured sources. Skip missing configurations and report them; do not fail the whole search.
5. Deduplicate by DOI, then EID, then normalized title plus year, then normalized title plus first author.
6. Triage titles as `strong`, `possible`, `weak`, or `exclude`. Keep `strong` and `possible` for abstract enrichment.
7. Retrieve Scopus abstracts with `get_scopus_abstracts_batch`, normally capped to the most promising 20 candidates.
8. Triage abstracts as `confirmed`, `partial`, `reject`, or `unknown`.
9. Query journal ranks with `get_publication_ranks_batch` for candidates with `publication_name`.
10. Present `include`, `maybe`, and `exclude/not prioritized` groups with reasons and next query suggestions.

## Screening Rules

Use topic relevance before venue rank:

```text
topic relevance > abstract match > year > citation count > journal rank
```

Do not exclude a highly relevant paper only because the rank is low or missing. Use rank as annotation, sorting reference, and review priority only.

Title triage:

- `strong`: title directly matches object, method, and application scenario.
- `possible`: title matches some elements and may be relevant.
- `weak`: broadly adjacent but likely outside scope.
- `exclude`: clearly outside the requested topic.

Abstract triage:

- `confirmed`: abstract clearly studies the requested problem or method.
- `partial`: abstract covers only part of the requested scope.
- `reject`: abstract shows the paper is off-topic.
- `unknown`: abstract is missing or retrieval failed.

Decision hints:

- `include`: title is strong and abstract is confirmed.
- `maybe`: title is strong/possible and abstract is partial or unknown.
- `exclude`: title or abstract clearly conflicts with the target scope.

## MCP Tool Use

- Use `search_scopus` for first-stage Scopus recall.
- Use `get_scopus_abstract` or `get_scopus_abstracts_batch` for Scopus candidate enrichment.
- Use existing open-source tools such as `search_openalex`, `search_crossref`, `search_semantic`, and `search_papers(sources=...)` for checked open sources.
- Use `get_publication_rank` or `get_publication_ranks_batch` for journal rank annotation through paper-rank-proxy.
- Never use or request `EASYSCHOLAR_SECRET_KEY` locally.

## References

- Read `references/source-selection.md` when deciding which checked source should handle a task.
- Read `references/scopus-query-guide.md` when constructing Scopus syntax.
- Read `references/open-source-query-guide.md` when constructing open-source queries.
- Read `references/result-schema.md` when the user wants a structured table or JSON.
- Read `references/workflow-examples.md` when a concrete end-to-end example would help.
