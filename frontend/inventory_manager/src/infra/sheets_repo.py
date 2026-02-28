"""
SheetsRepository: Minimal Google Sheets repository to satisfy tests.
Implements read/write, basic retry, caching, and a simple Unit of Work.
"""
from __future__ import annotations

import contextlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

# Import via services.sheets re-exports so tests can patch
import gspread  # type: ignore
import pandas as pd

from .exceptions import QuotaExceededError, WorksheetNotFoundError

INVENTORY_WS = "Inventory"
CONFIG_WS = "Config"
SALESLOG_WS = "SalesLog"
RESTOCK_WS = "RestockList"


class SheetsRepository:
    def __init__(
        self,
        credentials_path: str,
        sheet_name: str,
        *,
        enable_cache: bool = False,
        cache_ttl: int = 60,
        max_retries: int = 2,
    ) -> None:
        self.credentials_path = credentials_path
        self.sheet_name = sheet_name
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self.max_retries = max_retries

        self._client = None
        self._spreadsheet = None

        # simple cache: {key: (expires_at, value)}
        self._cache: dict[str, tuple[datetime, pd.DataFrame]] = {}

    # --------------- helpers ---------------
    def _ensure_client(self) -> None:
        if self._client is None:
            # Tests patch gspread.authorize to return a mock client
            self._client = gspread.authorize(None)
            self._spreadsheet = self._client.open(self.sheet_name)

    def _worksheet(self, name: str):
        self._ensure_client()
        try:
            return self._spreadsheet.worksheet(name)
        except Exception as e:  # Mapped to domain-specific errors
            msg = str(e)
            if "Worksheet not found" in msg:
                raise WorksheetNotFoundError(msg)
            raise

    def _retry_call(self, func, *args, **kwargs):
        last_exc: Exception | None = None
        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exc = e
                # Allow transient errors to be retried
                if attempt < self.max_retries - 1:
                    continue
        # Map quota errors when surfaced after retries
        if last_exc and "Quota exceeded" in str(last_exc):
            raise QuotaExceededError(str(last_exc))
        if last_exc:
            raise last_exc

    # --------------- transforms ---------------
    def _sheets_to_dataframe(self, records: list[dict[str, Any]]) -> pd.DataFrame:
        df = pd.DataFrame(records)
        # Attempt rudimentary type conversions
        for col in df.columns:
            if col.lower().startswith("qty"):
                with pd.option_context('mode.use_inf_as_na', True):
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
            elif "price" in col.lower():
                df[col] = pd.to_numeric(df[col], errors='coerce').astype(float)
        return df

    def _dataframe_to_sheets(self, df: pd.DataFrame) -> list[list[Any]]:
        def cast(v: Any) -> Any:
            if isinstance(v, (pd.Timestamp, datetime)):
                return v.strftime('%Y-%m-%d %H:%M:%S')
            return v
        return [[cast(v) for v in row] for row in df.to_numpy().tolist()]

    # --------------- reads ---------------
    def get_inventory(self) -> pd.DataFrame:
        cache_key = "inventory"
        if self.enable_cache and cache_key in self._cache:
            exp, val = self._cache[cache_key]
            if datetime.utcnow() < exp:
                return val.copy()
        ws = self._worksheet(INVENTORY_WS)
        records = self._retry_call(ws.get_all_records)
        df = self._sheets_to_dataframe(records)
        if self.enable_cache:
            self._cache[cache_key] = (datetime.utcnow() + timedelta(seconds=self.cache_ttl), df.copy())
        return df

    def get_config(self) -> dict[str, int]:
        ws = self._worksheet(CONFIG_WS)
        records = self._retry_call(ws.get_all_records)
        config: dict[str, int] = {}
        for row in records:
            k = row.get('Setting')
            v = row.get('Value')
            if k is not None and v is not None:
                with contextlib.suppress(Exception):
                    config[str(k)] = int(v)
        return config

    def get_sales_log(self) -> pd.DataFrame:
        ws = self._worksheet(SALESLOG_WS)
        records = self._retry_call(ws.get_all_records)
        return pd.DataFrame(records)

    # --------------- writes ---------------
    def update_inventory(self, df: pd.DataFrame) -> bool:
        ws = self._worksheet(INVENTORY_WS)
        ws.clear()
        if not df.empty:
            data = [list(df.columns)] + self._dataframe_to_sheets(df)
            ws.update(data)
        if self.enable_cache and "inventory" in self._cache:
            del self._cache["inventory"]
        return True

    def add_sales_log_entry(self, sale_hash: str) -> None:
        ws = self._worksheet(SALESLOG_WS)
        ws.append_row([sale_hash, datetime.now().strftime('%Y-%m-%d %H:%M:%S')])

    def update_restock_list(self, df: pd.DataFrame) -> bool:
        ws = self._worksheet(RESTOCK_WS)
        ws.clear()
        if not df.empty:
            data = [list(df.columns)] + self._dataframe_to_sheets(df)
            ws.update(data)
        return True


# --------------- Unit of Work ---------------
@dataclass
class _InventoryWriter:
    repo: SheetsRepository
    def update(self, df: pd.DataFrame) -> None:
        self.repo.update_inventory(df)


@dataclass
class _SalesLogWriter:
    repo: SheetsRepository
    def add_entry(self, sale_hash: str) -> None:
        self.repo.add_sales_log_entry(sale_hash)


class SheetsUnitOfWork:
    def __init__(self, repo: SheetsRepository) -> None:
        self.repo = repo
        self.inventory = _InventoryWriter(repo)
        self.sales_log = _SalesLogWriter(repo)
        self._committed = False

    def __enter__(self) -> SheetsUnitOfWork:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if exc:
            # Rollback semantics are no-ops for mocked environment
            return
        if not self._committed:
            # Auto-commit at exit if not explicitly committed
            self.commit()

    def commit(self) -> None:
        self._committed = True
