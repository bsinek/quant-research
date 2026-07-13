# SPX IV Surface — Design Spec & Plan

**Date:** 2026-07-10 (updated 2026-07-11) · **Status:** data layer built; v1 (clean + visualize) next
**Author of record:** brainstormed with Ben; Ben writes the finance core.

## Goal

From a single SPX option-chain snapshot, clean the data and render the 3D
volatility surface. Built so live / replay / backtest are later *additions*, not
rewrites.

## Roadmap — the ladder

| Rung | What it is | Focus |
| --- | --- | --- |
| **v1 — clean + visualize** *(current)* | Filter the chain, assemble the grid, plot one slice (the smile) then the full 3D surface as a **raw scatter, no fit**. IV comes from CBOE's `iv` field, to validate the clean→slice→surface pipeline end-to-end. | Data cleaning + visualization |
| **Own pricer** *(next)* | `blackscholes.py` (price + vega) + `impliedvol.py` (solver); swap CBOE `iv` → our own IV; validate against `cboe_iv`. | Ben writes — the interview surface |
| **v2 — SVI fit** | Fit a Gatheral SVI smile per expiry *through* the raw dots; overlay. | Smoothing / interpolation / no-arb |
| **v3 — ML / no-arb** | Optional fancier smoothing + butterfly/calendar checks. | Optional flourish |

Each rung stands on the one below. The fit (SVI/ML) only launders *random* noise
and fills gaps — *systematic* artifacts and garbage are cleaned upfront by the
filters, never left for the fit.

## Architecture — one pure core, swappable edges

```
 SPX data adapter  ─►  normalized chain  ─►  [ C O R E ]  ─►  surface grid  ─►  3D plot
   (swappable)          (fixed schema)       pure function     (IV by moneyness, T)  (notebook)
```

The **core** is a pure function `normalized chain snapshot → surface`. The data
adapter and the plotter are the swappable edges. Live / replay / backtest are
later just different *drivers* calling this same core.

| File | Responsibility | Author |
| --- | --- | --- |
| `data.py` | Fetch SPX chain, parse symbols, normalize to the fixed schema. **Built.** | me |
| `surface.py` | Filter, imply forward per expiry, OTM-select + stitch, build the (moneyness, T) IV grid | pair |
| `plot.py` | slice + 3D surface render helpers | me (on request) |
| `blackscholes.py` | BS price + vega | **Ben** |
| `impliedvol.py` | Invert BS per contract (Newton via vega, Brent fallback) | **Ben** |
| `surface.ipynb` | Import the above; tell the story; show the surface | pair |
| `tests/` | round-trip + CBOE-oracle tests | pair |

## Decisions (rationale + trade-offs in `docs/DECISIONS.md`)

- **Underlying:** SPX — European, cash-settled → clean Black-Scholes.
- **Price:** mid. **Day count:** calendar/365 (matches the `cboe_iv` oracle).
- **Forward:** implied via put-call parity; moneyness axis = `ln(K/F)`.
- **v1 filters:** `bid>0 & ask>0 & volume>0`, then **OTM-select off the forward** —
  OTM puts below `F`, OTM calls above `F`, **stitched at `F`** (max signal; not calls-only).
- **Root/expiry:** keep *all* expiries; prefer SPXW; dedupe only the 5 same-date
  3rd-Friday collisions.
- **Deferred to a final polish pass:** monotonicity (no-arb) filter, spread-outlier
  filter, true-settlement-time `T` refinement.

## Data source — CBOE free delayed quotes (verified 2026-07-10)

- Endpoint: `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json`
  (index symbols take a leading underscore). ~13 MB, ~29k contracts.
- **Spot:** `data.current_price`. **Snapshot time:** `timestamp`.
- **Validation oracle:** CBOE returns its own `iv` + Greeks + `theo` per contract.
  v1 plots CBOE `iv`; the own-pricer milestone computes ours and validates against it.
- **Symbol (OCC/OSI):** `SPX260717C00200000` = root + `YYMMDD` + `C|P` + strike×1000.
  Roots: `SPX` (AM-settled monthly + LEAPS), `SPXW` (PM-settled weekly/daily/EOM).
- **Not in the feed:** `r` (small, known — used in parity), `q` (sidestepped by parity).
- **Later:** purchased SPX history (2022-01-01 → 2022-03-31) drops in behind the
  same schema as a *replay* source.

## Normalized chain schema (`data.py` output)

Per contract row: `expiry` (date), `T` (years), `type` (`C`/`P`), `strike`, `bid`,
`ask`, `mid`, `volume`, `open_interest`, `cboe_iv`. Snapshot-level: `spot`, `asof`.

## v1 — scope & acceptance criteria

**Scope:** one live snapshot, cleaned, **raw scatter (no fit)**, IV from `cboe_iv`,
OTM puts + calls stitched at the forward, axis `ln(K/F)` vs `T`.

1. `data` fetches, parses ≥ 3 known symbols correctly, emits the schema.
2. Filter keeps only `bid>0 & ask>0 & volume>0` — the exploding wings are gone.
3. Forward computed per expiry via put-call parity (≈ flat across strikes).
4. OTM selection: puts below `F`, calls above `F`, stitched into one smile per expiry.
5. Notebook renders (a) one expiry **slice** (the smile) and (b) the **full 3D
   surface** (`ln(K/F)` × `T` × IV) from one snapshot.

## Own-pricer milestone — acceptance criteria (Ben writes)

1. `bs_price` matches independent reference to ≤ 1e-6; `bs_vega` matches finite-diff to ≤ 1e-6.
2. `implied_vol` round-trips: price at a known σ, recover σ to ≤ 1e-6.
3. On liquid near-ATM contracts, our IV matches `cboe_iv` within 0.5 vol points.

## Who writes what

- **Ben:** `blackscholes.py`, `impliedvol.py` (the interview surface); drives the build.
- **Claude (on request):** `data.py`, `plot.py`, filter/grid plumbing, tests.

## Deferred / open

- Own pricer swaps `cboe_iv` → our IV (next milestone).
- Monotonicity, spread-outlier, true-settlement-time `T` — final polish pass.
