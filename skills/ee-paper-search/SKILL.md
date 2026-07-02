---
name: ee-paper-search
description: Multi-source electrical engineering literature search workflow for AI agents including Codex, Claude Code, and Hermes Agent. Use when searching, screening, enriching, ranking, or summarizing academic papers in electrical engineering across Scopus, OpenAlex, Crossref, Semantic Scholar, Unpaywall, and optional sources such as IEEE Xplore, with Elsevier Abstract Retrieval and paper-rank-proxy journal rank annotation.
---

# EE Paper Search

Use this skill to plan and execute electrical engineering literature searches with an MCP backend. It is agent-agnostic and can be used by Codex, Claude Code, Hermes Agent, or other AI agents that can read this skill and call the configured MCP tools.

Keep scholarly judgment in the agent: build queries, compare titles and abstracts, balance topic relevance with journal rank, decide include/maybe/exclude, and use the MCP only for retrieval, enrichment, metadata backfill, and journal rank annotation.

## Instruction Priority

User prompts and task-specific instructions have higher priority than this skill. If the prompt specifies new requirements for topic relevance, journal rank systems, target quartiles, time range, source selection, exclusion rules, or output format, follow the prompt first and use this skill only as the default workflow.

Do not treat the screening rules below as hard filters unless the user explicitly asks for hard filtering. When the user gives rank preferences, try to select papers from the requested rank levels while preserving enough highly relevant candidates for review.

## Agent Compatibility

- Codex: use the MCP tools directly when available and keep reasoning, screening, and final synthesis in the conversation.
- Claude Code: use the same skill workflow and MCP tool names; if tools are exposed through a different wrapper, map the wrapper calls back to the tool roles in this file.
- Hermes Agent: use the same source checklist, screening labels, journal rank preferences, and result schema; report unavailable tools instead of silently changing the workflow.
- Other agents: preserve the same retrieval/enrichment/rank-annotation separation and avoid storing EasyScholar credentials locally.

## Enabled Sources

Only call checked sources by default. Unchecked sources are not used by default; sources marked "(unsupported)" also require connector implementation and tests before use.

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

- [ ] IEEE Xplore (unsupported)
  - Role: electrical engineering source for IEEE journals, magazines, standards-related venues, and conferences.
  - Use: call an IEEE connector only after the API key, connector, and tests are available.
  - Requires: `PAPER_SEARCH_MCP_IEEE_API_KEY`.

- [ ] ScienceDirect Search (unsupported)
  - Role: Elsevier full-text/search expansion and publisher-side metadata verification.
  - Use: call a ScienceDirect Search connector only after implementation and tests are available; Scopus remains the Elsevier-side retrieval source until then.
  - Requires: Elsevier API credentials and connector support.

- [ ] Web of Science (unsupported)
  - Role: citation-index retrieval, journal-index cross-check, and citation analysis.
  - Use: call a Web of Science connector only after credentials, implementation, and tests are available.
  - Requires: Web of Science API credentials and connector support.

## Journal Rank Preferences

Use journal rank as a co-primary screening dimension with topic relevance. When the user asks for specific rank systems or rank levels, prefer papers from those selected levels. If the user does not specify a rank target, use the default electrical-engineering preference order below as a soft ranking guide.

Common rank systems for electrical engineering:

- SCI/JCR quartile (`sci`): prefer Q1 and Q2; use Q3 as possible when topic relevance is strong; deprioritize Q4 unless the paper is highly relevant or uniquely useful.
- JCR impact factor (`sciif`) and five-year impact factor (`sciif5`): use as secondary tie-breakers within the same topic relevance and quartile level.
- CAS/Chinese Academy of Sciences upgraded partition (`sciUp`): prefer Zone 1 and Zone 2; use Zone 3 as possible when relevance is strong; deprioritize Zone 4 unless needed.
- CAS upgraded top flag (`sciUpTop`): prioritize Top journals when topic relevance is comparable.
- CAS upgraded small category (`sciUpSmall`): use to judge whether the journal belongs to a relevant electrical engineering, energy, power systems, automation, control, electronics, or computer-adjacent category.
- CAS basic partition (`sciBase`): use as fallback if upgraded partition is missing.
- SCI warning lists (`sciwarn`, `xrWarn`): flag clearly and normally deprioritize unless the user explicitly accepts warning-listed venues.
- EI (`eii`): prioritize EI-indexed conference or engineering journal papers when conference literature is requested or when SCI rank is not applicable.
- Peking University Core (`pku`): for Chinese journals, prefer PKU Core when the user accepts Chinese-language literature.
- CSCD (`cscd`): for Chinese science and engineering journals, prefer CSCD-indexed venues.
- Chinese Science and Technology Core (`zhongguokejihexin`): use as a supplementary Chinese-journal quality signal.
- CCF (`ccf`): use only for computer-science-adjacent electrical engineering topics such as power cyber-physical systems, AI for power systems, optimization platforms, or communications/control intersections.

