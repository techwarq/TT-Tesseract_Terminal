# Market Intelligence Terminal

A focused internal, Bloomberg-style terminal (Textual TUI) with two modules:
- Public Stocks
- Startup Signals

The UI is intentionally compact, dark, and data-dense with keyboard-friendly navigation. Data is mocked behind clean interfaces so real sources can be swapped in later.

## Stack
- UI: Textual (Python TUI)
- Backend: FastAPI

## Folder Structure
- `/Users/sonalinayak/br-terminal/tui`: Textual UI
- `/Users/sonalinayak/br-terminal/backend`: FastAPI API

## TUI Architecture
- `tui/app.py` defines the Textual interface, tabs, and data views
- Uses HTTP calls to the FastAPI endpoints

Keyboard navigation:
- `1` → Stocks
- `2` → Startups
- `Arrow Up / Arrow Down` navigates tables
- `q` quits

## Backend Architecture
- `app/data.py` stores mock data
- `app/models.py` defines Pydantic models and transformations
- `app/main.py` exposes placeholder endpoints

Endpoints:
- `GET /api/stocks/overview`
- `GET /api/stocks`
- `GET /api/stocks/{ticker}`
- `GET /api/stocks/watchlist`
- `GET /api/startups`
- `GET /api/startups/{startup_id}`

## Running Locally

### Backend
```bash
cd /Users/sonalinayak/br-terminal/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### TUI
```bash
cd /Users/sonalinayak/br-terminal/tui
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Future Data Upgrades
- Replace `backend/app/data.py` with:
  - Daily/weekly batch jobs for market snapshots
  - ETL pipelines for startup signals (hiring/buzz/event detection)
  - Cached time-series storage (Postgres + Timescale or ClickHouse)
- Add auth + rate limits for internal access

## Notes
- No trading or order execution is implemented.
- Data is daily/weekly mock data only; no real-time tick data.
- No news feed is included.
