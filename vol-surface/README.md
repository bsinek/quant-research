# vol-surface

Volatility surface construction and analysis.

_Work in progress._

## Running

Requires Python 3.11+. A virtual environment is recommended:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .   # installs deps + the engine package (editable)
```

The editable install (`-e .`) links the `engine` package into the venv, so you
can `import engine.data` from anywhere without path hacks. Then, in Python:

```python
from engine.data import load_chain, chain_to_frame

df = chain_to_frame(load_chain())   # newest SPX snapshot, as a tidy DataFrame
```

## Data

`engine/data.py` pulls the SPX option chain from CBOE's free delayed-quotes feed.
`load_chain()` reuses the newest frozen snapshot under `data/`, downloading one
(e.g. `data/spx_2026-07-11.json`) if the folder is empty.

`data/` is gitignored on purpose. CBOE's [terms](https://www.cboe.com/terms/)
license the delayed data for personal, non-commercial use only and prohibit
redistribution, so the raw chain is never committed — anyone who runs the code
fetches their own copy. See `docs/DECISIONS.md` for the rationale.
