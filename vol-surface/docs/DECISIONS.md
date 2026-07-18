# Decisions (ADR log)

> One entry per architectural decision. Append-only, newest on top.
> State the decision, not a claim of truth — hedge to the evidence, stamp the date.

## 011. `expiry_mask` — drop same-day/expired (T=0) contracts; settlement-time T stays deferred — 2026-07-17
- **Decision:** Added `expiry_mask(df, min_T=0.0)` as a v1 validity filter (drops `T ≤ min_T`; default 0 drops same-day/expired). `T` is calendar-days/365, so a same-day expiry lands exactly on 0. Granular settlement-time T remains deferred.
- **Why:** The pinned 07-13 snapshot was taken at 21:19 (after close), so it carried 490 expired 0DTE contracts (1.66% of the raw chain, all the 07-13 expiry). `bidask` + OTM incidentally remove all but one, which reached the pricer and pinned the bisection solver at its σ=500 ceiling — at T=0 the option is pure intrinsic for *any* σ (Black-76 `d1/d2` divide by `σ√T = 0`), so no IV exists. A finer clock would give tiny positive T, but past-settlement contracts still need dropping, so the filter is required regardless. `cboe_iv` on a T=0 option is itself fabricated (CBOE floors T).
- **Trade-off:** Drops 0DTE / very-short-dated points (marginal for a term-structure surface). Settlement-time T — the more accurate near-term fix, which would also dissolve the AM/PM zigzag (ADR 004) — stays parked pending timezone verification of the CBOE timestamp.

## 010. Own IV pricer: Black-76 off the parity forward, bisection solver, scipy added — 2026-07-17
- **Decision:** `engine/blackscholes.py` = `bs_price` (Black-76 — prices off the parity forward `F`, discounts by `e^{-rT}`, needs only `r`) + `implied_vol` (vectorized bisection on σ ∈ [1e-6, 5], since price is monotone in σ). Added `scipy` as a core dependency (`scipy.special.ndtr` for the normal CDF). `bs_vega` and a Newton solver are deferred.
- **Why:** Black-76 is self-consistent with the parity forward and `ln(K/F)` axis (ADR 003) and sidesteps a dividend `q`. Bisection is bulletproof and vectorizes trivially (identical per-step op across all contracts), and 13.5k contracts invert instantly — speed isn't the constraint. Validated two ways: our IV matches `cboe_iv` to **0.14 vp median** (corr 0.9997), and a synthetic vol round-trip (invent σ → price → invert) recovers σ to **3.8e-7**. `ndtr` is the standard C-vectorized normal CDF; hand-rolling risked tail-accuracy bugs, and SVI (v3) needs scipy anyway.
- **Trade-off:** Bisection is slower than Newton/Jäckel (irrelevant at this scale; Newton is the deferred speed upgrade, and needs `bs_vega`). scipy relaxes ADR 007's minimal-deps stance — justified. Price round-trip is ~1e-3, not 1e-6, because `eps` is a tolerance in *vol* space and price error ≈ `vega × vol_error` — the IV itself is accurate to ~1e-6.

## 009. v1 filters simplified to OTM + bid/ask; staleness dropped, spread filter → pricer — 2026-07-14
- **Decision:** v1 clean pipeline = OTM-selection + `bid/ask>0` only. `staleness_mask` dropped from the default (kept available in `engine/filters.py`, like `volume_mask`). The spread-outlier filter (median+MAD) is promoted from "someday" to the **pricer milestone** (v2).
- **Why:** On the pinned snapshot, `staleness ≤ 7d` dropped ~half of each slice's OTM quotes — and the dropped ones were *tight, never-traded* market-maker quotes (median spread 1.6%, all `last_trade = NaT`). We price off the **mid**, so a two-sided quote is usable whether or not it ever traded; staleness was discarding good data. Dropping it keeps ~46% of the chain (vs ~39%) with no loss of smile quality, and the forward's *median* is unchanged (7536.2 → 7536.3 — the extra per-strike scatter is wing dispersion the median steps over). The genuinely bad quotes are the **wide wings** (40–57% relative spread), which the spread filter targets — but `cboe_iv` (v1) is CBOE-smoothed and stays clean despite them. Our own mid-based IV (v2) won't be, so the spread filter lands there.
- **Trade-off:** v1 keeps some wide wing quotes (harmless under `cboe_iv`; must be filtered once IV comes from the mid). Supersedes the staleness portion of ADR 008.

