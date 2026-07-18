# Architecture

> Current-state technical design of the system. Update via the cascade rule when structure changes.

## Overview

Builds an SPX implied-volatility surface from CBOE's delayed option chain. The flow is a
linear pipeline: **fetch → clean → construct → price**, one tidy contract frame threaded
through each stage. Each stage is a small module with one responsibility; detail lives in the
code docstrings, not here.

```mermaid
flowchart LR
    CBOE[(CBOE feed)] --> data[data.py<br/>fetch / cache / tidy-frame]
    data --> filters[filters.py<br/>quality masks]
    filters --> surface[surface.py<br/>parity forward + OTM]
    surface --> bs[blackscholes.py<br/>Black-76 price + IV]
    bs -.-> grid[grid / SVI fit<br/>not built]
```

## Components
_Each major unit and its single responsibility._

- **`data.py`** — the only place the data source lives. Fetches the SPX chain from CBOE's
  delayed feed, freezes dated snapshots to disk, and flattens the JSON into one tidy row per
  contract. Swapping to purchased history touches nothing downstream.
- **`filters.py`** — contract-quality masks (each takes the frame, returns a boolean keep-mask,
  composes with `&`). v1 defaults: `bidask_mask` + `expiry_mask`. Available but off by default:
  `staleness_mask`, `volume_mask` (ADR 008/009). Cleaning only — never modifies a row.
- **`surface.py`** — *construction*, not cleaning: derives each expiry's forward `F` from
  put-call parity (`forward_by_expiry`), then uses it to pick the reliable OTM side
  (`select_otm`) and place the `ln(K/F)` moneyness axis. Depends on the modeled forward, so it
  runs **after** the quote filters (the forward is computed from the surviving set).
- **`blackscholes.py`** — Black-76 pricing off the parity forward. `bs_price` maps σ → price;
  `implied_vol` inverts price → σ numerically (vectorized bisection). CBOE's `iv` is the
  validation oracle, never an input (ADR 010).

## Data / interfaces
_Key data models and the durable interface surface._

- **Tidy contract frame** (`chain_to_frame`): one row per option. Columns `root, expiry, T,
  type ('C'/'P'), strike, bid, ask, mid, volume, open_interest, last_trade_time, cboe_iv`;
  snapshot `spot` / as-of `asof` in `df.attrs`. `surface.py` attaches `F` (forward per expiry).
- **Pipeline order matters at one seam:** per-row quote masks commute freely, but the forward /
  OTM step reads the whole surviving set to compute `F`, so it must run after cleaning.
- **Price convention:** mid, `T` = calendar-days/365 (ADR 002); forward via parity, rate `r`
  the only free input (ADR 003).
