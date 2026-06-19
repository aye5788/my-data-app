# User Guide

This guide walks through the app one feature at a time. You don't need any
programming knowledge to follow it. Each section is a "how do I…" recipe.

The app has two tabs at the top:

- **📊 Data Studio** — load data, clean it, chart it, measure it.
- **🤖 AI Workspace** — ask an AI assistant questions about your data.

Most controls live in the **left sidebar** (choosing a data source, filtering)
or in **collapsible "expander" panels** in the main area (the ones with a ▸
arrow you click to open).

---

## 1. Load your data (Connect)

Everything starts in the sidebar under **"Select Data Source."** Pick one of
four sources from the dropdown.

### 1a. Local Upload (the simplest)

1. In the sidebar, choose **Local Upload**.
2. Click **Browse files** and pick a `.csv`, `.xlsx`, `.json`, or `.parquet`
   file.
3. The data appears in the main area as a table. Done.

> Default upload limit is **200 MB**. To change it, see
> [Configuration → Upload size](CONFIGURATION.md#upload-size).

### 1b. API / REST (pull from the web)

1. Choose **API / REST**, then pick a **Provider**:
   - **FRED – Series Observations** — U.S. economic data (free key). Enter a
     series id (e.g. `GDP`, `UNRATE`, `DGS10`) and your FRED key.
   - **Custom URL** — paste any URL that returns JSON or CSV. Optionally give a
     "Records path" (e.g. `data.results`) if the rows are nested inside the
     JSON; leave it blank to auto-detect.
   - **FMP – Historical Prices** — stock prices (requires an FMP key).
2. Enter the API key if prompted. (Store keys once in secrets so you don't
   re-type them — see [Configuration](CONFIGURATION.md#api-keys).)
3. The fetched data loads as the active dataset.

> Tip: data from APIs is often messy — go straight to the **Normalizer**
> (section 3) to standardize dates and price columns.

### 1c. SQL Database

1. Choose **SQL Database**.
2. Pick **Build from fields** (enter host/port/database/user/password) or
   **Full URL / secret** (paste a SQLAlchemy URL like
   `postgresql+psycopg2://user:pass@host:5432/dbname`).
   - Supported: **PostgreSQL, MySQL, SQLite, DuckDB**.
3. Once connected, choose **Load by → Table** (pick a table + a row limit) or
   **Custom SQL** (write your own query — use `LIMIT` to keep it manageable).
4. The query result becomes the active dataset.

> The database must be reachable from wherever the app runs. On the cloud that
> means internet-reachable; to reach a database on your own machine, run the
> app locally (see README → Option B).

### 1d. Google Cloud Storage

1. Choose **Google Cloud Storage (GCS)** (requires a service-account key —
   see [Configuration](CONFIGURATION.md#google-cloud-storage)).
2. Pick a bucket, then pick a file from the explorer.
3. The file loads just like a local upload.

---

## 2. Fix column types (optional)

Open the **"Modify Column Data Types"** panel. For any column you can force it
to **Text, Integer, Float, or Datetime**. Use this when, say, a date came in as
plain text, or numbers were read as text. Leave columns on **No Change** to keep
them as-is.

This matters because filters and charts behave differently per type (a date
column gets a calendar picker; a number column gets a slider).

---

## 3. Standardize price data (Normalizer)

Price data arrives in inconsistent shapes. The **"Normalize price / time-series
data"** panel cleans it up. Open it and tick **"Standardize as time-series /
price data."** Then:

1. **Datetime column** — the app guesses it; confirm or change it.
2. **Map price columns** — match your source columns to the standard names
   `open / high / low / close / adj_close / volume`. The app pre-fills obvious
   matches (e.g. it knows `adjClose` → `adj_close`). Leave any as `—` if absent.
3. **Options:**
   - *Also clean other numeric-looking text columns* — strips `$`, `,`, `%`
     from any column so `"$1,234.50"` becomes `1234.5`.
   - *Set datetime as index* — makes the date the row index (needed for some
     date features and resampling).
   - *Resample frequency* — roll the data up to Daily / Weekly / Monthly
     (OHLC-aware: open=first, high=max, low=min, close=last, volume=sum).

**Why bother?** The candlestick chart and several metrics expect the standard
`open/high/low/close` names. Normalizing once unlocks all of them.

---

## 4. Add technical indicators (optional)

Open **"Technical Indicators"** and tick **"Add technical indicators."**

1. Choose the **price column** (it prefers `adj_close`/`close`/`price`).
2. Pick any of: **SMA, EMA, Returns, Log returns, Cumulative return, Rolling
   volatility, RSI, Bollinger Bands.**
3. For SMA/EMA, type the windows you want, e.g. `20, 50, 200`.

Each indicator is added as a **new column** (e.g. `sma_50`, `rsi_14`,
`bb_upper_20`). Importantly they're computed on the **full series** *before* any
date filtering, so a 200-day average isn't cut short by your date range.

**On the chart:** moving averages (`sma_`, `ema_`) and Bollinger bands (`bb_`)
**automatically overlay** the candlestick/OHLC price chart. Others (RSI,
volatility, returns) become columns you can plot as a Line chart or export.

---

## 5. Filter the data (sidebar)

The **"Filter Workspace"** in the sidebar builds itself from your columns:

- **Date columns / date index** → a from–to calendar picker.
- **Number columns** → a min–max slider.
- **Text/category columns** → a checklist of values to include.

Filtering produces a narrowed view that flows into the table, export, metrics,
and charts below. (The multi-symbol comparison in section 9 deliberately uses
the *full* series, not the filtered view.)

---

## 6. View, edit, and export

- **Data Table (Filtered & Editable)** — your data, formatted (2-decimal
  numbers, `YYYY-MM-DD` dates). You can **edit cells directly** and even add or
  delete rows; edits flow downstream.
- **Export Workspace** — click **Download Filtered Data as CSV** to save the
  current view.

---

## 7. Returns & Risk metrics

Tick **"Show Returns & Risk."** Choose a price column and you get:

| Metric | Meaning |
|---|---|
| **Total Return** | Overall % change start→end |
| **CAGR** | Compound annual growth rate |
| **Annual Volatility** | Annualized standard deviation of returns |
| **Sharpe (rf=0)** | Return per unit of risk (risk-free rate assumed 0) |
| **Max Drawdown** | Largest peak-to-trough drop |
| **Best / Worst Day** | Largest single-period gain/loss |
| **Observations** | Number of data points used |

The app infers whether your data is daily/weekly/monthly from the spacing of
the dates and annualizes accordingly. If there's no date column it assumes
daily.

---

## 8. Data Health Check

Tick **"Show Data Health Check"** for a quick quality snapshot: total rows,
total columns, duplicate rows, and the percentage of missing values per column.
Good for spotting gaps before you trust a chart.

---

## 9. Charts (Visualization Studio)

Pick a **Chart Type**:

- **Line / Bar / Scatter** — choose any column for X and Y. Good for plotting an
  indicator (e.g. `rsi_14` over the date).
- **Candlestick / OHLC** — a proper price chart. Requires standard
  `open/high/low/close` columns (run the **Normalizer**, section 3) and a date
  axis. You get:
  - a **volume sub-panel** if a `volume` column exists,
  - a **Log price scale** checkbox,
  - automatic overlays of any moving-average / Bollinger columns you added.

---

## 10. Compare several symbols

Open **"Multi-Symbol Comparison."** This compares multiple price series — and it
works regardless of where each one came from (upload, FRED, custom API, SQL).

The workflow is **load → add → repeat → compare**:

1. Load symbol A (section 1), pick its **price column**, give it a **label**,
   and click **Add ↗**.
2. Load symbol B, add it. Repeat for as many as you like.
3. Two views appear:
   - **Rebased performance** — every series starts at 100, so you compare
     *growth* regardless of price level (a $40 stock vs a $4,000 index line up).
   - **Return correlation** — a heatmap of how the series' daily returns move
     together (appears once you have ≥2 series).

Use **Remove unselected** or **Clear all** to manage the set. Added series
persist while you keep the app open.

---

## 11. The AI Workspace

Switch to the **🤖 AI Workspace** tab. This is a chat assistant (DeepSeek) that
works *with* your active dataset, not just talks about it.

**Compute mode** (toggle, on by default): ask a question and the assistant
writes a small bit of code, **runs it on your real data**, shows the
result (a number, a table, or a chart), and explains what it means. Examples:

- *"What was the average close in 2024?"*
- *"Plot the 20-day rolling volatility of close and tell me when it peaked."*
- *"Which day had the biggest single-day drop?"*

**It fixes its own mistakes.** If the code hits an error (wrong column name,
etc.), the assistant sees the error, corrects the code, and re-runs — up to a
few attempts — all visible to you in the "Code ran/error" expanders.

**It can help you debug.** Because it has your live data in scope, you can paste
an error or a snippet that's misbehaving and it can reproduce and explain it.

**Turn Compute mode off** for a plain describe-only chat (no code execution),
and use **Clear chat** to start over.

> Safety: the assistant's code runs in a locked-down sandbox — it can only see a
> copy of your data and the analysis libraries, with no file, network, or import
> access. See [Architecture → AI sandbox](ARCHITECTURE.md#the-ai-sandbox).
> Requires a DeepSeek key ([Configuration](CONFIGURATION.md#deepseek-ai)).

---

## A complete example, start to finish

Goal: *candlestick chart of a price series with a 50-day moving average, plus
its annualized volatility.*

1. **Connect** → Local Upload → choose your price CSV.
2. **Normalizer** → tick standardize → confirm the date column → map
   `open/high/low/close` (and `volume` if present) → close the panel.
3. **Indicators** → tick add → SMA windows `50` → also tick **Rolling
   volatility**.
4. **Visualization** → Chart Type **Candlestick**. The 50-day average overlays
   automatically; volume shows beneath.
5. **Returns & Risk** → tick → read the **Annual Volatility** metric.

That's the whole loop. Everything else is variations on it.
