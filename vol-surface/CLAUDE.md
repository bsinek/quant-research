# vol-surface

Volatility surface construction and analysis.

## Docs
- `docs/plans/` — dated implementation plans (`YYYY-MM-DD-<slug>.md`). Acceptance criteria live in the plan (written before building) and become the tests. Plans are a historical archive, not current truth.
- `docs/DECISIONS.md` — single ADR log (Decision / Why / Trade-off), hedged, dated, newest on top. One entry per real decision-with-a-tradeoff.
- `docs/ARCHITECTURE.md` — the map: how the pieces fit + one top-level Mermaid diagram. Short; per-piece API/behavior detail lives in code docstrings.
- `docs/STATE.md` — date-stamped snapshot (working / in flight / next / deferred). Update at every phase-boundary commit, in the same commit — update ARCHITECTURE if structure changed, append DECISIONS if a decision-with-a-tradeoff was made. Never promote a deferred idea into Next without Ben.

## Durable truth
- Acceptance criteria → in the plan, become the tests (the executable oracle).
- Per-piece API/behavior → code docstrings + types (co-located, never drifts).
- How the pieces fit → `docs/ARCHITECTURE.md`. Why → `docs/DECISIONS.md`.
- The plan → archived in `docs/plans/` as dated history; not maintained.
