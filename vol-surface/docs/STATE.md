# State

> Date-stamped snapshot of where the project stands. Rewrite freely — it's a snapshot, not a log.

**Last updated:** 2026-07-20 (branch `feat/svi-ssvi-surface`)

## Working
_Built and functioning now. (API detail lives in the code — see `engine/*.py` docstrings.)_
- `engine/data.py` — SPX chain fetch / disk-cache / tidy-frame conversion. Built, verified.
- `engine/filters.py` — `bidask_mask` + `expiry_mask` (v1 filters) + `staleness_mask` / `volume_mask` (available, dropped from the default; ADR 009 / 008). Built.
- `engine/surface.py` — `implied_forwards` / `forward_by_expiry` / `select_otm` + `blend_roots` (one root per expiry: SPXW ≤60d, richest beyond; shared by both surface notebooks, ADR 015). Built, verified.
- `engine/blackscholes.py` — `bs_price` (Black-76 off the parity forward) + `implied_vol` (safeguarded Newton–bisection) + `bs_vega` (∂price/∂σ, matches finite-diff). Validated vs `cboe_iv` (0.14 vp median, corr 0.9997; synthetic σ round-trip ~1e-14). ADR 010/014.
- `engine/svi.py` — `svi_w` + `fit_slice` (Zeliade quasi-explicit, vega/spread weighted) + `fit_surface` (per-expiry; reports vol-pt `rmse_vol`, ~0.28 median on 07-13) + `svi_g` (butterfly `g(k)≥0`). Synthetic recovery ~4e-7; `g` matches Breeden-Litzenberger density 100%. ADR 012/014.
- `engine/ssvi.py` — `ssvi_w` + `fit_ssvi` (global `(ρ,η,γ)`, GJ Thm 4.2 butterfly-constrained → arb-free by construction) + `atm_theta`. Synthetic recovery ~2e-14. ADR 013.
- `engine/metrics.py` — `surface_metrics` (ATM vol, 25d skew, 25d fly/curvature per expiry) + `forward_vol` (event radar between expiries) + `butterfly_free_fraction`. Built.
- `notebooks/surface_svi.ipynb` — SVI+SSVI end to end: quotes → raw SVI per expiry → butterfly/calendar checks → 3D surface → term-structure metrics → global arb-free SSVI. Self-contained; **code verified to run clean, but outputs are stale after the Newton-solver + root-blend edits — needs Ben to re-run + commit rendered outputs.** On 07-13: 12,091 quotes / 55 expiries, 55/55 SVI-fit, ~0.27 vol-pt median fit error, ~98% butterfly-free, θ_T monotone, SSVI arb-free (rmse ~1 vol pt vs per-slice).
- `notebooks/surface.ipynb` — the 3D surface from **our** solver's IV: clean pipeline + shared root blend → invert every quote → raw scatter (dots only, no fit) + an all-expiries flat view. **Outputs stale after the Newton-solver + root-blend edits — needs re-run.** On the 07-13 snapshot: 12,091 clean OTM quotes, 100% solved.
- `notebooks/eda.ipynb` — evidence-doc EDA: coverage → convergence → filters(bid/ask + T>0, on strikes) → forward(parity QC) + OTM → smile → term structure. Cleaning and modeling are separate sections, mirroring `filters.py` vs `surface.py`. Pinned to the 2026-07-13 snapshot, committed with rendered outputs. v1 filters = bid/ask + T>0, then OTM (ADR 009/011), IV = `cboe_iv` (ADR 006).
- Packaging — `pyproject.toml` (hatchling) editable install.
- Docs: README, DECISIONS, ARCHITECTURE, plan.

## In flight
_Actively being worked on._
- (none — pricer + solver shipped.)

## Next
_The committed next 1–2 steps._
1. **Re-run both surface notebooks** (`surface.ipynb` + `surface_svi.ipynb`) and commit rendered outputs — stale after the Newton-solver + root-blend edits. Refresh the hardcoded numbers in `surface_svi.ipynb`'s summary cell to match. Then merge `feat/svi-ssvi-surface` to main.
2. **eSSVI** (θ-dependent ρ) — tightens the SSVI short-end fit (~2 vol pts today) toward the per-slice accuracy; natural follow-on to ADR 013.
3. CBOE-vs-ours side-by-side on the fitted surface; spread-outlier filter (median+MAD). All later polish. (Safeguarded-Newton solver — done, ADR 014.)

## Ideas (deferred)
_Parking lot, uncommitted._
- **√T-scaled / delta-band moneyness range** at the grid/fit stage — the raw cube is a ragged fan in `ln(K/F)`; a risk-adjusted axis makes slices comparable across maturity (near-term ±0.05 = ±14σ; far-term ±0.9 = ±5σ). This is the SSVI-native fix.
- **Richer-root-at-overlap** — at the 5 SPX/SPXW collision dates, default SPXW covers the practical smile; consider `max(SPXW, SPX)` by strike-count beyond ~30d to grab SPX's deep-tail wings (converged there, so ~free). Only matters if modeling deep-tail skew.
- Monotonicity (no-arb) filter — longest-monotonic-subsequence; good résumé showcase.
- True-settlement-time `T` (AM 9:30 ET / PM 16:00 ET) — dissolves the AM/PM gap at the root; isolated to `data.py`; needs timezone verification of the CBOE `timestamp`. (The ADR 004 ~0.3 vp figure vs the ~0.04 vp far-out finding is now resolved: EDA §2 measures 0.41 vp at 4 d falling to ~0.04 vp beyond 60 d — the 0.3 was near-term, the 0.04 the long end where the roots hand off. This is what ADR 015's 60-day cutoff rests on.)
- Mid-session vs frozen-close snapshot for the pinned data — mid-session has tighter spreads but async cross-sectional wobble (moving market); a frozen close is smoother. Current pin = 07-13 after-close (smooth). Revisit when re-pinning.
- ML / neural-net fit as an alternative to SVI; purchased 2022 SPX history as a replay source.
- **Configurable data dir** — `data.py`'s `_DATA_DIR` is `__file__`-relative, so it assumes the package sits inside the checkout; true only under `pip install -e .`, and a plain install silently points it at `site-packages/data`. Layer a `data_dir` param over an env var over today's default when it bites (the param is also what makes the module testable).
- **Surface readouts across dates** — `metrics.py` extracts ATM vol / 25d skew per snapshot; the remaining idea is comparing them *across* dates (event humps, skew regimes) once more snapshots are pinned. Curvature + event-hump flagging still unbuilt. Reading guide: https://claude.ai/code/artifact/a04fa49a-048f-49b7-9a7e-c91d531d94b7
