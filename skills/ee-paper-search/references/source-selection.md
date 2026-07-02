# Source Selection

Use checked sources from `SKILL.md` by default. If a checked source is not configured, skip it and report the reason.

## Sources

| Source | Best use | Limits |
| --- | --- | --- |
| Scopus | Primary peer-reviewed recall, EID, DOI, citation count, publication venue | Requires Elsevier key and entitlement |
| Elsevier Abstract Retrieval | Abstract and richer metadata for Scopus candidates | Use after title triage, not for bulk discovery |
| OpenAlex | Broad open metadata, concepts, citation and OA clues | Metadata quality varies by record |
| Crossref | DOI, venue, publisher, issue/page metadata | Abstracts are often absent |
| Semantic Scholar | Citation count, abstracts, fields, related discovery | Coverage and rate limits vary |
| Unpaywall | OA status and OA URL when DOI is known | Not a keyword search source |
| paper-rank-proxy | Journal rank annotation | Requires publication name, not ISSN-only |

## Default Call Pattern

1. Run `list_literature_sources`.
2. Use Scopus as the primary recall source when configured.
3. Add OpenAlex, Crossref, and Semantic Scholar as supplementary recall sources.
4. Use Unpaywall only after DOI extraction.
5. Use rank proxy only after candidate venues are known.

## Future Sources

IEEE Xplore, ScienceDirect Search, and Web of Science remain unchecked until API access, connector implementation, and tests are complete.
