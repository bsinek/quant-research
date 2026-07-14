# State

> Date-stamped snapshot of where the project stands. Rewrite freely — it's a snapshot, not a log.

**Last updated:** 2026-07-14

## Working
_Built and functioning now. (API detail lives in the code — see `engine/*.py` docstrings.)_
- `engine/data.py` — SPX chain fetch / disk-cache / tidy-frame conversion. Built, verified.
- `engine/filters.py` — `bidask_mask` (v1 filter) + `staleness_mask` / `volume_mask` (available, both dropped from the default; ADR 009 / 008). Built.
- `engine/surface.py` — `implied_forwards` / `forward_by_expiry` / `select_otm` (parity forward + OTM selection). Built, verified.
- `notebooks/eda.ipynb` — evidence-doc EDA: coverage → convergence → forward(parity QC) → filters(raw→clean) → smile → term structure. Pinned to the 2026-07-13 snapshot, committed with rendered outputs. v1 filters = OTM + bid/ask (ADR 009), IV = `cboe_iv` (ADR 006).
- Packaging — `pyproject.toml` (hatchling) editable install.
- Docs: README, DECISIONS, ARCHITECTURE, plan.

## In flight
_Actively being worked on._
- (none — EDA shipped.)

## Next
_The committed next 1–2 steps._
1. **Own-pricer (v2)** — Ben writes `blackscholes.py` (price + vega) + `impliedvol.py` (solver). Swap `cboe_iv` → our IV in the pipeline; **validate our IV against `cboe_iv`** (the oracle). Add the **spread-outlier filter** (median+MAD) — now needed, since mid-based IV lacks CBOE's smoothing and the wide wings (40–57% spread) would go noisy (ADR 009).
2. **The surface / grid (v3)** — resample the clean slices onto a regular `(moneyness, T)` grid; SVI/SSVI fit → smooth, arbitrage-free surface (fills the ragged fan, √T scaling baked in). Then render the full 3D surface with *our* IV. No-arb (monotonicity) check.

## Ideas (deferred)
_Parking lot, uncommitted._
- **√T-scaled / delta-band moneyness range** at the grid/fit stage — the raw cube is a ragged fan in `ln(K/F)`; a risk-adjusted axis makes slices comparable across maturity (near-term ±0.05 = ±14σ; far-term ±0.9 = ±5σ). This is the SSVI-native fix.
- **Richer-root-at-overlap** — at the 5 SPX/SPXW collision dates, default SPXW covers the practical smile; consider `max(SPXW, SPX)` by strike-count beyond ~30d to grab SPX's deep-tail wings (converged there, so ~free). Only matters if modeling deep-tail skew.
- Monotonicity (no-arb) filter — longest-monotonic-subsequence; good résumé showcase.
- True-settlement-time `T` (AM 9:30 ET / PM 16:00 ET) — dissolves the AM/PM zigzag; isolated to `data.py`; needs timezone verification of the CBOE `timestamp`. (Note: the "0.3 vp long-end zigzag" from ADR 004 sits uneasily with this session's convergence finding of ~0.04 vp far-out — re-measure before trusting.)
- Mid-session vs frozen-close snapshot for the pinned data — mid-session has tighter spreads but async cross-sectional wobble (moving market); a frozen close is smoother. Current pin = 07-13 after-close (smooth). Revisit when re-pinning.
- v3 ML / no-arb; purchased 2022 SPX history as a replay source.
