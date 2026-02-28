# DonxEra Inventory Manager – Executive Summary (IS344/IS218)

## Purpose
A self-managing inventory system for a sneaker/clothing shop, optimized for class demos and recruiter reviews. It integrates Lightspeed Retail X-Series (POS) and Google Sheets (Ops dashboard) with a Flask app and automated jobs.

## ERP data at a glance
- Organizational: Store locations
- Master: Products, variants, pricing
- Transactional: Inventory on hand, sales

## How it works
1) Sync products/variants from Lightspeed
2) Fetch inventory and compute low stock
3) Persist to Google Sheets (source of truth)
4) Reconcile sales and update on-hand
5) Nightly sort and CSV backup

Demo Mode bypasses external services and uses local fixtures to ensure deterministic, credential-free runs.

## Architecture
- Flask UI (Dashboard, Inventory)
- Infra adapters: LightspeedGateway (API), SheetsRepository (gspread)
- Services: CSV ingest, Inventory operations
- Jobs: Hourly sync, nightly maintenance

## Demo Mode
- No network calls
- Lightspeed fixture-backed endpoints (products/inventory/sales)
- Banner in UI + /health JSON reports demo_mode

## Screenshots
- Dashboard: ![Dashboard](/docs/assets/dashboard.png)
- Health: ![Health](/docs/assets/health.png)

## Links
- Lightspeed API overview: /docs/lightspeed_api_overview.md
- Quickstart: /docs/QUICKSTART.md
- Changelog: /CHANGELOG.md
