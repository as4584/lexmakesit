# Demo Instructions

## Quickstart (Demo Mode)
```bash
cp .env.example .env
export DEMO_MODE=true
poetry install
poetry run python app.py
```
Open http://localhost:8000

## Expected outputs
- Homepage shows key metrics and “Demo Mode Active” banner
- /inventory lists sample items with counts
- /health returns JSON: { status, demo_mode: true, sheets_configured }

## Optional: Sheets sync demo (fixture-backed)
```bash
curl -X POST http://localhost:8000/sync/sheets/full
```
Expected JSON: { status: "success", rows_written, low_stock_count, demo_mode: true }

## Screenshots (thumbnails)
- Dashboard: ![Dashboard](/docs/assets/dashboard.png)
- Health: ![Health](/docs/assets/health.png)
