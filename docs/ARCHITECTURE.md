# Architecture

This document is for anyone who wants to **change the code** — add a data
source, add an analysis step, or understand how the pieces fit. It assumes you
can read Python.

---

## The big idea

The app is a [Streamlit](https://streamlit.io) application. Streamlit re-runs
the whole script top-to-bottom on every interaction, so state that must survive
between clicks lives in `st.session_state`.

There is **one active dataset** — a single pandas DataFrame — and every feature
is a function that takes that DataFrame, draws some widgets, and returns a
(possibly modified) DataFrame. The features are chained in `app.py`. That's the
entire architecture in one sentence.

```
load → f1(df) → f2(df) → … → render
```

---

## File-by-file

```
app.py                  Entry point. Builds the page, loads the active dataset,
                        and calls each stage in order inside two tabs.
state.py                Dataclass `Dataset` + get/set/clear helpers that store
                        the active dataset in st.session_state.

connectors/
  __init__.py           REGISTRY (name → module) and render_source_selector(),
                        which draws the sidebar picker and dispatches.
  loaders.py            load_data_file(): shared CSV/XLSX/JSON/Parquet reader
                        (cached). Used by upload and gcs.
  upload.py             Local file upload.
  rest.py               Generic REST/API: providers (FMP/FRED/Custom), key
                        resolution, JSON/CSV parsing.
  sql.py                SQLAlchemy connector: engine cache, table list, query.
  gcs.py                Google Cloud Storage bucket/file browser + loader.

transform/
  typing.py             render_type_editor(): per-column dtype casting.
  normalize.py          Time-series/price normalizer: date detection, OHLCV
                        mapping, numeric cleaning, resampling. Also time_axis().
  filters.py            Sidebar filters, the editable table, and CSV export.

analytics/
  stats.py              compute_stats() (returns/risk) + render_returns_panel().
  indicators.py         Pure indicator math (SMA/EMA/RSI/Bollinger/…) +
                        render_indicators().
  compare.py            Multi-symbol comparison (rebased overlay + correlation).

quality/
  profiling.py          get_data_profile() + render_health_check().

viz/
  charts.py             render_visualization(): generic XY charts and the
                        candlestick/OHLC price chart with overlays.

ai/
  deepseek.py           The chat workspace and the self-healing compute loop.
  sandbox.py            run_code(): sandboxed execution of model-written code.
```

---

## The data flow (in `app.py`)

```python
df, source_name, asset_name = render_source_selector()   # CONNECT
if df is not None:
    state.set_dataset(df, source=source_name, asset=asset_name)

# --- Data Studio tab ---
df = render_type_editor(df)            # may recast dtypes
df = render_normalizer(df)             # opt-in price/time-series standardization
df = render_indicators(df)             # opt-in: appends indicator columns
filtered_df = render_filters(df)        # sidebar filters → narrowed view
filtered_df = render_table(filtered_df) # editable table → edits flow on
render_export(filtered_df)
render_returns_panel(filtered_df)
render_health_check(filtered_df)
render_visualization(filtered_df)
render_multi_symbol(df, asset_name)     # uses the FULL df, not the filtered one

# --- AI Workspace tab ---
render_ai_workspace(df)
```

Two things worth noting:

- **Indicators run before filtering** so window-based math (e.g. a 200-day SMA)
  uses the whole series, not just the visible date range.
- **Multi-symbol uses `df`, not `filtered_df`**, on purpose — you compare full
  histories, not whatever the current filter happens to show.

---

## The connector contract

Every data source is a module that exposes exactly two things:

```python
NAME = "Human-readable source name"      # shown in the sidebar dropdown

def render():
    """Draw this source's widgets and load data.

    Returns (df, asset_name) on success, or (None, "") when there's
    nothing to load yet (e.g. no file chosen, missing credentials).
    """
```

It is registered in `connectors/__init__.py`:

```python
from . import upload, sql, rest, gcs
REGISTRY = {
    upload.NAME: upload,
    sql.NAME: sql,
    rest.NAME: rest,
    gcs.NAME: gcs,
}
```

### Adding a new source

1. Create `connectors/myapi.py` with `NAME` and `render()`.
2. Reuse `loaders.load_data_file()` if you're reading file bytes.
3. Pull any secret from `st.secrets[...]` (don't hard-code keys).
4. Add it to `REGISTRY`. Done — it appears in the dropdown automatically.

Caching tips used across connectors: wrap pure fetches in `@st.cache_data`, and
expensive handles (DB engines) in `@st.cache_resource`.

---

## Adding an analysis / transform step

A stage is just a function `render_x(df) -> df` (or `-> None` if it only
displays). Write it, then insert one line in `app.py` at the right point in the
pipeline. Conventions to match the existing code:

- Wrap optional/heavy steps in `st.expander(...)` with a default-off checkbox so
  they don't clutter the page or add columns unless asked.
- Keep the *math* in pure, importable functions (see `analytics/indicators.py`)
  and the Streamlit widgets in a thin `render_*` wrapper. This is what makes the
  logic unit-testable without a running app.

The time axis of a frame (index vs. a date column) is resolved centrally by
`transform.normalize.time_axis(df)` — reuse it instead of re-detecting dates.

---

## The AI sandbox

`ai/deepseek.py` runs a bounded loop: the model writes a Python snippet → it's
executed → the result (or error) is fed back → the model interprets or fixes it.
Bounds: `MAX_FIX_ATTEMPTS = 3`, `MAX_MODEL_CALLS = 8`.

`ai/sandbox.py` does the execution. The snippet runs via `exec()` in a
**restricted namespace**:

- **Exposed:** a *copy* of `df` (so mutations can't affect the real dataset),
  plus `pd`, `np`, `px`, `go`. The snippet assigns `result` and/or `fig`.
- **Removed:** `__import__`, `open`, `eval`, `exec`, `compile`, `getattr`,
  `globals`, … — only a curated allow-list of safe builtins is provided. So no
  imports, no file access, no network.
- stdout, the `result`, the `fig`, and any traceback are captured and returned.

> This is a guardrail against accidental/destructive operations in a personal
> tool — not a hardened boundary against a determined attacker (perfect CPython
> sandboxing is famously hard). It's appropriate because you're running it on
> your own data, but don't expose this endpoint to untrusted users as-is.

---

## Conventions & gotchas

- **Streamlit reruns everything** on each interaction. Don't rely on local
  variables persisting; use `st.session_state` (see `state.py`,
  `analytics/compare.py`'s series store, and `ai/deepseek.py`'s chat history).
- **Widget keys must be unique.** Every widget passes an explicit `key=`. When
  rendering lists of charts, keys are suffixed by index to avoid collisions.
- **Pinned dependencies** in `requirements.txt`. Streamlit Cloud installs these
  on each deploy; bump them deliberately.
- **Secrets never touch git.** `.streamlit/secrets.toml`, `.env`, and
  `gcs_key.json` are git-ignored. Read everything via `st.secrets`.
- **Deploy = push.** A push to `master` redeploys the Cloud app. Work on a
  branch, verify, then merge.

---

## Testing approach

There's no formal test suite, but the pure functions are designed to be checked
quickly in isolation, e.g.:

```bash
python - <<'PY'
import pandas as pd
from analytics.indicators import rsi, bollinger
s = pd.Series([1,2,3,4,5,4,3,2,3,4,5,6,7,6,5.0])
print(rsi(s, 14).iloc[-1])          # bounded 0–100
mid, up, lo = bollinger(s, 5)
assert (lo <= mid).all() and (mid <= up).all()
print("ok")
PY
```

Before a deploy, the working pattern is: `py_compile` the changed files, run a
functional check of any new pure logic, and do a headless boot
(`streamlit run app.py --server.headless true --server.port <p>`) confirming the
health endpoint returns 200.
