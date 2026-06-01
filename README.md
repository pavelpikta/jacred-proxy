# jacred-proxy

A Python [Flask](https://flask.palletsprojects.com/) service that sits in front of a [JacRed](https://github.com/jacred-fdb/jacred) torrent aggregator and exposes **Torznab** and **Jackett-compatible** HTTP APIs. Clients such as Sonarr, Radarr, Prowlarr, AIOStreams, qBittorrent (Jackett search plugin), and Lampa can search JacRed without speaking its native API directly.

**Version:** 1.0.0 · **License:** [MIT](LICENSE) · **Python:** ≥ 3.9

## What it does

```
Client (Torznab / Jackett JSON)
        │
        ▼
   jacred-proxy  :5002
        │
        ├─► JacRed v2  GET /api/v2.0/indexers/all/results
        └─► JacRed v1  GET /api/v1.0/torrents   (optional merge)
        │
        ▼
   Torznab RSS XML  or  Jackett JSON
```

The proxy translates client requests into JacRed backend calls, merges v1 and v2 results (deduplicated by infohash), normalizes fields, and returns responses in the format each client expects.

## Features

- **Torznab RSS** — `/api` and Jackett-style Torznab paths for *arr apps and AIOStreams
- **Jackett JSON** — `/api/v2.0/indexers/.../results` for Lampa, qBittorrent Jackett plugin, and similar clients
- **Card vs fuzzy search** — detects Lampa-style metadata searches (`title`, `year`, `Category[]`) vs free-text queries and adjusts backend strategy
- **v1 + v2 merge** — optional legacy v1 API queries merged with v2 for broader coverage (`JACRED_MERGE_V1`, default on)
- **Bilingual queries** — splits `local / original` titles and runs RU/EN query variants
- **Title enrichment** — optional voice-track tags in Torznab titles (`JACRED_ENRICH_TITLES`)
- **Category handling** — respects requested Torznab category (movie/TV/anime) instead of always defaulting to movies
- **Rotating logs** — file + stdout, API keys redacted in debug output
- **Docker-ready** — production image runs **gunicorn** via `jacred_proxy.wsgi:app`

## Custom behavior (AIOStreams / Lampa)

This fork includes optimizations tuned for **AIOStreams** and **Lampa** integration:

| Behavior | Env var | Default | Notes |
|----------|---------|---------|-------|
| Append voice tags and `[].rus` to Torznab titles | `JACRED_ENRICH_TITLES` | `true` | Non-Russian releases may still get a `.rus` suffix when no voice metadata is present |
| Strip trailing `(19\|20)xx` from free-text `q` | `JACRED_STRIP_YEAR` | `false` | Improves fuzzy search when clients append release year |
| Return requested category on items | *(always on)* | — | `t=moviesearch` → 2000, `t=tvsearch` → 5000, or `cat=` param |

To restore plain titles, set `JACRED_ENRICH_TITLES=false`. To enable year stripping, set `JACRED_STRIP_YEAR=true`.

## HTTP API

### Torznab (Sonarr / Radarr / AIOStreams)

| Route | Purpose |
|-------|---------|
| `GET /api` | Short Torznab URL — e.g. `http://host:5002/api` |
| `GET /api/v2.0/indexers/<status>/results/torznab/api` | Jackett-style Torznab path (qBittorrent plugin) |

Common query parameters:

| Param | Description |
|-------|-------------|
| `t=caps` | Capabilities document |
| `t=indexers&configured=true` | Indexer list (returns aggregate `all`) |
| `t=search` | General search |
| `t=moviesearch` | Movie search (`cat` → 2000) |
| `t=tvsearch` | TV search (`cat` → 5000); supports `season`, `ep` |
| `q` or `Query` | Search text |
| `title`, `title_original`, `year`, `is_serial`, `genres`, `Category[]` | Lampa card-style metadata |
| `apikey` | Passed through to JacRed when set |

### Jackett JSON

| Route | Purpose |
|-------|---------|
| `GET /api/v2.0/indexers` | Indexer list (single aggregate `all` entry) |
| `GET /api/v2.0/indexers/<status>/results` | Search; returns `{"Results": [...]}` |
| `GET /api/v1/indexer` | Minimal Prowlarr-style stub |

`<status>` is typically `all`. Search accepts the same metadata params as Torznab (`Query`, `title`, `Category[]`, etc.).

### System

| Route | Purpose |
|-------|---------|
| `GET /version` | Proxy version; forwards to JacRed `/version` when reachable |
| `GET /lastupdatedb` | JacRed database last-update timestamp |

## Installation

### Prerequisites

- Python **3.9+**
- A running **JacRed** instance (default `http://127.0.0.1:9117`)

### From source

```bash
git clone https://github.com/pavelpikta/jacred-proxy.git
cd jacred-proxy

python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
pip install -e .
```

Run the development server:

```bash
jacred-proxy
# or
python -m jacred_proxy
```

Production (install gunicorn extra):

```bash
pip install ".[production]"
gunicorn -b 0.0.0.0:5002 jacred_proxy.wsgi:app
```

The service listens on **port 5002** by default.

### Package naming

| Context | Name |
|---------|------|
| PyPI / `pip install` | `jacred-proxy` (hyphen) |
| Python import / `python -m` | `jacred_proxy` (underscore) |
| Source directory | `jacred-proxy/` |

Per [PEP 503](https://peps.python.org/pep-0503/), the install name and import name differ by design.

## Project layout

```
jacred-proxy/                 # Python package (import: jacred_proxy)
  __main__.py                 # CLI: jacred-proxy / python -m jacred_proxy
  app.py                      # Flask application factory
  config.py                   # Settings from environment
  wsgi.py                     # Gunicorn entry: jacred_proxy.wsgi:app
  backend/
    client.py                 # HTTP client for JacRed
    v1.py                     # Legacy /api/v1.0/torrents
    v2.py                     # Jackett v2 /api/v2.0/indexers/.../results
    search.py                 # Card/fuzzy modes, v1+v2 merge
  formats/
    torznab_xml.py            # Torznab RSS/XML builders
    jackett_json.py           # Jackett JSON result mapping
  routes/
    torznab.py                # Torznab blueprints
    jackett.py                # Jackett JSON blueprints
    system.py                 # /version, /lastupdatedb
pyproject.toml                # Distribution metadata (version 1.0.0)
requirements.txt              # Runtime deps: Flask, requests
Dockerfile                    # python:3.12-slim + gunicorn
docker-compose.example.yml    # Example stack: jacred-proxy + JacRed
```

## Configuration

All settings are read from **environment variables** at startup.

| Variable | Default | Description |
|----------|---------|-------------|
| `JACRED_BASE_URL` | `http://127.0.0.1:9117` | JacRed base URL (**must be reachable from the proxy process**) |
| `JACRED_APIKEY` | *(empty)* | JacRed API key; also accepted per-request via `apikey` query param |
| `JACRED_TIMEOUT` | `20` | Backend HTTP timeout (seconds) |
| `JACRED_MERGE_V1` | `true` | Also query v1 `/api/v1.0/torrents` and merge by infohash |
| `JACRED_STRIP_YEAR` | `false` | Strip trailing year from free-text `q` before search |
| `JACRED_ENRICH_TITLES` | `true` | Append voice tags / `[].rus` to Torznab item titles |
| `JACRED_SKIP_CAT_FILTER` | `false` | Torznab only: skip post-merge `cat=` trimming (max result count) |
| `HOST` | `0.0.0.0` | Bind address |
| `PORT` | `5002` | Listen port |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `LOG_FILE` | `/tmp/jacred_proxy.log` | Rotating log file (10 MB × 5 backups) |
| `GUNICORN_WORKERS` | `2` | Worker processes (Docker / gunicorn only) |
| `GUNICORN_TIMEOUT` | `30` | Gunicorn worker timeout; should be ≥ `JACRED_TIMEOUT` |

Example local shell:

```bash
export JACRED_BASE_URL="http://127.0.0.1:9117"
export JACRED_APIKEY="your-api-key"
export PORT=5002
export LOG_LEVEL="INFO"
jacred-proxy
```

## Docker

The image installs the package with the `production` extra and runs **gunicorn**, not the Flask dev server.

**Important:** Inside a container, `JACRED_BASE_URL` must point to JacRed on the Docker network (e.g. `http://jacred:9117`), not `127.0.0.1` unless JacRed runs in the same container.

### Build and run

```bash
docker build -t jacred-proxy:latest .

docker run -d \
  --name jacred-proxy \
  -p 5002:5002 \
  -e JACRED_BASE_URL="http://jacred:9117" \
  -e JACRED_APIKEY="your-api-key" \
  jacred-proxy:latest
```

Do **not** bake `JACRED_APIKEY` into the image; pass it at runtime (`-e` or compose `env_file`).

### Docker Compose

Copy [`docker-compose.example.yml`](docker-compose.example.yml) to `docker-compose.yml`, set secrets, and adjust the `jacred` service image to match your deployment:

```bash
cp docker-compose.example.yml docker-compose.yml
docker compose up -d
```

The example wires `jacred-proxy` → `http://jacred:9117` on a shared network and publishes ports **5002** (proxy) and **9117** (JacRed).

## Client setup

### AIOStreams

1. Plugins → Marketplace → **Torznab**
2. **URL:** `http://<proxy-host>:5002`
3. **Path:** `/api`
4. **API key:** same as JacRed (or leave empty if JacRed has no key)

### Sonarr / Radarr

1. Settings → Indexers → **+** → **Torznab**
2. **URL:** `http://<proxy-host>:5002/api`
3. **API Key:** optional (must match JacRed if required)
4. Test and save

### qBittorrent (Jackett search plugin)

Install the [Jackett search plugin](https://github.com/qbittorrent/search-plugins/wiki/How-to-configure-Jackett-plugin), then edit `nova3/engines/jackett.json`:

```json
{
    "api_key": "1",
    "url": "http://127.0.0.1:5002",
    "tracker_first": false,
    "thread_count": 1
}
```

Point **`url`** at this proxy (port **5002**), not JacRed directly (port **9117**). Use `thread_count: 1` to search the aggregate `all` indexer once.

### Lampa

Point the Jackett integration URL to the proxy (`http://<host>:5002`), not JacRed.

Lampa uses two search patterns via `GET /api/v2.0/indexers/all/results`:

**Card search** (movie/serial detail page) sends metadata:

- `title`, `title_original`, `year`, `is_serial`, `genres`
- `Category[]=2000` or `5000` (and `5070` for anime)

JacRed uses exact bucket lookup; `Query` may be present but is ignored when `title` is set. The proxy uses **card mode**: one v2 request with all params, plus v1 merge when enabled.

**Global parser search** sends only `Query` — fuzzy fastdb search. The proxy uses **fuzzy mode**: multiple v2 query variants (RU/EN) and v1 `search`/`altname` pairs.

| Mode | v2 behavior | v1 merge |
|------|-------------|----------|
| Card (Lampa detail) | Single Lampa-style v2 call | Always when `JACRED_MERGE_V1=true` |
| Fuzzy / Torznab | Per query variant | Multiple search pairs |

## Search examples

```bash
# Capabilities
curl 'http://localhost:5002/api?t=caps'

# Movie search
curl 'http://localhost:5002/api?t=moviesearch&q=Inception'

# TV search
curl 'http://localhost:5002/api?t=tvsearch&q=Breaking+Bad&season=1&ep=1'

# Jackett JSON
curl 'http://localhost:5002/api/v2.0/indexers/all/results?Query=matrix'
```

## Logging

Logs go to **stdout** and to `LOG_FILE` (rotating, 10 MB, 5 backups). Format includes timestamp, level, function, and line number. Backend requests are logged with `[BACKEND]`, Torznab with `[TORZNAB]`, Jackett JSON with `[JACKETT]`.

```bash
tail -f /tmp/jacred_proxy.log
grep '\[TORZNAB\]' /tmp/jacred_proxy.log
grep '\[JACRED\]' /tmp/jacred_proxy.log   # legacy tag; backend uses [BACKEND]
grep '\[BACKEND\]' /tmp/jacred_proxy.log
```

## Troubleshooting

### Connection refused

- Confirm JacRed is running and reachable at `JACRED_BASE_URL`
- In Docker, use the service hostname (`http://jacred:9117`), not `localhost`
- Check firewall rules between proxy and JacRed containers/hosts

### 401 Unauthorized

- Set `JACRED_APIKEY` or pass `apikey` in client requests
- Verify the key matches JacRed configuration

### No or fewer results than JacRed UI

- Inspect logs: `grep '\[BACKEND\]' /tmp/jacred_proxy.log`
- JacRed fuzzy search is capped by `maxreadfile` in JacRed's `init.conf` (often **200**)
- Disable v1 merge temporarily: `JACRED_MERGE_V1=false` to compare v2-only counts
- Ensure query params match the intended mode (card metadata vs free-text `q`)

### Wrong categories or dropped results (AIOStreams)

- Use `t=moviesearch` / `t=tvsearch` or explicit `cat=` — the proxy assigns category from the request
- Set `JACRED_ENRICH_TITLES=false` if title suffixes confuse downstream filtering

### Timeouts

- Increase `JACRED_TIMEOUT` and `GUNICORN_TIMEOUT` together
- Reduce concurrent load or JacRed backend latency

## Development

```bash
pip install -e .
LOG_LEVEL=DEBUG jacred-proxy
```

Build check after CPython changes:

```bash
pip install -e .
python -c "from jacred_proxy import create_app; create_app()"
```

## Contributing

Issues and pull requests are welcome on [GitHub](https://github.com/pavelpikta/jacred-proxy).

## License

Copyright (c) 2026 [Pavel Pikta](https://github.com/pavelpikta). Released under the [MIT License](LICENSE).
