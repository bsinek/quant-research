import numpy as np
from scipy.optimize import minimize

def svi_w(k, a, b, rho, m, sigma) -> np.ndarray:
    """Raw-SVI total variance w(k) at log-moneyness k. Vectorized over k.

    Returns TOTAL VARIANCE (w = iv**2 * T), not vol. `sigma` is the SVI curvature
    param (roundness of the smile's bottom), NOT volatility — Gatheral's name
    collision. `m` locates the minimum; wings are linear in k with slopes b(1±rho).
    """
    k = np.asarray(k, dtype=float)
    return a + b * (rho * (k - m) + np.sqrt((k - m)**2 + sigma**2))


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