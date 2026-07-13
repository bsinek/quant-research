# Decisions (ADR log)

> One entry per architectural decision. Append-only, newest on top.
> State the decision, not a claim of truth — hedge to the evidence, stamp the date.

## 007. Packaging: pyproject + hatchling (editable install), drop requirements.txt — 2026-07-12
- **Decision:** `vol-surface` is an installable package via `pyproject.toml` (hatchling backend); `engine` is the package. Install with `pip install -e .` (core) or `pip install -e ".[dev]"` (adds `ipykernel` for notebooks). The 108-line `pip freeze` `requirements.txt` is deleted. Core deps: pandas, numpy, matplotlib, requests. Dev extra: ipykernel.
- **Why:** Notebooks moved to `notebooks/`, breaking cwd-based imports. An editable install makes `engine` importable from any cwd with no `sys.path` hacks and scales to N notebooks with one setup. Hatchling leaves no `.egg-info` in the source tree (setuptools does). Splitting notebook tooling into a `[dev]` extra keeps `engine`'s runtime deps honest — the library doesn't need Jupyter to function.
- **Trade-off:** Lost the pinned-version lockfile (exact reproducibility) the frozen `requirements.txt` gave; pyproject lists loose deps. Re-pin later if exact repro is needed.

## 006. v1 scope = clean + visualize raw data, no fitting — 2026-07-11
- **Decision:** The current sprint plots the *raw* cleaned surface (scatter, no fit), using CBOE's `iv` field to validate the clean→slice→surface pipeline end-to-end. Our own Black-Scholes IV, and SVI fitting, are subsequent milestones.
- **Why:** De-risks the pipeline (viz works independent of BS correctness) and gets a cleaned surface on screen fast; Ben's stated goal is "most signal down, cleaned + visualized" before modeling.
- **Trade-off:** The v1 surface shows CBOE's IV, not ours — the own-pricer milestone must swap it in before any correctness claim about our solver.

## 005. Filters: v1 = bid/ask>0 + volume>0; heavier filters deferred — 2026-07-11
- **Decision:** v1 keeps `bid>0 & ask>0 & volume>0` plus OTM-selection off the forward. Monotonicity (no-arb), spread-outlier, and true-settlement-time `T` are deferred to a final polish pass.
- **Why:** The two cheap filters remove the bulk of the garbage (64% zero-volume; the exploding wings). `volume>0` (per-day, fresh) is the workhorse; OI is near-redundant (removes only ~461 more) and lags EOD, so it is not required. The heavier filters are legit but lower marginal value for a raw scatter.
- **Trade-off:** The raw v1 surface keeps minor artifacts (residual noisy points, the AM/PM zigzag) that the deferred filters + SVI would clean.

## 004. Root/expiry: keep all expiries, prefer SPXW, dedupe only same-date collisions — 2026-07-11
- **Decision:** Use each expiry's available series; on the 5 same-date 3rd-Friday collisions (both SPX+SPXW), prefer SPXW. Keep all expiries including SPX-only long-dated LEAPS. No clean cutover.
- **Why:** Dropping SPX would amputate the long end (LEAPS to 2031); forcing a cutover would delete real SPXW quarterly expiries (12-31, 03-31, 06-30) to hide a cosmetic seam. Preferring SPXW keeps the near/mid term on one PM-settled series (no monthly notches).
- **Trade-off:** A ~0.3-vol-point AM/PM zigzag remains in the long-end term structure. The proper fix is true-settlement-time `T` (deferred), not root-picking.

## 003. Forward implied via put-call parity — 2026-07-11
- **Decision:** Compute the per-expiry forward `F` from put-call parity (`F = K + e^{rT}(C−P)` at liquid strikes), not `F = S·e^{(r−q)T}` with a dividend forecast. Moneyness axis = `ln(K/F)`.
- **Why:** Parity reads the market's combined (r−q) directly off option prices, is self-consistent with the prices being modeled, and sidesteps guessing SPX's dividend yield. Verified flat (~7,581) across all strikes.
- **Trade-off:** Needs a liquid call+put pair per expiry (fine near ATM); still needs a rate `r` (small, known), though not `q`.

## 002. Price = mid; day count = calendar/365 — 2026-07-11
- **Decision:** Use the bid/ask **mid** as the option price (not last-traded or settlement). Compute `T` as calendar-days/365.
- **Why:** Mid is current (last-traded is stale — weeks-old prints observed) and available in both the live feed and purchased EOD data (settlement is EOD-only) → portable across live/replay. Calendar/365 matches how CBOE measures time, so our IV can match the `cboe_iv` oracle (252-vs-365 shifts IV by √(252/365)≈0.83 unless consistent).
- **Trade-off:** Calendar/365 is a standard approximation; true intraday settlement times (AM open vs PM close) are ignored for now, leaving the small AM/PM offset.

## 001. Data fetched at runtime, gitignored, not committed — 2026-07-10
- **Decision:** The SPX chain is pulled live from CBOE's free delayed feed by `engine/data.py` and frozen to a dated file under `data/`, which is gitignored. The notebook is committed with rendered outputs; the raw chain is never committed.
- **Why:** CBOE's website terms (read 2026-07-10) license the data for personal, non-commercial use and prohibit redistribution/publishing; committing the chain to a public repo would be redistribution. Fetch-at-runtime keeps use within personal-use bounds and still lets anyone reproduce the notebook.
- **Trade-off:** Recruiters can't diff the exact input data, and a live run sees a *different* (current) chain than the committed outputs; exact-number reproducibility depends on the local dated snapshot, which isn't shared. The unverified "auto-extraction / IP-blocking" clause (seen in one search summary, not confirmed on the terms page) is a residual risk.

## NNN. <short decision title> — YYYY-MM-DD
- **Decision:** what was chosen
- **Why:** the reasoning / evidence it rests on
- **Trade-off:** what this costs or what was given up