Default rank preference when the user gives no specific rank requirement:

```text
SCI Q1/Q2 or CAS Zone 1/2 or CAS Top
> EI-indexed strong engineering venues
> CSCD / PKU Core / Chinese Science and Technology Core for Chinese journals
> other ranked venues
> unranked or warning-listed venues
```

Rank handling rules:

- Balance topic relevance and journal rank. Neither should automatically dominate the other.
- Prefer selected rank levels when several papers have comparable relevance.
- Do not discard a highly relevant paper only because rank data is missing, unless the user explicitly requires ranked-only results.
- If the user asks for hard rank constraints, apply them and clearly report how many candidates were excluded by the constraint.
- Treat rank proxy data as annotation and decision support; keep the original source metadata visible when possible.

## Workflow

1. Clarify the research object, scenario, method terms, exclusion terms, year range, desired output size, and journal rank preferences.
2. Read this checked source list. Call `list_literature_sources` or `check_ee_paper_search_config` if configuration is uncertain.
3. Build a broad Scopus query and simpler natural-language queries for checked open sources. See `references/scopus-query-guide.md` and `references/open-source-query-guide.md` when query design matters.
4. Retrieve candidates from checked, configured sources. Skip missing configurations and report them; do not fail the whole search.
5. Deduplicate by DOI, then EID, then normalized title plus year, then normalized title plus first author.
6. Triage titles as `strong`, `possible`, `weak`, or `exclude`. Keep `strong` and `possible` for abstract enrichment unless the user asks for a different rule.
7. Retrieve Scopus abstracts with `get_scopus_abstracts_batch`, normally capped to the most promising 20 candidates.
8. Triage abstracts as `confirmed`, `partial`, `reject`, or `unknown`.
9. Query journal ranks with `get_publication_ranks_batch` for candidates with `publication_name`.
10. Apply the user-specified rank preferences or the default electrical-engineering rank preference.
11. Present `include`, `maybe`, and `exclude/not prioritized` groups with topic reasons, rank reasons, and next query suggestions.

## Screening Rules

Use topic relevance and journal rank as co-primary dimensions:

```text
topic relevance + journal rank > abstract match detail > year > citation count
```

For electrical engineering literature review tasks, prefer papers that are both topically relevant and published in the selected or preferred rank levels. If topic relevance and rank conflict, report the tradeoff instead of hiding the paper.

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

Rank triage:

- `preferred`: rank matches the user's selected rank levels or the default high-priority electrical-engineering levels.
- `acceptable`: rank is below the preferred level but still reasonable for the task.
- `low_priority`: rank is low, warning-listed, missing, or outside the requested rank preference.
- `unknown`: rank lookup failed or the venue cannot be matched.

Decision hints:

- `include`: topic relevance is strong/confirmed and rank is preferred or acceptable.
- `maybe`: topic relevance is strong/possible but rank is low_priority/unknown, or rank is preferred but topical evidence is partial.
- `exclude`: title or abstract clearly conflicts with the target scope, or the user requested hard rank filtering and the paper fails it.

## MCP Tool Use

- Use `search_scopus` for first-stage Scopus recall.
- Use `get_scopus_abstract` or `get_scopus_abstracts_batch` for Scopus candidate enrichment.
- Use existing open-source tools such as `search_openalex`, `search_crossref`, `search_semantic`, and `search_papers(sources=...)` for checked open sources.
- Use `get_publication_rank` or `get_publication_ranks_batch` for journal rank annotation through paper-rank-proxy.
- Never use or request `EASYSCHOLAR_SECRET_KEY` locally.
- Require `PAPER_SEARCH_MCP_RANK_PROXY_URL` and `PAPER_SEARCH_MCP_RANK_PROXY_TOKEN` for rank proxy calls; do not rely on a built-in default rank proxy URL.

## References

- Read `references/source-selection.md` when deciding which checked source should handle a task.
- Read `references/scopus-query-guide.md` when constructing Scopus syntax.
- Read `references/open-source-query-guide.md` when constructing open-source queries.
- Read `references/result-schema.md` when the user wants a structured table or JSON.
- Read `references/workflow-examples.md` when a concrete end-to-end example would help.
