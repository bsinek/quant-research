"""Black-76 option pricing and implied-vol inversion.

Prices European options off the forward ``F`` (Black-76): needs only ``r``, no
dividend ``q`` — self-consistent with the parity forward and ``ln(K/F)`` axis
(ADR 003).

``implied_vol`` inverts price → σ numerically: no closed form exists (σ is trapped
inside the normal CDF), so we search for the σ whose Black-76 price matches the
market mid. CBOE's ``iv`` is the validation oracle, never an input here.
"""
from __future__ import annotations

import numpy as np
from scipy.special import ndtr


def bs_price(F, K, T, sigma, opt_type, r = 0.04) -> np.ndarray:
    """Black-76 European option price(s) off the forward. opt_type 'C'/'P'; vectorized."""
    F, K, T, sigma = (np.asarray(x, dtype=float) for x in (F, K, T, sigma))
    cp_sign = np.where(np.asarray(opt_type, dtype=str) == 'C', 1, -1)
    d1 = (np.log(F / K) + sigma**2 * T * 0.5) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)

    return cp_sign * np.exp(-r * T) * ((F * ndtr(cp_sign * d1)) - (K * ndtr(cp_sign * d2)))


def implied_vol(price, F, K, T, opt_type, r = 0.04, eps = 1e-8, max_iter = 50) -> np.ndarray:
    """Implied vol σ reproducing ``price`` under Black-76, found numerically. Vectorized.

    Safeguarded Newton (``rtsafe``): a Newton step ``σ -= (price(σ)-target)/vega`` inside a
    bracket ``[lo, hi]`` that provably contains the root (Black-76 price is monotone in σ).
    Each step tightens the bracket by the sign of the residual; where the Newton point escapes
    the bracket or vega≈0 makes the step blow up (deep wings), that element takes a bisection
    step instead — so it converges to machine precision in ~6 iterations yet cannot diverge.
    The upper bound is not hardcoded: ``hi`` starts at 1.0 and doubles until it brackets the
    root (``zbrac``), so a 300% crash-put IV is discovered dynamically rather than capped. Junk
    quotes with no finite root expand to the loop guard and get dropped by the downstream screen.
    """
    price, F, K, T = (np.asarray(x, dtype=float) for x in (price, F, K, T))
    opt_type = np.asarray(opt_type, dtype=str)

    lo = np.full(price.shape, 1e-6)                         # vol > 0, a natural floor (not magic)
    hi = np.full(price.shape, 1.0)
    for _ in range(20):                                     # expand hi until it brackets the root
        under = bs_price(F, K, T, hi, opt_type, r) < price  # model price still below market → root above hi
        if not np.any(under):
            break
        hi = np.where(under, hi * 2, hi)                    # double only the not-yet-bracketed
    sigma = np.full(price.shape, 0.2)                       # seed; safeguarding recovers bad seeds
    for _ in range(max_iter):
        diff = bs_price(F, K, T, sigma, opt_type, r) - price
        hi = np.where(diff > 0, sigma, hi)                  # price too high -> root is below σ
        lo = np.where(diff < 0, sigma, lo)                  # price too low  -> root is above σ
        vega = bs_vega(F, K, T, sigma, r)
        newton = sigma - diff / np.where(vega > 1e-12, vega, np.nan)
        unsafe = ~np.isfinite(newton) | (newton <= lo) | (newton >= hi)
        step = np.where(unsafe, 0.5 * (lo + hi), newton)    # bisect where Newton is out of bounds
        if np.all(np.abs(step - sigma) < eps):
            return step
        sigma = step

    return sigma


def bs_vega(F, K, T, sigma, r = 0.04) -> np.ndarray:
    """Black-76 vega dPrice/dSigma (per 1.00 of vol), identical for calls and puts. Vectorized.

    Weights the SVI fit: a wide spread on a high-vega quote still pins σ tightly, so
    vol uncertainty ≈ spread / vega. Also the derivative a Newton IV solve divides by.
    ``phi`` here is the standard-normal *density*, not the CDF ``ndtr``.
    """
    F, K, T, sigma = (np.asarray(x, dtype=float) for x in (F, K, T, sigma))
    d1 = (np.log(F / K) + sigma**2 * T * 0.5) / (sigma * np.sqrt(T))
    phi = np.exp(-0.5 * d1**2) / np.sqrt(2 * np.pi)

    return np.exp(-r * T) * F * np.sqrt(T) * phi
