# State

> Date-stamped snapshot of where the project stands. Rewrite freely — it's a snapshot, not a log.

**Last updated:** 2026-07-18

## Working
_Built and functioning now. (API detail lives in the code — see `engine/*.py` docstrings.)_
- `engine/data.py` — SPX chain fetch / disk-cache / tidy-frame conversion. Built, verified.
- `engine/filters.py` — `bidask_mask` + `expiry_mask` (v1 filters) + `staleness_mask` / `volume_mask` (available, dropped from the default; ADR 009 / 008). Built.
- `engine/surface.py` — `implied_forwards` / `forward_by_expiry` / `select_otm` (parity forward + OTM selection). Built, verified.
- `engine/blackscholes.py` — `bs_price` (Black-76 off the parity forward) + `implied_vol` (vectorized bisection). Built, validated vs `cboe_iv` (0.14 vp median, corr 0.9997; synthetic σ round-trip 3.8e-7). ADR 010.
- `notebooks/eda.ipynb` — evidence-doc EDA: coverage → convergence → filters(bid/ask + T>0, on strikes) → forward(parity QC) + OTM → smile → term structure. Cleaning and modeling are separate sections, mirroring `filters.py` vs `surface.py`. Pinned to the 2026-07-13 snapshot, committed with rendered outputs. v1 filters = bid/ask + T>0, then OTM (ADR 009/011), IV = `cboe_iv` (ADR 006).
- Packaging — `pyproject.toml` (hatchling) editable install.
- Docs: README, DECISIONS, ARCHITECTURE, plan.

## In flight
_Actively being worked on._
- (none — pricer + solver shipped.)

## Next
_The committed next 1–2 steps._
1. **Finish v2** — add the **spread-outlier filter** (median+MAD), needed once IV comes off the mid, since it lacks CBOE's smoothing and the wide wings (40–57% spread) go noisy (ADR 009). Then swap `cboe_iv` → our IV — but *not* in `eda.ipynb`: our IV is a model output, not observed data, so the pricer-vs-`cboe_iv` validation belongs in its own notebook (decided 2026-07-18). Optional polish: `bs_vega` + safeguarded-Newton solver (bisection works and is validated; Newton is a speed upgrade, not correctness).
2. **The surface / grid (v3)** — resample the clean slices onto a regular `(moneyness, T)` grid; SVI/SSVI fit → smooth, arbitrage-free surface (fills the ragged fan, √T scaling baked in). Then render the full 3D surface with *our* IV. No-arb (monotonicity) check.

## Ideas (deferred)
_Parking lot, uncommitted._
- **√T-scaled / delta-band moneyness range** at the grid/fit stage — the raw cube is a ragged fan in `ln(K/F)`; a risk-adjusted axis makes slices comparable across maturity (near-term ±0.05 = ±14σ; far-term ±0.9 = ±5σ). This is the SSVI-native fix.
- **Richer-root-at-overlap** — at the 5 SPX/SPXW collision dates, default SPXW covers the practical smile; consider `max(SPXW, SPX)` by strike-count beyond ~30d to grab SPX's deep-tail wings (converged there, so ~free). Only matters if modeling deep-tail skew.
- Monotonicity (no-arb) filter — longest-monotonic-subsequence; good résumé showcase.
- True-settlement-time `T` (AM 9:30 ET / PM 16:00 ET) — dissolves the AM/PM zigzag; isolated to `data.py`; needs timezone verification of the CBOE `timestamp`. (Note: the "0.3 vp long-end zigzag" from ADR 004 sits uneasily with this session's convergence finding of ~0.04 vp far-out — re-measure before trusting.)
- Mid-session vs frozen-close snapshot for the pinned data — mid-session has tighter spreads but async cross-sectional wobble (moving market); a frozen close is smoother. Current pin = 07-13 after-close (smooth). Revisit when re-pinning.
- v3 ML / no-arb; purchased 2022 SPX history as a replay source.
