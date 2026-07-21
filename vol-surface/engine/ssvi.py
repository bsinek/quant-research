"""SSVI global volatility surface (Gatheral-Jacquier 2013).

One surface driven by the ATM total-variance term structure theta_T plus three global
params (rho, eta, gamma), with *explicit* no-arbitrage conditions — unlike independent
raw-SVI slices, which can cross in maturity (calendar arbitrage). Per-slice SSVI at a
fixed theta is itself an SVI slice, so the raw-SVI machinery still applies for plotting
and butterfly checks. Ref: Gatheral & Jacquier, "Arbitrage-free SVI volatility surfaces",
arXiv:1204.0646 (SSVI formula and Thms 4.1/4.2).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import least_squares

from engine.svi import svi_w


def ssvi_w(k, theta, rho, eta, gamma) -> np.ndarray:
    """SSVI total variance w(k, theta) with power-law phi(theta) = eta * theta**-gamma.

    ``theta`` is ATM total variance at the quote's maturity (scalar or per-quote array),
    ``k`` is log-moneyness. rho in (-1, 1), eta > 0, gamma in (0, 1). Vectorized.
    """
    k, theta = np.asarray(k, dtype=float), np.asarray(theta, dtype=float)
    phi = eta * theta**(-gamma)
    return 0.5 * theta * (1 + rho * phi * k + np.sqrt((phi * k + rho)**2 + (1 - rho**2)))


def ssvi_butterfly_ok(theta, rho, eta, gamma) -> bool:
    """True if the SSVI butterfly conditions (GJ Thm 4.2) hold across the given theta values.

    Requires theta*phi*(1+|rho|) < 4 and theta*phi**2*(1+|rho|) <= 4 for every theta, with
    phi = eta*theta**-gamma. Pass the distinct theta_T of the surface.
    """
    theta = np.asarray(theta, dtype=float)
    phi = eta * theta**(-gamma)
    cond1 = theta * phi * (1 + abs(rho))
    cond2 = theta * phi**2 * (1 + abs(rho))
    return bool(np.all(cond1 < 4) and np.all(cond2 <= 4))


def atm_theta(surface: pd.DataFrame) -> pd.DataFrame:
    """Attach ATM total variance theta_T = svi_w(0, slice params) to a fit_surface frame.

    theta_T is the SSVI term-structure input. Returns a copy with a ``theta`` column;
    unfitted (NaN-param) expiries get NaN theta. Calendar no-arb needs theta_T
    non-decreasing in T — check/enforce after sorting by T (see notebook).
    """
    out = surface.copy()
    out["theta"] = svi_w(0.0, surface["a"], surface["b"], surface["rho"],
                         surface["m"], surface["sigma"])
    return out


def fit_ssvi(df, weight_col=None) -> dict:
    """Fit one global SSVI (rho, eta, gamma) to all quotes at once.

    ``df`` needs columns: k (log-moneyness), w (total variance), theta (ATM total variance
    for that quote's expiry), and ``weight_col`` if given. Returns
    {rho, eta, gamma, rmse, butterfly_ok}. theta must be monotone in maturity for calendar
    no-arb (the caller's responsibility); butterfly is verified here via GJ Thm 4.2.
    """
    k = df["k"].to_numpy(dtype=float)
    w = df["w"].to_numpy(dtype=float)
    theta = df["theta"].to_numpy(dtype=float)
    sqrt_wt = np.sqrt(df[weight_col].to_numpy(dtype=float)) if weight_col else 1.0

    def resid(params):
        rho, eta, gamma = params
        return sqrt_wt * (ssvi_w(k, theta, rho, eta, gamma) - w)

    res = least_squares(
        resid, x0=[-0.5, 1.0, 0.5],
        bounds=([-0.999, 1e-6, 1e-3], [0.999, 10.0, 0.999]),
    )
    rho, eta, gamma = res.x
    rmse = float(np.sqrt(np.mean((ssvi_w(k, theta, rho, eta, gamma) - w)**2)))
    return {
        "rho": rho, "eta": eta, "gamma": gamma, "rmse": rmse,
        "butterfly_ok": ssvi_butterfly_ok(np.unique(theta), rho, eta, gamma),
    }
