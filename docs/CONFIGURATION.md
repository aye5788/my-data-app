# Configuration

The app works with **no configuration at all** for local file uploads and
charting. The optional features — AI chat, web APIs, SQL databases, and Google
Cloud Storage — need credentials. This page explains how to provide them.

Credentials live in a file called **`secrets.toml`** (the Streamlit standard).
Nothing here is ever committed to git: `.streamlit/secrets.toml`, `.env`, and
`gcs_key.json` are all in `.gitignore`. Keep it that way.

---

## Where secrets go

### Running locally / desktop

Create a file at **`.streamlit/secrets.toml`** in the project folder. Streamlit
reads it automatically when you run `streamlit run app.py`.

### Running on Streamlit Community Cloud

Don't put a file in the repo. Instead, open your app in the
[Streamlit Cloud dashboard](https://share.streamlit.io) →
**Settings → Secrets**, and paste the same TOML content into that box. Save and
the app reboots with the secrets available.

---

## The full `secrets.toml` template

Include only the sections you need; delete the rest.

```toml
# --- AI assistant (DeepSeek) ---
DEEPSEEK_API_KEY = "sk-your-deepseek-key"

# --- API keys for the REST connector ---
[api_keys]
fred = "your-fred-key"
fmp  = "your-fmp-key"        # only if you have an FMP subscription

# --- SQL database (optional: prefills the connection URL) ---
[connections.sql]
url = "postgresql+psycopg2://user:pass@host:5432/dbname"

# --- Google Cloud Storage service account ---
[connections.gcs]
type = "service_account"
project_id = "your-project-id"
private_key_id = "..."
private_key = """-----BEGIN PRIVATE KEY-----
...multiple lines...
-----END PRIVATE KEY-----
"""
client_email = "name@your-project.iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
```

> **TOML gotcha — the GCS private key.** It's long and contains newlines. Paste
> it as a **triple-quoted** (`"""…"""`) block exactly as shown, with real line
> breaks. Pasting it as one giant single-quoted line is the most common cause of
> an "Invalid TOML format" error.

---

## Feature-by-feature

### DeepSeek AI

The AI Workspace needs `DEEPSEEK_API_KEY`. Without it the tab shows a "not
configured" notice and the rest of the app works normally. Get a key from your
DeepSeek account; it's used to call `deepseek-chat`.

```toml
DEEPSEEK_API_KEY = "sk-..."
```

### API keys (REST connector)

Keys for the API / REST connector go under `[api_keys]`, keyed by provider name
(`fred`, `fmp`). If a key is present there, the connector uses it automatically
and you won't be prompted. If it's absent, you can still type it into the
sidebar each session (it's never saved).

```toml
[api_keys]
fred = "..."
```

- **FRED** keys are free from the St. Louis Fed.
- **FMP** requires a paid subscription. If you don't have one, use FRED, a
  Custom URL, SQL, or local upload instead.

### SQL database

Two ways to connect (see [User Guide §1c](USER_GUIDE.md#1c-sql-database)):

1. **In the UI** — fill in host/port/database/user/password, or paste a full
   SQLAlchemy URL. Nothing needs to be in secrets.
2. **Prefill from secrets** — store a URL so it's ready each time:

```toml
[connections.sql]
url = "mysql+pymysql://user:pass@host:3306/dbname"
```

URL formats by database:

| Database | URL prefix | Example |
|---|---|---|
| PostgreSQL | `postgresql+psycopg2://` | `postgresql+psycopg2://u:p@host:5432/db` |
| MySQL | `mysql+pymysql://` | `mysql+pymysql://u:p@host:3306/db` |
| SQLite | `sqlite:///` | `sqlite:////absolute/path/to/file.db` |
| DuckDB | `duckdb:///` | `duckdb:////absolute/path/to/file.duckdb` |

> **Reachability:** on Streamlit Cloud the database must be reachable from the
> public internet. SQLite/DuckDB files and LAN databases only work when you run
> the app locally.

### Google Cloud Storage

The GCS connector authenticates two ways, in this order:

1. **From secrets** — the `[connections.gcs]` service-account block above. This
   is what Streamlit Cloud uses (there's no key file on disk there).
2. **Application Default Credentials** — if no secret is present, it falls back
   to ADC (e.g. a `gcs_key.json` referenced by `GOOGLE_APPLICATION_CREDENTIALS`,
   or `gcloud auth` on your machine). Handy for local/desktop use.

The service account needs read access to the buckets you want to browse.

---

## Upload size

The local-upload limit defaults to **200 MB**. To change it, create
**`.streamlit/config.toml`**:

```toml
[server]
maxUploadSize = 500    # megabytes
```

(Bigger limits use more of the instance's memory — on the cloud free tier,
~1 GB RAM total, so keep large files modest or run locally.)

---

## Deployment notes

- The app deploys to Streamlit Community Cloud from the GitHub repo. **Every
  push to `master` triggers an automatic redeploy.**
- The repo is **public** (the free tier allows only one private app). Because no
  secrets are ever committed, a public repo is safe — secrets live only in the
  Cloud dashboard.
- Dependencies are pinned in `requirements.txt`; Streamlit Cloud installs them
  on each deploy.

---

## Security checklist

- ✅ `secrets.toml`, `.env`, `gcs_key.json` are git-ignored — never commit them.
- ✅ On the cloud, secrets live only in the dashboard, not the repo.
- ✅ API keys typed into the UI are used for that session only and not persisted.
- ✅ The AI assistant runs code in a sandbox with no file/network/import access
  (see [Architecture → AI sandbox](ARCHITECTURE.md#the-ai-sandbox)).
