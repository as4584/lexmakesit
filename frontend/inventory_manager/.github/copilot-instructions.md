# Project purpose
Build a **Self-Managing Inventory Manager** for a sneaker/clothing shop.

- **POS**: Lightspeed Retail **X-Series** via official API (products, variants, inventory, sales).
- **Ops dashboard**: Google Sheets (source of truth for daily operations).
- **App**: Python 3.11 + Flask + Pandas + gspread; APScheduler hourly sync.
- **No SMS/email alerts** (organization only).

# Must-follow requirements
1) **Lightspeed X-Series API**
   - Use token or OAuth per account setup; handle pagination + rate limits.
   - Endpoints to implement first: products (+variants), inventory by product/variant, sales by date range.
   - Provide `sync_from_ls()` (full sync) and `reconcile_sales()` (apply sales to on-hand).
2) **Google Sheets**
   - Spreadsheet: from `GOOGLE_SHEET_NAME` env.
   - Worksheets:
     - `Inventory`: `ItemID, SKU, Name, Category, Color, Size, Barcode, RetailPrice, QtyOnHand, QtySold, Location, LastUpdated`
     - `Config`: `LowStockThreshold` (default 5)
     - `SalesLog`: de-duplication hashes for sales rows
     - `RestockList`: auto-maintained items under threshold
3) **Business logic**
   - `auto_sort(df)`: Category → Name → Size; consistent formatting.
   - `low_stock(df)`: filter by threshold; mirror to `RestockList`.
   - Idempotent reconciliation (no double-decrement if same sale ingested twice).
4) **Flask UI**
   - `/` dashboard tiles (total SKUs, on-hand, low-stock count).
   - `/inventory` searchable/sortable table.
   - `POST /sync` (manual full sync), `POST /ingest-csv` (upload LS CSV fallback).
5) **Jobs**
   - Hourly: `sync_from_ls()`.
   - Nightly: `auto_sort` + CSV backup export.

# Folder structure to scaffold
/lightspeed-inventory
├─ app.py
├─ services/
│  ├─ ls_auth.py
│  ├─ ls_api.py
│  ├─ ls_webhooks.py            # optional if store enables webhooks
│  ├─ csv_ingest.py
│  ├─ sheets.py
│  └─ inventory.py
├─ web/
│  └─ templates/{index.html,inventory.html,low_stock.html}
├─ jobs/scheduler.py
├─ sample_data/{sales.csv,products.csv}
├─ tests/
├─ .env.example
├─ requirements.txt
└─ README.md

# Environment variables (.env.example)
GOOGLE_SERVICE_ACCOUNT_JSON=./service_account.json
GOOGLE_SHEET_NAME=Live ATS Inventory
LS_X_API_TOKEN= # or OAuth envs if used
LS_ACCOUNT_DOMAIN=

# Acceptance criteria
- Running the app serves on port 8000.
- Full sync pulls products/variants + current stock from Lightspeed to Google Sheet.
- Uploading a Sales CSV or calling `/sales?from=YYYY-MM-DD&to=YYYY-MM-DD` updates on-hand, qty sold, and RestockList.
- Pagination and rate limiting respected; sheet stays sorted after operations.

# Coding style
- Small, testable functions; type hints; docstrings.
- Clear, conventional commits (e.g., `feat(ls_api): paginate products`).
- Add pytest for reconciliation math, de-dup, and CSV parsing.

# Helpful links (for the agent)
- Lightspeed X-Series API hub & tutorials (auth, pagination, rate limits, inventory updates).
- Google Sheets API (gspread) usage patterns.