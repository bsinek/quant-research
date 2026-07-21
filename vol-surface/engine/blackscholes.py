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


def implied_vol(price, F, K, T, opt_type, r = 0.04, eps = 1e-6) -> np.ndarray:
    """Implied vol σ reproducing ``price`` under Black-76, found numerically. Vectorized."""
    price, F, K, T = (np.asarray(x, dtype=float) for x in (price, F, K, T))
    opt_type = np.asarray(opt_type, dtype=str)

    hi = np.full(price.shape, 500)
    lo = np.zeros(price.shape)
    while np.any(hi - lo > eps):
        mid = (hi + lo) / 2
        pred = bs_price(F, K, T, mid, opt_type, r)
        hi = np.where(pred > price, mid, hi)
        lo = np.where(pred < price, mid, lo)

    return (hi + lo) / 2


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
