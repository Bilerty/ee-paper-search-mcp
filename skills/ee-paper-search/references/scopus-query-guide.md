# Scopus Query Guide

Use Scopus for structured, high-precision recall. Start broad, inspect titles, then narrow.

## Patterns

Broad recall:

```text
TITLE-ABS-KEY(("power system" OR "distribution network" OR microgrid) AND (fault OR outage OR resilience) AND (optimization OR restoration OR reconfiguration))
```

Title-focused recall:

```text
TITLE(("distribution network" AND restoration) OR ("service restoration" AND microgrid))
```

Recent work:

```text
TITLE-ABS-KEY(("resilience-oriented" OR resilience) AND ("optimal power flow" OR restoration)) AND PUBYEAR > 2019
```

## Rules

- Put exact phrases in quotes.
- Use synonyms for power systems terms: distribution network, distribution system, microgrid, active distribution network, integrated energy system.
- Use method synonyms: restoration, reconfiguration, optimal power flow, dispatch, resilience, fault recovery.
- Avoid over-narrow first queries; narrow after title inspection.
- Prefer `TITLE-ABS-KEY` for first recall and `TITLE` for precision passes.
