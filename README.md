# Personal Data Analysis Application

A web app for **importing, cleaning, and analyzing historical price data** (and
tabular data generally). You point it at a data source, it standardizes the
messy shapes price data comes in, and then it gives you filtering, charts,
return/risk metrics, technical indicators, multi-symbol comparison, and an AI
assistant that can actually run calculations on your data.

It runs in a normal web browser — no software to install for everyday use — and
the same code can also be run on your own machine.

> **New here? Read this page, then the [User Guide](docs/USER_GUIDE.md).**
> Setting up keys/secrets? See [Configuration](docs/CONFIGURATION.md).
> Want to change the code? See [Architecture](docs/ARCHITECTURE.md).

---

## What can it actually do?

| Stage | What you get |
|---|---|
| **Connect** | Load data from a local file, a SQL database, a web API (FRED, custom URLs, FMP), or Google Cloud Storage. |
| **Type & normalize** | Fix column types; auto-detect the date column; rename messy price columns (e.g. `adjClose`, `4. close`) to standard `open/high/low/close/volume`; strip `$`, `,`, `%` out of numbers; resample to daily/weekly/monthly. |
| **Indicators** | Add SMA, EMA, RSI, Bollinger Bands, rolling volatility, and returns as new columns. Moving averages and bands overlay on the price chart automatically. |
| **Explore** | Filter by date range, number range, or category; view and **edit** the data in a table; download the result as CSV. |
| **Measure** | A Returns & Risk panel: total return, CAGR, annualized volatility, Sharpe ratio, max drawdown, best/worst day. |
| **Visualize** | Line / Bar / Scatter charts, plus **candlestick** and **OHLC** price charts with a volume sub-panel and log-scale option. |
| **Compare** | Load several symbols and overlay them rebased to 100, with a return-correlation heatmap. |
| **Ask (AI)** | A chat assistant (DeepSeek) that writes and runs pandas/plotly code on your live data, shows the result, explains it, and fixes its own errors. |

If you just want to **see a candlestick chart of a price series with a 50-day
moving average and its annualized volatility**, that's about five clicks. See
the [User Guide](docs/USER_GUIDE.md).

---

## The mental model

Everything revolves around **one "active dataset"** — the table currently loaded
into the app. You load it once (Connect), and every other tool operates on that
same table as it flows through the pipeline:

```
            ┌─────────────┐
 source ──▶ │   CONNECT   │  upload / SQL / API / GCS
            └──────┬──────┘
                   ▼
        ┌──────────────────────┐   (each step is optional; skip what you don't need)
        │  Type editor         │   fix column dtypes
        │  Normalizer          │   detect date, map OHLCV, clean numbers, resample
        │  Indicators          │   add SMA/EMA/RSI/Bollinger/vol/returns columns
        │  Filters (sidebar)   │   narrow by date / number / category
        │  Editable table      │   inspect & hand-edit
        │  Export              │   download CSV
        │  Returns & Risk      │   performance metrics
        │  Health check        │   rows/dupes/missing
        │  Visualization       │   line/bar/scatter/candlestick/OHLC
        │  Multi-symbol compare│   overlay several tickers
        └──────────────────────┘
                   ▼
            ┌─────────────┐
            │ AI WORKSPACE│  ask questions; it runs code on the active data
            └─────────────┘
```

The app has **two tabs**: **📊 Data Studio** (everything above the AI box) and
**🤖 AI Workspace** (the assistant).

---

## Quick start

### Option A — Use it in the browser (Streamlit Community Cloud)

The app is deployed from this GitHub repo to Streamlit Community Cloud. Open the
app's URL (find it in your [Streamlit Cloud dashboard](https://share.streamlit.io)),
and you're in. Every push to `master` redeploys it automatically.

To enable the optional features (AI chat, cloud/database sources) you paste
secrets into the Streamlit dashboard once — see [Configuration](docs/CONFIGURATION.md).

### Option B — Run it on your own machine

```bash
# 1. Get the code
git clone https://github.com/aye5788/my-data-app.git
cd my-data-app

# 2. (Recommended) a virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) add secrets for AI / databases / cloud — see docs/CONFIGURATION.md
#    create .streamlit/secrets.toml

# 5. Run it
streamlit run app.py
```

It opens at `http://localhost:8501`. Running locally also lets you reach
databases and files on your own computer/LAN that the cloud version can't.

Requires **Python 3.10+**.

---

## What you need vs. what's optional

| To do this… | You need… |
|---|---|
| Upload a CSV/Excel/JSON/Parquet file and analyze it | **Nothing** — works out of the box |
| Pull data from a web API (FRED, a custom URL) | That provider's API key (FRED is free) |
| Connect to a SQL database | The database connection details, and the DB reachable from where the app runs |
| Load from Google Cloud Storage | A Google service-account key |
| Use the AI assistant | A DeepSeek API key |

None of these block the others — the app degrades gracefully. If a key is
missing, only that one feature shows a "not configured" notice.

> **Note on FMP:** the API connector includes a Financial Modeling Prep preset,
> but it requires an active FMP key. If you don't have one, use **FRED**, a
> **Custom URL**, a **SQL database**, or **local upload** instead — they cover
> the same ground.

---

## Where things live

```
app.py                  Navigation shell — wires the pipeline together
state.py                The single "active dataset" held in memory
connectors/             Data sources (upload, sql, rest, gcs) + the picker
transform/              typing (dtypes), normalize (price/time-series), filters
analytics/              stats (returns/risk), indicators, compare (multi-symbol)
quality/                profiling (health check)
viz/                    charts (generic + candlestick/OHLC)
ai/                     deepseek (chat loop) + sandbox (safe code execution)
requirements.txt        Pinned dependencies
docs/                   The guides this README points to
```

A full walkthrough of each file and how to extend the app is in
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Documentation map

- **[User Guide](docs/USER_GUIDE.md)** — step-by-step "how do I…" recipes for
  every feature. Start here if you want to *use* the app.
- **[Configuration](docs/CONFIGURATION.md)** — secrets, API keys, database URLs,
  GCS credentials, upload-size limits, and deployment.
- **[Architecture](docs/ARCHITECTURE.md)** — how the code is organized, the data
  flow, the connector contract, the AI sandbox, and how to add your own source
  or analysis step.
