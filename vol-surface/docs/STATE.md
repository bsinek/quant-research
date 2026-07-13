# State

> Date-stamped snapshot of where the project stands. Rewrite freely — it's a snapshot, not a log.

**Last updated:** 2026-07-12

## Working
_Built and functioning now. (API detail lives in the code — see `engine/data.py` docstrings.)_
- `engine/data.py` — SPX chain fetch / disk-cache / tidy-frame conversion. Built, verified.
- `engine/filters.py` — `volume_mask` / `bidask_mask` quality filters (parametrized floors, return boolean masks). Built.
- `engine/surface.py` — `implied_forwards` / `forward_by_expiry` / `select_otm` (parity forward + OTM selection). Built, verified.
- Packaging — `pyproject.toml` (hatchling) editable install; `requirements.txt` retired.
- Docs: README, DECISIONS, plan.

## In flight
_Actively being worked on._
- EDA notebook (`notebooks/eda.ipynb`) — forward-pipeline walkthrough + parity QC plot done; filter-comparison smiles / term structure / SPX-SPXW still to add. On a weekend snapshot; refresh on a market-hours pull. Uncommitted.

## Next
_The committed next 1–2 steps._
1. **`surface.py` grid** — build the (moneyness `ln(K/F)`, T) IV grid from the OTM-selected quotes (forward + OTM-select now done).
2. **EDA notebook** (Claude writes, Ben runs) — justify the filters (`volume>0` vs `bid/ask>0` vs both, the stitch, the term-structure flattening), then plot one **slice** (the smile) and the **full 3D surface** (`ln(K/F)` × `T` × IV) as a raw scatter, IV from `cboe_iv`. ~100–300 pts/slice.
3. **Own-pricer** — Ben writes `blackscholes.py` (price + vega) + `impliedvol.py` (solver); swap `cboe_iv` → our IV; validate against `cboe_iv`.

## Ideas (deferred)
_Parking lot, uncommitted._
- Monotonicity (no-arb) filter — longest-monotonic-subsequence; good résumé showcase.
- Spread-outlier filter (>Nσ per expiry).
- True-settlement-time `T` (AM 9:30 ET / PM 16:00 ET) — dissolves the AM/PM zigzag; isolated to `data.py`; needs timezone verification of the CBOE `timestamp`.
- v2 SVI fit; v3 ML / no-arb.
- Purchased 2022 SPX history as a replay source.
