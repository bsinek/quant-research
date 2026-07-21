"""Standard surface read-outs off a fitted SVI surface.

The quoted metrics desks track — ATM vol, 25-delta skew, term-structure slope — plus the
butterfly-arb coverage. All evaluate the *fitted* slices, so they read the smile at strikes
that are almost never listed (e.g. the 25-delta point), which is why they need the fit first.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import brentq

from engine.svi import svi_w, svi_g

# d1 at 25-delta: N(d1) = 0.25 (call) / 0.75 (put)  ->  +/- 0.6745
_D1_25C, _D1_25P = -0.6744897501960817, 0.6744897501960817


def _delta_k(row, d1_target: float) -> float:
    """Log-moneyness where the fitted slice reaches ``d1_target`` (Black-76 d1)."""
    def f(k):
        w = max(float(svi_w(k, row.a, row.b, row.rho, row.m, row.sigma)), 1e-8)
        return (-k + 0.5 * w) / np.sqrt(w) - d1_target
    try:
        return brentq(f, -1.5, 1.0)
    except ValueError:
        return np.nan


def surface_metrics(fit: pd.DataFrame) -> pd.DataFrame:
    """Add ATM vol and 25-delta skew columns to a fitted surface (needs a..sigma, theta, T).

    Adds: atm_vol (sqrt(theta/T)), iv_25c, iv_25p, skew_25d (put IV - call IV, in vol).
    Skips unfitted (NaN-param) rows. Returns a new frame.
    """
    out = fit.dropna(subset=["a"]).copy()
    out["atm_vol"] = np.sqrt(out["theta"] / out["T"])
    out["k_25c"] = out.apply(lambda r: _delta_k(r, _D1_25C), axis=1)
    out["k_25p"] = out.apply(lambda r: _delta_k(r, _D1_25P), axis=1)
    for tag, col in [("k_25c", "iv_25c"), ("k_25p", "iv_25p")]:
        out[col] = np.sqrt(svi_w(out[tag], out["a"], out["b"], out["rho"],
                                 out["m"], out["sigma"]) / out["T"])
    out["skew_25d"] = out["iv_25p"] - out["iv_25c"]                       # risk reversal (tilt)
    out["fly_25d"] = (out["iv_25c"] + out["iv_25p"]) / 2 - out["atm_vol"]  # butterfly (curvature)
    return out


def forward_vol(fit: pd.DataFrame) -> pd.DataFrame:
    """Forward vol between adjacent expiries from the ATM total-variance term structure.

    Forward variance over [T_i, T_{i+1}] = (theta_{i+1} - theta_i) / (T_{i+1} - T_i); its
    sqrt is the vol the market prices for that *future* window. Spot (implied) vol averages
    from now to each expiry, smearing events; forward vol isolates them — a window whose
    forward vol spikes above its neighbours is pricing a scheduled event (Fed, CPI, ...).
    Needs theta (ATM total variance) per expiry. Columns: expiry_from, expiry_to, T_mid, fwd_vol.
    """
    f = fit.dropna(subset=["theta"]).sort_values("T")
    T, th, exp = f["T"].to_numpy(), f["theta"].to_numpy(), f["expiry"].to_numpy()
    fwd_var = np.diff(th) / np.diff(T)
    return pd.DataFrame({
        "expiry_from": exp[:-1], "expiry_to": exp[1:],
        "T_mid": (T[:-1] + T[1:]) / 2,
        "fwd_vol": np.sqrt(np.maximum(fwd_var, 0.0)),
    })


def butterfly_free_fraction(fit: pd.DataFrame, quotes: pd.DataFrame) -> float:
    """Fraction of fitted expiries whose g(k) >= 0 across that expiry's quoted k range."""
    fitted = fit.dropna(subset=["a"])
    ok = 0
    for _, r in fitted.iterrows():
        kk = quotes.loc[quotes["expiry"] == r.expiry, "k"]
        grid = np.linspace(kk.min(), kk.max(), 300)
        ok += int(np.all(svi_g(grid, r.a, r.b, r.rho, r.m, r.sigma) >= 0))
    return ok / len(fitted)
