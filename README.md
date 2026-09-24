# F1 Backend

A FastAPI backend for Formula 1 seasons, weekends, sessions, results, drivers,
championship standings, starting grids and position updates. It retrieves data
from OpenF1, downloads flags and portraits from the supplied image URLs, and
caches responses in Redis.

## Run locally

Use Python 3.11 or newer with an activated virtual environment:

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Redis must be available at `127.0.0.1`, or at the hostname set by `REDIS_HOST`.
The local API is available at `http://localhost:8000`, with interactive HTTP
documentation at `/docs` and its OpenAPI schema at `/openapi.json`.

## Endpoints

All endpoints use GET.

| Path | Response |
| --- | --- |
| `/seasons/` | Ascending list of available season years |
| `/seasons/{season}/weekends/` | Weekends with country metadata and encoded flags |
| `/weekend/{weekend_id}/sessions/` | Sessions, including testing days when present |
| `/session/{session_id}/result/` | Session classifications |
| `/seasons/{season}/drivers/{driver_id}/` | Driver profile with an encoded portrait |
| `/standings/{season}/driver_standings/` | Driver championship standings |
| `/standings/{season}/team_standings/` | Team championship standings |
| `/weekend/{weekend_id}/starting_grid/` | Grids associated with qualifying sessions |
| `/grand-prix/{session_id}/positions/` | Chronological position updates with driver profiles |

Weekend IDs are OpenF1 meeting keys, session IDs are OpenF1 session keys and
driver IDs are racing numbers. Country IDs are OpenF1 country keys, not ISO
numeric codes. Country data contains `id`, `name`, `alpha3_code` and
`flag_base64`; no REST Countries enrichment is performed.

## Sphinx documentation

The documentation includes application and route functions, service methods,
private service helpers, response models, caching rules and conversion details.
API references are generated directly from the English reStructuredText
Docstrings (`:param:`, `:return:`, `:raises:`).

From this directory, in an activated Python environment:

```bash
python -m pip install -r requirements-docs.txt
python -m sphinx -b html -W --keep-going docs docs/_build/html
```

Open [docs/_build/html/index.html](docs/_build/html/index.html) after building.
The source starts at [docs/index.rst](docs/index.rst). Generated files are ignored
by Git. Building imports the backend but does not start the application or
require a running Redis server or upstream connection.

## Request pacing

OpenF1 API attempts are spaced at least 2.1 seconds apart within each client.
HTTP 429 responses allow up to two retries, honoring Retry-After when usable.
Up to eight image downloads run concurrently; external image URLs bypass the
OpenF1 API limiters. See [usage and behavior](docs/usage.rst) for caching,
selection rules and error handling.
