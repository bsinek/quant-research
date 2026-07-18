"""Contract-quality filters for the raw option chain.

Each function takes the tidy contract frame (see ``chain_to_frame``) and returns a
boolean mask — True = keep. Masks compose with ``&``,
``df[volume_mask(df) & bidask_mask(df)]``, and their pass rates (``mask.mean()``)
are the numbers that justify the filters. Filters only *drop* untradeable or stale
quotes; they never modify a row. Surface construction (forward, OTM-select, grid)
lives in ``surface.py``, downstream of these.
"""
from __future__ import annotations

import pandas as pd


def volume_mask(df: pd.DataFrame, min_volume: int = 0) -> pd.Series:
    """Mark contracts that traded more than ``min_volume`` this session (True = keep).

    Volume is the last session's contract count; the default 0 keeps anything with
    a real print — the workhorse liquidity filter (ADR 005). Drops quotes listed
    but never changed hands (stale / phantom marks). Raise ``min_volume`` to demand
    deeper liquidity.
    """
    return df['volume'] > min_volume


def bidask_mask(df: pd.DataFrame, min_price: float = 0.0) -> pd.Series:
    """Mark contracts quoted two-sided above ``min_price`` (bid and ask both > it).

    A zero bid or ask means no dealer is quoting that side, so mid is meaningless;
    the default 0 removes those one-sided / no-quote contracts (mostly the deep
    wings). Raise ``min_price`` to drop penny / near-worthless quotes too.
    """
    return (df['bid'] > min_price) & (df['ask'] > min_price)


def expiry_mask(df: pd.DataFrame, min_T: float = 0.0) -> pd.Series:
    """Keep contracts with more than ``min_T`` years to expiry (True = keep).

    The default 0 drops only same-day/expired contracts (T=0): they hold no time
    value and no IV exists, since Black-76's d1/d2 divide by ``sigma*sqrt(T)=0``.
    Same-day expiries land exactly on 0 because T is calendar-days/365 (see the
    deferred settlement-time-T note); a finer clock would give them a tiny positive
    T, but they'd still need dropping once past settlement. Raise ``min_T`` to also
    drop noisy near-expiry contracts (e.g. 0.02 ≈ one week).
    """
    return df['T'] > min_T


def staleness_mask(df: pd.DataFrame, max_days: int = 7) -> pd.Series:
    """Keep contracts traded within ``max_days`` of the snapshot (True = keep).

    Liquidity gate keyed on ``last_trade_time`` vs the snapshot as-of time
    (``df.attrs['asof']``). A contract not traded within the window — or never
    traded (no timestamp) — is dropped. Leaner and less path-dependent than
    volume>0, which demands a trade the *same session* (ADR 008): a contract that
    printed a few days ago but not today is still liquid. ``max_days`` is the
    recency window (calendar days).
    """
    asof = df.attrs['asof']
    if asof.tzinfo is not None:
        asof = asof.tz_localize(None)
    age = (asof - df['last_trade_time']).dt.days
    return age <= max_days
