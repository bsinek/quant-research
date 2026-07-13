"""SPX option-chain access.

Pulls the SPX chain from CBOE's free delayed-quotes feed — an undocumented,
delayed, personal-use endpoint (see docs/DECISIONS.md). The only place the data
source lives, so swapping to purchased history touches nothing downstream.

Two verbs: ``download_chain`` (hit CBOE, freeze a dated snapshot) and
``load_chain`` (read the newest frozen snapshot into a tidy frame). Everyday use
is ``load_chain``; run ``download_chain`` once to grab a snapshot.
"""
from __future__ import annotations

import json
import pathlib
import re

import pandas as pd
import requests

CBOE_URL = "https://cdn.cboe.com/api/global/delayed_quotes/options/_{symbol}.json"

# OCC/OSI option symbol, e.g. "SPX260717C00200000":
#   root (letters) | YYMMDD expiry | C/P | strike x 1000 (8 digits)
_SYMBOL_RE = re.compile(r"^(?P<root>[A-Z]+)(?P<ymd>\d{6})(?P<cp>[CP])(?P<strike>\d{8})$")

# data/ lives at the project root, anchored to this file (not the cwd) so it
# resolves the same whether called from vol-surface/ or notebooks/.
_DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"  # engine/ -> vol-surface/data/


def fetch_chain(symbol: str = "SPX") -> dict:
    """Download the raw chain JSON. Index symbols take a leading underscore (_SPX)."""
    resp = requests.get(CBOE_URL.format(symbol=symbol), timeout=30)
    resp.raise_for_status()
    return resp.json()


def chain_to_frame(raw: dict) -> pd.DataFrame:
    """Flatten CBOE's JSON into one tidy row per contract.

    Columns: expiry, T (years), type ('C'/'P'), strike, bid, ask, mid, last,
    volume, open_interest, cboe_iv. Snapshot-level spot / as-of live in df.attrs.
    """
    data = raw["data"]
    asof = pd.Timestamp(raw["timestamp"])
    rows = []
    for o in data["options"]:
        m = _SYMBOL_RE.match(o["option"])
        if m is None:
            continue
        ymd = m["ymd"]
        rows.append(
            {
                "expiry": pd.Timestamp(f"20{ymd[:2]}-{ymd[2:4]}-{ymd[4:6]}"),
                "type": m["cp"],
                "strike": int(m["strike"]) / 1000,
                "bid": o["bid"],
                "ask": o["ask"],
                "last": o["last_trade_price"],
                "volume": o["volume"],
                "open_interest": o["open_interest"],
                "cboe_iv": o["iv"],  # CBOE's own IV — for validation, never as input
            }
        )
    df = pd.DataFrame(rows)
    df["mid"] = (df["bid"] + df["ask"]) / 2
    df["T"] = (df["expiry"] - asof.normalize()).dt.days / 365.0
    df.attrs["spot"] = data["current_price"]
    df.attrs["asof"] = asof
    return df


def download_chain(symbol: str = "SPX", data_dir=_DATA_DIR) -> pathlib.Path:
    """Fetch a fresh chain from CBOE and freeze it as spx_<date>.json.

    Deliberate — use to grab a NEW snapshot even when one already exists.
    Returns the saved path. ``data_dir`` is gitignored (personal-use data).
    """
    raw = fetch_chain(symbol)
    date = pd.Timestamp(raw["timestamp"]).strftime("%Y-%m-%d")
    p = pathlib.Path(data_dir) / f"spx_{date}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(raw))
    return p


def load_chain(data_dir=_DATA_DIR, date: str | None = None) -> dict:
    """Load a frozen snapshot's raw chain dict from disk (symmetric with fetch_chain).

    Newest snapshot by default; if ``data_dir`` is empty, downloads and freezes
    one automatically (network hit once, then offline). Pass date='YYYY-MM-DD'
    to pin a specific snapshot — raises FileNotFoundError if that one is missing.
    Feed the result to ``chain_to_frame`` for a tidy DataFrame.
    """
    d = pathlib.Path(data_dir)
    if date:
        p = d / f"spx_{date}.json"
        if not p.exists():
            raise FileNotFoundError(f"no snapshot {p} — check the date or run download_chain()")
    else:
        snapshots = sorted(d.glob("spx_*.json"))
        p = snapshots[-1] if snapshots else download_chain(data_dir=data_dir)
    return json.loads(p.read_text())
