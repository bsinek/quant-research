"""Vol-surface construction: forward, OTM-selection, grid.

Downstream of ``filters.py``. These steps are *modeling*, not cleaning: they derive
the per-expiry forward from option prices (put-call parity) and use it to pick the
reliable (OTM) side of each strike and to place the moneyness axis. Run these on
already-filtered, two-sided quotes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def implied_forwards(df: pd.DataFrame, r: float = 0.04) -> pd.DataFrame:
    """Forward implied by put-call parity at each strike — one row per call+put pair.

    Pairs the call and put mids at each (root, expiry, strike) — never across roots,
    since SPX (AM) and SPXW (PM) settle differently — then F = K + e^{rT}(C − P).
    Strikes missing a leg drop out. Every paired strike of an expiry should imply the
    *same* F, so the spread of these estimates is a quality check (near-ATM tight,
    wings noisy). ``r`` is the only free input (ADR 003).

    Columns: root, expiry, strike, T, F.
    """
    pair = df.pivot_table(index=["root", "expiry", "strike", "T"], columns="type", values="mid")
    pair = pair.dropna(subset=["C", "P"]).reset_index()
    pair["F"] = pair["strike"] + np.exp(r * pair["T"]) * (pair["C"] - pair["P"])
    return pair[["root", "expiry", "strike", "T", "F"]]


def forward_by_expiry(df: pd.DataFrame, r: float = 0.04) -> pd.Series:
    """One reconciled forward F per expiry (index = expiry).

    Median of ``implied_forwards`` over each expiry's paired strikes — robust to a
    stray bad strike. An expiry with no paired strikes gets no entry (drops from the
    surface). This F feeds both ``select_otm`` and the ln(K/F) moneyness axis.
    """
    return implied_forwards(df, r).groupby("expiry")["F"].median()


def select_otm(df: pd.DataFrame) -> pd.Series:
    """Boolean mask keeping the OTM side of each strike: puts below F, calls above F.

    Returns a mask (True = keep), consistent with ``filters.py``. Expects an ``F``
    column — attach with ``df["F"] = df["expiry"].map(forward_by_expiry(df))``. OTM
    options are the liquid, reliable side; the ITM side is parity-redundant and
    wider-spread. Construction, not a quality filter — it depends on the modeled
    forward, which is why it lives here, not in ``filters.py``.
    """
    return ((df["type"] == "P") & (df["strike"] < df["F"])) | (
        (df["type"] == "C") & (df["strike"] > df["F"])
    )


def blend_roots(df: pd.DataFrame, asof=None, cutoff_days: int = 60) -> pd.DataFrame:
    """Collapse each expiry to a single root: SPXW within ``cutoff_days``, richest beyond.

    Only the five same-date 3rd-Friday SPX/SPXW collisions list both roots; single-root
    expiries (near-term SPXW weeklies, long-end SPX LEAPS) pass through untouched. At a
    collision, near-term prefers PM-settled SPXW — the AM/PM settlement gap (~0.3 day, SPX
    settling on the Friday open vs SPXW at the close) costs most as a fraction of a short
    ``T``, and SPXW's weeklies are the dense near-term series anyway. Beyond the cutoff that
    gap is negligible (<~0.04 vol pt), so the root with more quotes wins, grabbing SPX's
    deeper wings. Supersedes ADR 004's always-SPXW collision rule (ADR 015). ``asof``
    defaults to ``df.attrs['asof']``.
    """
    asof = pd.Timestamp(df.attrs["asof"] if asof is None else asof).normalize()
    keep = {}
    for exp, g in df.groupby("expiry"):
        roots = set(g["root"])
        if len(roots) == 1:
            keep[exp] = g["root"].iloc[0]
        elif (pd.Timestamp(exp) - asof).days <= cutoff_days:
            keep[exp] = "SPXW" if "SPXW" in roots else next(iter(roots))
        else:
            keep[exp] = g.groupby("root").size().idxmax()
    return df[df["root"] == df["expiry"].map(keep)].copy()
