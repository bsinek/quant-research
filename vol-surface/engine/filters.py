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
