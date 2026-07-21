import numpy as np
import pandas as pd
from scipy.optimize import minimize

def svi_w(k, a, b, rho, m, sigma) -> np.ndarray:
    """Raw-SVI total variance w(k) at log-moneyness k. Vectorized over k.

    Returns TOTAL VARIANCE (w = iv**2 * T), not vol. `sigma` is the SVI curvature
    param (roundness of the smile's bottom), NOT volatility — Gatheral's name
    collision. `m` locates the minimum; wings are linear in k with slopes b(1±rho).
    """
    k = np.asarray(k, dtype=float)
    return a + b * (rho * (k - m) + np.sqrt((k - m)**2 + sigma**2))


def svi_g(k, a, b, rho, m, sigma) -> np.ndarray:
    """Gatheral-Jacquier g(k) for one SVI slice; butterfly-arb-free iff g(k) >= 0 for all k.

    g = (1 - k*w'/(2w))**2 - (w'**2/4)*(1/w + 1/4) + w''/2, where w, w', w'' are the SVI
    total variance and its first two k-derivatives (all analytic). A negative g(k) means a
    negative implied density there. Ref: Gatheral & Jacquier, arXiv:1204.0646, Lemma 2.2.
    Vectorized over k.
    """
    k = np.asarray(k, dtype=float)
    u = k - m
    root = np.sqrt(u**2 + sigma**2)
    w = a + b * (rho * u + root)
    w1 = b * (rho + u / root)                       # dw/dk
    w2 = b * sigma**2 / root**3                     # d2w/dk2
    return (1 - k * w1 / (2 * w))**2 - (w1**2 / 4) * (1 / w + 0.25) + w2 / 2


def fit_slice(k, w, weights=None):
    """Fit raw SVI to one expiry; returns (a, b, rho, m, sigma, rmse).

    Zeliade quasi-explicit: an exact weighted least-squares solve for the three
    linear params (a, b*rho, b) sits inside a 2-D Nelder-Mead search over the two
    nonlinear ones (m, sigma) that are trapped in the sqrt. `weights` defaults to
    uniform; pass vega/spread to downweight noisy wings. `sigma` is the SVI
    curvature param, not vol. rmse is unweighted w-space error (a quality flag).
    """
    k, w = (np.asarray(x, dtype=float) for x in (k, w))
    weights = np.ones_like(w) if weights is None else np.asarray(weights, dtype=float)

    def solve(m, sigma):
        X = np.column_stack([np.ones_like(k), (k - m), np.sqrt((k - m)**2 + sigma**2)])
        X_weighted, w_weighted = X * np.sqrt(weights)[:, None], w * np.sqrt(weights)
        beta = np.linalg.lstsq(X_weighted, w_weighted, rcond=None)[0]
        resid = np.sum((X_weighted @ beta - w_weighted)**2)
        return beta, resid

    def objective(x):
        m, sigma = x
        return solve(m, sigma)[1]

    m0, sigma0 = k[np.argmin(w)], (k.max() - k.min()) / 2
    m, sigma = minimize(objective, x0=(m0, sigma0), method='Nelder-Mead').x
    beta, _ = solve(m, sigma)
    a, c, b = beta                                  # c = b*rho, so rho = c/b
    rho = c / b
    rmse = np.sqrt(np.mean((svi_w(k, a, b, rho, m, sigma) - w)**2))
    return a, b, rho, m, sigma, rmse


def fit_surface(df, weight_col=None, min_quotes=10):
    """Fit raw SVI to every expiry in ``df`` with at least ``min_quotes`` rows.

    ``df`` needs columns: expiry, T, k (log-moneyness), w (total variance), and
    ``weight_col`` if given. Every expiry gets a row; those with fewer than
    ``min_quotes`` rows are left unfitted (NaN params) so skips stay visible and
    plottable. Sorted by expiry, so T increases down the frame.

    Columns: expiry, T, n_quotes, a, b, rho, m, sigma, rmse.
    """
    rows = []
    for expiry, g in df.groupby("expiry"):
        if len(g) >= min_quotes:
            weights = g[weight_col].to_numpy() if weight_col else None
            a, b, rho, m, sigma, rmse = fit_slice(g["k"].to_numpy(), g["w"].to_numpy(), weights)
        else:
            a = b = rho = m = sigma = rmse = np.nan
        rows.append({
            "expiry": expiry, "T": g["T"].iloc[0], "n_quotes": len(g),
            "a": a, "b": b, "rho": rho, "m": m, "sigma": sigma, "rmse": rmse,
        })
    return pd.DataFrame(rows)