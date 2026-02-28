# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Docs: Lightspeed API overview with ERP mapping (`docs/lightspeed_api_overview.md`).
- Test DX: Fast, deterministic pytest setup (pytest 8, xdist, timeout, randomly, freezegun) with `PYTEST_RUNNING` anti-hang fixture.
- VS Code: Settings to use in-project `.venv` and auto test discovery on save.
 - Demo Mode: Local fixtures for Lightspeed API, UI banner, and `/health` endpoint reporting `demo_mode` and `sheets_configured`.
 - Sheets: New POST `/sync/sheets/full` route that writes Inventory and mirrors RestockList in Demo Mode.

### Changed
- Flask UI: Dashboard and Inventory templates/text adjusted to satisfy tests (labels, metrics visible).
- CSV Ingest: Variant extraction prefers numeric sizes from SKU (e.g., `9.5`), better color parsing.
- Inventory Service: Added compatibility service exposing expected API (apply batches, idempotent `sync_with_deduplication`, low-stock helpers).

### Fixed
- Import stability via legacy shims (e.g., `services.ls_api`) and Sheets credentials import path.
- Type/lint issues in ingest and services modules.
 - Demo Mode: Prevent infinite pagination by applying `limit/offset` slicing to fixtures in `LightspeedGateway`.
 - LightspeedGateway: Correct pagination semantics (stable offsets per call, optional final empty page) and default `rate_limit_delay=0.0` to satisfy tests.

### CI/Security
- Ensure Poetry in-project venv usage; test configuration consolidated in `pyproject.toml`.
- Keep security scans and caches (prior hardening preserved).

### Planned
- Email notifications for low stock alerts
- Advanced reporting and analytics dashboard
- Multi-location inventory support
- Barcode scanning integration

---

## [1.0.0] - 2025-10-10

### 🎉 Initial Production Release

This is the first production-ready release of the Self-Managing Inventory Manager.

### Added

#### Core Features
- **Lightspeed X-Series Integration**
  - Full product and variant sync from Lightspeed POS
  - Inventory level synchronization with pagination support
  - Sales data reconciliation by date range
  - Rate limiting and retry logic with exponential backoff
  - OAuth and token-based authentication support

- **Google Sheets Backend**
  - Automated sync to Google Sheets as source of truth
  - Four worksheets: Inventory, Config, SalesLog, RestockList
  - Automatic data sorting (Category → Name → Size)
  - De-duplication of sales records via hash tracking
  - Low stock threshold configuration (default: 5 units)

- **Web Dashboard**
  - Flask-based responsive web interface with Bootstrap 5
  - Dashboard homepage with key metrics (total SKUs, on-hand quantity, low-stock count)
  - Searchable and sortable inventory table
  - Low stock alerts page with automatic restock list
  - Manual sync trigger via `/sync` endpoint

- **Background Jobs**
  - Hourly automatic sync from Lightspeed (APScheduler)
  - Nightly maintenance: auto-sort and CSV backup export
  - Configurable job scheduling

- **CSV Import/Export**
  - CSV upload fallback for manual data ingestion
  - Validation and error handling for CSV files
  - Sample data templates included
  - Automated daily backup exports

#### Development & Quality
- **Testing Framework**
  - pytest test suite with 80% coverage requirement
  - Unit tests for reconciliation logic, CSV parsing, API pagination
  - Mock fixtures for external API dependencies
  - CI/CD integration with automated test runs

- **Code Quality Tools**
  - Ruff linting and formatting
  - mypy strict type checking
  - Pre-commit hooks for automatic validation
  - Comprehensive Makefile with development commands

- **CI/CD Pipeline**
  - GitHub Actions workflow for lint, format, type-check
  - Automated test execution on Python 3.11 and 3.12
  - Coverage reporting with Codecov integration
  - Security scanning with Bandit, Safety, pip-audit

- **Security**
  - CodeQL weekly security scanning
  - Dependabot automated dependency updates (weekly)
  - Bandit security linter for Python code
  - Safety vulnerability scanner for dependencies
  - Secure credential management via environment variables

#### Documentation
- **Comprehensive Documentation**
  - Detailed README with setup instructions
  - Architecture overview and project structure
  - API endpoint documentation
  - Environment variable configuration guide
  - Development workflow guidelines

- **Code Documentation**
  - Docstrings for all public functions and classes
  - Type hints throughout codebase
  - Inline comments for complex logic

### Technical Details

- **Python**: 3.11+ required
- **Framework**: Flask 3.0.0
- **Data Processing**: Pandas 2.1.4
- **Scheduling**: APScheduler 3.10.4
- **Google Sheets**: gspread 5.12.0
- **Testing**: pytest 7.4.3

### Known Limitations

- SMS/email notifications not implemented (organization use only)
- Single location support only (multi-location planned for v2.0)
- Manual Google Sheets service account setup required
- Lightspeed API token must be manually provisioned

### Migration Notes

This is the first release. No migration needed.

---

## [0.2.0] - 2025-10-05

### Added
- CSV import functionality for manual data uploads
- Sample data files for testing (products.csv, sales.csv)
- Mock data patterns for development without Lightspeed API

### Changed
- Refactored services to use shared HTTP client utilities
- Improved error handling in Lightspeed API calls
- Enhanced CSV validation with detailed error messages

### Fixed
- Fixed pagination issue with large product catalogs
- Fixed race condition in sales reconciliation
- Fixed cryptography dependency version conflict

---

## [0.1.0] - 2025-10-01

### Added
- Initial project scaffold
- Basic Flask application structure
- Service stubs for Lightspeed API and Google Sheets
- Basic HTML templates with Bootstrap
- Development environment setup
- Git repository initialization

---

## Version History Summary

| Version | Date | Type | Status |
|---------|------|------|--------|
| 1.0.0 | 2025-10-10 | Major | ✅ Current |
| 0.2.0 | 2025-10-05 | Minor | Deprecated |
| 0.1.0 | 2025-10-01 | Initial | Deprecated |

---

## Release Notes Guidelines

When adding entries to this changelog:

### Categories (in order):
1. **Added** - New features
2. **Changed** - Changes in existing functionality
3. **Deprecated** - Soon-to-be removed features
4. **Removed** - Removed features
5. **Fixed** - Bug fixes
6. **Security** - Security fixes

### Format:
- Use present tense ("Add feature" not "Added feature")
- Reference issue numbers: `(#123)`
- Group related changes under subheadings
- Include migration notes for breaking changes
- Mark security fixes with `[SECURITY]`

### Example Entry:
```markdown
## [1.1.0] - 2025-11-10

### Added
- Email notifications for low stock alerts (#45)
- New `/api/reports` endpoint for custom reports

### Changed
- Improved sync performance by 30% (#52)
- Updated to Python 3.12 as recommended version

### Fixed
- Fixed memory leak in long-running sync jobs (#48)
- Resolved timezone handling in sales reports (#50)

### Security
- [SECURITY] Patched XSS vulnerability in search (#49, CVE-2025-1234)
```

---

## Links

- **GitHub Releases**: [View all releases](https://github.com/your-org/inventory-manager/releases)
- **Versioning Guide**: See `docs/VERSIONING.md`
- **Security Policy**: See `SECURITY.md`

[Unreleased]: https://github.com/your-org/inventory-manager/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/your-org/inventory-manager/releases/tag/v1.0.0
[0.2.0]: https://github.com/your-org/inventory-manager/releases/tag/v0.2.0
[0.1.0]: https://github.com/your-org/inventory-manager/releases/tag/v0.1.0