## 008. Filters revised: drop volume, use OTM + bid/ask + staleness — 2026-07-13
> **Superseded in part (2026-07-14):** the `staleness` portion is dropped by ADR 009 (it discards tight never-traded quotes; v1 = OTM + bid/ask).
- **Decision:** v1 filters = OTM-selection + `bid/ask>0` + `staleness_mask` (last trade within N days, default 7). `volume>0` is dropped from the default pipeline (`volume_mask` kept as an available function). Spread-outlier (median+MAD preferred over mean+Nσ) and monotonicity stay deferred.
- **Why:** EDA on live intraday data showed `volume>0` is identical to "traded today" (same keep-set as last-trade ≤ 1d), dropping ~61% and *asymmetrically* gutting the untraded wing (e.g. OTM calls on a down day) — fragile for a run-anytime tool. `OTM + bid/ask` alone gives a clean, full, both-wings smile (median quote width 1.7%); `staleness ≤ 7d` is a leaner, less path-dependent liquidity gate. Quote-based filters are direction/time-independent.
- **Trade-off:** Staleness is still trade-based, so a *sustained* one-directional market could thin the quiet side (far less than volume). The deferred spread-outlier via **median+MAD** is the more principled gate (robust to the masking effect that breaks mean+Nσ). Supersedes the volume portion of ADR 005.

## 007. Packaging: pyproject + hatchling (editable install), drop requirements.txt — 2026-07-12
- **Decision:** `vol-surface` is an installable package via `pyproject.toml` (hatchling backend); `engine` is the package. Install with `pip install -e .` (core) or `pip install -e ".[dev]"` (adds `ipykernel` for notebooks). The 108-line `pip freeze` `requirements.txt` is deleted. Core deps: pandas, numpy, matplotlib, requests. Dev extra: ipykernel.
- **Why:** Notebooks moved to `notebooks/`, breaking cwd-based imports. An editable install makes `engine` importable from any cwd with no `sys.path` hacks and scales to N notebooks with one setup. Hatchling leaves no `.egg-info` in the source tree (setuptools does). Splitting notebook tooling into a `[dev]` extra keeps `engine`'s runtime deps honest — the library doesn't need Jupyter to function.
- **Trade-off:** Lost the pinned-version lockfile (exact reproducibility) the frozen `requirements.txt` gave; pyproject lists loose deps. Re-pin later if exact repro is needed.

## 006. v1 scope = clean + visualize raw data, no fitting — 2026-07-11
- **Decision:** The current sprint plots the *raw* cleaned surface (scatter, no fit), using CBOE's `iv` field to validate the clean→slice→surface pipeline end-to-end. Our own Black-Scholes IV, and SVI fitting, are subsequent milestones.
- **Why:** De-risks the pipeline (viz works independent of BS correctness) and gets a cleaned surface on screen fast; Ben's stated goal is "most signal down, cleaned + visualized" before modeling.
- **Trade-off:** The v1 surface shows CBOE's IV, not ours — the own-pricer milestone must swap it in before any correctness claim about our solver.

## 005. Filters: v1 = bid/ask>0 + volume>0; heavier filters deferred — 2026-07-11
> **Superseded in part (2026-07-13):** the `volume>0` choice here is reversed by ADR 008 (volume is asymmetric/fragile intraday).
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
- **Trade-off:** Recruiters can't diff the exact input data, and a live run sees a *different* (current) chain than the committed outputs; exact-number reproducibility depends on the local dated snapshot, which isn't shared.
- **Update (2026-07-14):** re-read of `cboe.com/terms` confirmed the redistribution ban is explicit and unqualified by commercial intent (*"...store ... in an electronic retrieval system, ... publish, ... distribute ... without Cboe's prior written consent"*), reaffirming the no-commit decision. The previously-flagged "auto-extraction / IP-blocking" clause does **not** exist on the terms page (refuted — it was in a separate vendor-only data policy that doesn't bind anonymous endpoint users). No attribution requirement applies to us either.

## NNN. <short decision title> — YYYY-MM-DD
- **Decision:** what was chosen
- **Why:** the reasoning / evidence it rests on
- **Trade-off:** what this costs or what was given up
