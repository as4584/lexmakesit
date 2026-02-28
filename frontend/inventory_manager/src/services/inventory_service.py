"""
Compatibility Inventory Service exposing API expected by tests.
Delegates or implements operations using the domain inventory logic.
"""
from __future__ import annotations

import hashlib
from dataclasses import replace

import pandas as pd

from src.domain.exceptions import InvalidInventorySchemaError, NegativeInventoryError
from src.domain.inventory import InventoryService as DomainInventoryService
from src.domain.models import Product, Sale


def generate_sale_hash(sale: dict) -> str:
    """Generate a stable hash for a sale dict for deduplication."""
    # Normalize fields that define a sale identity
    sku = str(sale.get("SKU", "")).strip().upper()
    qty = int(sale.get("Quantity", 0))
    date = str(sale.get("Date", "")).strip()
    price = str(sale.get("UnitPrice", "")).strip()
    payload = f"{sku}|{qty}|{date}|{price}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class InventoryService:
    def __init__(self) -> None:
        self._domain = DomainInventoryService()

    # ----- Single item operations -----
    def apply_sale(self, product: Product, sale: Sale) -> Product:
        """Apply a sale to a single product and return updated product."""
        new_on_hand = product.qty_on_hand - sale.quantity
        if new_on_hand < 0:
            new_on_hand = 0
        return replace(product, qty_on_hand=new_on_hand, qty_sold=product.qty_sold + sale.quantity)

    # ----- Batch operations over DataFrames -----
    def apply_sales_batch(
        self,
        inventory_df: pd.DataFrame,
        sales_df: pd.DataFrame,
        *,
        allow_negative: bool = True,
    ) -> pd.DataFrame:
        """Apply sales to an inventory DataFrame with optional negative prevention and dedup via SaleHash."""
        if inventory_df.empty or sales_df.empty:
            return inventory_df.copy()

        df_inv = inventory_df.copy()
        df_sales = sales_df.copy()

        # Deduplicate by SaleHash if present
        applied_hashes: set[str] = set()

        for _, row in df_sales.iterrows():
            sku = row.get("SKU")
            qty = int(row.get("Quantity", 0) or 0)
            if not sku or qty <= 0:
                continue

            sale_hash = row.get("SaleHash")
            if sale_hash:
                if sale_hash in applied_hashes:
                    continue
                applied_hashes.add(sale_hash)

            mask = df_inv["SKU"] == sku
            if not mask.any():
                continue

            current_on_hand = int(pd.to_numeric(df_inv.loc[mask, "QtyOnHand"].iloc[0], errors="coerce") or 0)
            new_on_hand = current_on_hand - qty
            if not allow_negative and new_on_hand < 0:
                raise NegativeInventoryError(f"Sale would make inventory negative for SKU {sku}")
            new_on_hand = max(0, new_on_hand)
            df_inv.loc[mask, "QtyOnHand"] = new_on_hand

            if "QtySold" in df_inv.columns:
                current_sold = int(pd.to_numeric(df_inv.loc[mask, "QtySold"].iloc[0], errors="coerce") or 0)
                df_inv.loc[mask, "QtySold"] = current_sold + qty

        return df_inv

    def sync_with_deduplication(self, inventory_df: pd.DataFrame, sales_df: pd.DataFrame) -> pd.DataFrame:
        """Idempotent apply: ignore duplicate SaleHash within provided sales and across repeated runs.

        We compute a stable hash of the provided sale hashes and skip applying if the
        inventory already indicates the same batch was processed.
        """
        df_inv = inventory_df.copy()
        # Build a sync batch hash
        sale_hashes = [str(h) for h in sales_df.get("SaleHash", []) if pd.notna(h)]
        batch_id = hashlib.sha256("|".join(sorted(set(sale_hashes))).encode("utf-8")).hexdigest() if sale_hashes else ""

        # If we've already applied this batch, return unchanged
        if "LastSyncHash" in df_inv.columns:
            existing = str(df_inv["LastSyncHash"].iloc[0]) if not df_inv.empty else ""
            if existing == batch_id:
                return df_inv

        updated = self.apply_sales_batch(df_inv, sales_df, allow_negative=True)
        # Record the batch on all rows so subsequent calls with same batch are idempotent
        if not updated.empty:
            updated["LastSyncHash"] = batch_id
        return updated

    # ----- Low stock helpers -----
    def detect_low_stock(self, inventory_df: pd.DataFrame, threshold: int = 5) -> pd.DataFrame:
        if inventory_df.empty:
            return inventory_df.copy()
        qty = (
            pd.to_numeric(inventory_df["QtyOnHand"], errors="coerce").fillna(0)
            if "QtyOnHand" in inventory_df.columns
            else pd.Series([0] * len(inventory_df))
        )
        return inventory_df[qty <= threshold].copy()

    def detect_low_stock_with_priority(self, inventory_df: pd.DataFrame, threshold: int = 5) -> pd.DataFrame:
        low = self.detect_low_stock(inventory_df, threshold)
        if low.empty:
            low["Priority"] = []  # create column
            return low
        qty = (
            pd.to_numeric(low["QtyOnHand"], errors="coerce").fillna(0)
            if "QtyOnHand" in low.columns
            else pd.Series([0] * len(low))
        )
        def to_priority(v: int) -> str:
            if v == 0:
                return "Critical"
            if v <= 1:
                return "High"
            if v <= max(1, threshold // 2 + (threshold % 2 > 0)):
                return "Medium"
            return "Low"
        low = low.copy()
        low["Priority"] = qty.astype(int).apply(to_priority)
        return low

    def generate_restock_recommendations(self, inventory_df: pd.DataFrame) -> pd.DataFrame:
        if inventory_df.empty:
            return pd.DataFrame(columns=["SKU", "RecommendedQty", "Reason"])
        df = inventory_df.copy()
        qty_sold = (
            pd.to_numeric(df["QtySold"], errors="coerce").fillna(0)
            if "QtySold" in df.columns
            else pd.Series([0] * len(df))
        )
        # Simple heuristic: 20% of past sold + baseline of 5
        recommended = (qty_sold * 0.2).round().astype(int).clip(lower=1) + 5
        out = pd.DataFrame({
            "SKU": df.get("SKU", []),
            "RecommendedQty": recommended.values,
            "Reason": ["Sales velocity and baseline"] * len(df)
        })
        return out

    # ----- Validation -----
    def validate_inventory_schema(self, df: pd.DataFrame) -> None:
        required = {"SKU", "QtyOnHand"}
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise InvalidInventorySchemaError(f"Missing required columns: {missing}")

    def validate_prices(self, df: pd.DataFrame) -> dict[str, pd.DataFrame]:
        prices = (
            pd.to_numeric(df["RetailPrice"], errors="coerce").fillna(0)
            if "RetailPrice" in df.columns
            else pd.Series([0] * len(df))
        )
        invalid_mask = prices <= 0
        return {"invalid_prices": df[invalid_mask].copy()}

    # ----- Sorting -----
    def auto_sort(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._domain.auto_sort(df)
