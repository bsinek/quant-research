# SPX IV Surface — Design Spec & v1 Plan

**Date:** 2026-07-10 · **Status:** design agreed; v1a not yet built
**Author of record:** brainstormed with Ben; Ben writes the finance core.

## Goal

From a single SPX option-chain snapshot, back out implied volatility per contract
and render the 3D volatility surface. Built so that live / replay / backtest are
later *additions*, not rewrites.

## Roadmap — the ladder

Each rung stands on the one below it. No rung is a rewrite of the prior.

| Rung | What it is | Where the hard part lives |
| --- | --- | --- |
| **v1a — raw surface** *(current milestone)* | Back out IV from market prices; plot IV vs spot-log-moneyness `ln(K/S)`, **calls only**. Ugly-but-real surface on screen. | Data, cleaning, the solver |
| **v1b — forward-corrected** | Compute forward `F` per expiry; switch axis to `ln(K/F)`; stitch OTM puts + calls. Smiles center. | Forward + put-call parity |
| **v2 — SVI fit** | Fit a Gatheral SVI smile per expiry *through* the v1 dots; overlay curve on dots. | Curve fitting |
| **v3 — ML / no-arb** | Fancier smoothing (spline / GP / NN) with butterfly + calendar no-arbitrage checks. | Arbitrage constraints |

## Why raw-first (v1a before SVI)

SVI is not a version of the surface — it is a curve fit *through* the surface's
points. It has nothing to fit until the raw IVs are backed out. If v1a is wrong,
SVI fits garbage smoothly and you never notice. The resume-strong visual is raw
dots + SVI curve overlaid; that requires v1a to exist first.

## Architecture — one pure core, swappable edges

```
 SPX data adapter  ─►  normalized chain  ─►  [ C O R E ]  ─►  surface grid  ─►  3D plot
   (swappable)          (fixed schema)       pure function     (IV by moneyness, T)  (notebook)
```

The **core** is a pure function `normalized chain snapshot → surface`. The data
adapter and the plotter are the swappable edges. Later, live / replay / backtest
are just different *drivers* calling this same unchanged core — that is what buys
additions-not-rewrites.

| File | Responsibility | Author |
| --- | --- | --- |
| `data.py` | Fetch SPX chain, parse symbols, normalize to the fixed schema. The **only** place the data source lives. | me (on request) |
| `blackscholes.py` | BS price + vega | **Ben** |
| `impliedvol.py` | Invert BS per contract (Newton via vega, Brent fallback) | **Ben** |
| `surface.py` | Clean / filter, `T` in years, (v1b) imply forward, pick OTM, build the IV grid | pair |
| `plot.py` | 3D surface render helper | me (on request) |
| `notebook.ipynb` | Import the above; tell the story; show the surface | pair |
| `tests/` | Textbook-value + round-trip + CBOE-oracle tests | pair |

## Data source — CBOE free delayed quotes (verified 2026-07-10)

- Endpoint: `https://cdn.cboe.com/api/global/delayed_quotes/options/_SPX.json`
  (index symbols take a leading underscore). HTTP 200, ~13 MB, ~29k contracts.
- **Spot:** `data.current_price`.
- **Per-contract fields used:** `option` (symbol), `bid`, `ask`, `bid_size`,
  `ask_size`, `volume`, `open_interest`, `last_trade_price`.
- **Validation oracle:** CBOE also returns `iv`, `delta/gamma/vega/theta/rho`,
  and `theo` per contract. We compute our own IV/Greeks and *validate against*
  CBOE's — never use CBOE `iv` as an input.
- **Symbol format (OCC/OSI):** `SPX260717C00200000` = root + `YYMMDD` expiry +
  `C|P` + strike×1000. Roots seen: `SPX` (AM-settled monthly) and `SPXW`
  (PM-settled weekly).
- **Not in the feed** — supplied as inputs: risk-free rate `r`, dividend yield `q`.
  v1a uses flat constants; refine later (curve / imply-from-parity).
- Data is delayed / last-close — fine for a static snapshot.
- **Later:** purchased SPX history (2022-01-01 → 2022-03-31) drops in behind the
  same normalized schema as a *replay* source; nothing downstream changes.

## Normalized chain schema (`data.py` output)

Per contract row: `expiry` (date), `T` (years), `type` (`C`/`P`), `strike`,
`bid`, `ask`, `mid`, `volume`, `open_interest`, `cboe_iv` (validation only).
Snapshot-level: `spot`, `timestamp`.

## v1a — scope & acceptance criteria

Acceptance criteria are written before building and become the tests.

**Scope:** calls only, spot-log-moneyness, one live snapshot, raw dots (no fit).

1. `blackscholes.bs_price` matches independent reference values to ≤ 1e-6;
   `bs_vega` matches a finite-difference check to ≤ 1e-6.
2. `impliedvol.implied_vol` round-trips: price at a known σ, recover σ to ≤ 1e-6.
3. On liquid near-ATM CBOE contracts, our IV matches CBOE `iv` within 0.5 vol pts.
4. `data` fetches, parses ≥ 3 known symbols correctly, and emits the schema.
5. Filtering drops zero-volume / zero-size / crossed-quote / non-positive-mid rows.
6. Notebook renders a 3D surface (IV vs `ln(K/S)` vs `T`) from one live snapshot.

## Who writes what

- **Ben:** `blackscholes.py`, `impliedvol.py` — the interview surface. Claude
  guides and reviews; touches code only when Ben says so.
- **Claude (on request):** `data.py`, `plot.py`, test harness.

## Deferred / open

- `r`, `q` sourcing — flat constant now; curve or imply-from-parity later.
- `SPX` vs `SPXW` handling — v1a may include both; revisit if it muddies the grid.
- SPX is European + cash-settled, so Black-Scholes' assumptions hold (this is why
  SPX was chosen over SPY).
