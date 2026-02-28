"""
Inventory business logic service.
Handles sorting, low stock detection, and reconciliation operations.
"""
from datetime import datetime
from typing import Any

import pandas as pd


class InventoryService:
    """Service for inventory business logic operations."""

    def __init__(self, sheets_service=None):
        """Initialize inventory service."""
        self.sheets_service = sheets_service

    def auto_sort(self, df: pd.DataFrame) -> pd.DataFrame:
        """Sort inventory data by Category → Name → Size for consistent formatting."""
        if df.empty:
            return df

        sort_columns = []

        # Add Category to sort if available
        if 'Category' in df.columns:
            sort_columns.append('Category')

        # Add Name to sort if available
        if 'Name' in df.columns:
            sort_columns.append('Name')

        # Add Size to sort if available (with custom sorting for shoe sizes)
        if 'Size' in df.columns:
            df_sorted = df.copy()
            # Convert sizes to sortable format
            df_sorted['SizeSort'] = df_sorted['Size'].apply(self._size_sort_key)
            sort_columns.append('SizeSort')

            # Sort the DataFrame
            df_sorted = df_sorted.sort_values(sort_columns, na_position='last')

            # Remove the temporary sort column
            df_sorted = df_sorted.drop('SizeSort', axis=1)

            return df_sorted
        else:
            # Sort without size
            return df.sort_values(sort_columns, na_position='last')

    def _size_sort_key(self, size: Any) -> float:
        """Convert size to numeric value for proper sorting."""
        if pd.isna(size):
            return 999.0

        size_str = str(size).strip().upper()

        # Handle numeric sizes (shoe sizes)
        try:
            return float(size_str)
        except ValueError:
            pass

        # Handle clothing sizes
        clothing_size_map = {
            'XS': 1.0, 'S': 2.0, 'M': 3.0, 'L': 4.0,
            'XL': 5.0, 'XXL': 6.0, 'XXXL': 7.0,
            'OS': 0.0  # One Size comes first
        }

        if size_str in clothing_size_map:
            return clothing_size_map[size_str]

        # Handle waist sizes (30, 32, 34, etc.)
        if size_str.isdigit() and len(size_str) == 2:
            return float(size_str)

        # Default: sort alphabetically by converting to ASCII sum
        return sum(ord(c) for c in size_str[:3])

    def low_stock(self, df: pd.DataFrame, threshold: int | None = None) -> pd.DataFrame:
        """Filter items below stock threshold and return low stock DataFrame."""
        if df.empty:
            return df

        # Get threshold from config if not provided
        if threshold is None:
            if self.sheets_service:
                config = self.sheets_service.get_config()
                threshold = int(config.get('LowStockThreshold', 5))
            else:
                threshold = 5

        # Filter items below threshold
        qty_column = 'QtyOnHand'
        if qty_column not in df.columns:
            print(f"Warning: {qty_column} column not found")
            return pd.DataFrame()

        low_stock_df = df[pd.to_numeric(df[qty_column], errors='coerce') <= threshold].copy()

        # Add threshold column for reference
        low_stock_df['Threshold'] = threshold

        # Select relevant columns for restock list
        restock_columns = ['SKU', 'Name', 'Category', 'QtyOnHand', 'Threshold', 'Location']
        available_columns = [col for col in restock_columns if col in low_stock_df.columns]

        return low_stock_df[available_columns] if available_columns else low_stock_df

    def reconcile_sales(self, inventory_df: pd.DataFrame, sales_df: pd.DataFrame,
                       processed_hashes: list[str] | None = None) -> dict[str, Any]:
        """Apply sales data to update on-hand quantities with deduplication."""
        if inventory_df.empty or sales_df.empty:
            return {
                'success': True,
                'processed_sales': 0,
                'items_updated': 0,
                'skipped_duplicates': 0,
                'errors': []
            }

        processed_hashes = processed_hashes or []
        reconcile_result = {
            'success': True,
            'processed_sales': 0,
            'items_updated': 0,
            'skipped_duplicates': 0,
            'errors': [],
            'updated_skus': []
        }

        # Ensure inventory has required columns
        if 'SKU' not in inventory_df.columns or 'QtyOnHand' not in inventory_df.columns:
            reconcile_result['success'] = False
            reconcile_result['errors'].append('Inventory missing required SKU or QtyOnHand columns')
            return reconcile_result

        # Create a copy for updates
        updated_inventory = inventory_df.copy()

        # Process each sale
        for _, sale_row in sales_df.iterrows():
            sale_hash = sale_row.get('SaleHash')
            sku = sale_row.get('SKU')
            quantity_sold = sale_row.get('Quantity', 0)

            # Skip if no hash or already processed
            if not sale_hash or sale_hash in processed_hashes:
                reconcile_result['skipped_duplicates'] += 1
                continue

            # Skip if no valid SKU or quantity
            if not sku or quantity_sold <= 0:
                continue

            # Find matching inventory item
            inventory_mask = updated_inventory['SKU'] == sku
            matching_items = updated_inventory[inventory_mask]

            if matching_items.empty:
                reconcile_result['errors'].append(f'SKU not found in inventory: {sku}')
                continue

            # Update quantity on hand
            try:
                current_qty = pd.to_numeric(matching_items.iloc[0]['QtyOnHand'], errors='coerce')
                if pd.isna(current_qty):
                    current_qty = 0

                new_qty = max(0, current_qty - quantity_sold)  # Don't go below 0

                # Update the inventory DataFrame
                updated_inventory.loc[inventory_mask, 'QtyOnHand'] = new_qty

                # Update QtySold if column exists
                if 'QtySold' in updated_inventory.columns:
                    current_sold = pd.to_numeric(
                        updated_inventory.loc[inventory_mask, 'QtySold'].iloc[0],
                        errors='coerce'
                    )
                    if pd.isna(current_sold):
                        current_sold = 0

                    updated_inventory.loc[inventory_mask, 'QtySold'] = current_sold + quantity_sold

                # Update LastUpdated timestamp
                if 'LastUpdated' in updated_inventory.columns:
                    updated_inventory.loc[inventory_mask, 'LastUpdated'] = \
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                reconcile_result['items_updated'] += 1
                reconcile_result['updated_skus'].append(sku)

            except Exception as e:
                reconcile_result['errors'].append(f'Error updating {sku}: {str(e)}')

            reconcile_result['processed_sales'] += 1

        reconcile_result['updated_inventory'] = updated_inventory

        return reconcile_result

    def generate_restock_suggestions(self, low_stock_df: pd.DataFrame) -> dict[str, Any]:
        """Generate intelligent restock suggestions based on sales velocity."""
        if low_stock_df.empty:
            return {'suggestions': [], 'total_items': 0}

        suggestions = []

        for _, item in low_stock_df.iterrows():
            sku = item.get('SKU', '')
            name = item.get('Name', '')
            qty_on_hand = item.get('QtyOnHand', 0)
            qty_sold = item.get('QtySold', 0)
            threshold = item.get('Threshold', 5)

            # Calculate suggested reorder quantity
            # Simple formula: threshold * 2 + recent sales velocity
            base_reorder = threshold * 2

            # Add sales velocity if we have sales data
            if qty_sold > 0:
                # Assume sales data represents 30-day period
                daily_velocity = qty_sold / 30
                monthly_buffer = daily_velocity * 30
                suggested_qty = int(base_reorder + monthly_buffer)
            else:
                suggested_qty = base_reorder

            # Minimum reorder of 5 units
            suggested_qty = max(5, suggested_qty)

            suggestions.append({
                'sku': sku,
                'name': name,
                'current_qty': qty_on_hand,
                'threshold': threshold,
                'suggested_reorder': suggested_qty,
                'priority': 'High' if qty_on_hand == 0 else 'Medium' if qty_on_hand <= threshold/2 else 'Low'
            })

        # Sort by priority and quantity on hand
        priority_order = {'High': 3, 'Medium': 2, 'Low': 1}
        suggestions.sort(key=lambda x: (priority_order[x['priority']], -x['current_qty']), reverse=True)

        return {
            'suggestions': suggestions,
            'total_items': len(suggestions),
            'high_priority': len([s for s in suggestions if s['priority'] == 'High']),
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def calculate_inventory_metrics(self, df: pd.DataFrame) -> dict[str, Any]:
        """Calculate key inventory metrics and KPIs."""
        if df.empty:
            return {
                'total_skus': 0,
                'total_on_hand': 0,
                'total_sold': 0,
                'total_value': 0,
                'low_stock_count': 0,
                'out_of_stock_count': 0,
                'categories': {}
            }

        # Basic metrics
        total_skus = len(df)
        total_on_hand = pd.to_numeric(df.get('QtyOnHand', 0), errors='coerce').sum()
        total_sold = pd.to_numeric(df.get('QtySold', 0), errors='coerce').sum()

        # Calculate total inventory value
        retail_prices = pd.to_numeric(df.get('RetailPrice', 0), errors='coerce').fillna(0)
        quantities = pd.to_numeric(df.get('QtyOnHand', 0), errors='coerce').fillna(0)
        total_value = (retail_prices * quantities).sum()

        # Count stock levels
        qty_on_hand = pd.to_numeric(df.get('QtyOnHand', 0), errors='coerce').fillna(0)
        out_of_stock_count = (qty_on_hand == 0).sum()

        # Low stock count (using default threshold of 5)
        threshold = 5
        if self.sheets_service:
            config = self.sheets_service.get_config()
            threshold = int(config.get('LowStockThreshold', 5))

        low_stock_count = (qty_on_hand <= threshold).sum()

        # Category breakdown
        categories = {}
        if 'Category' in df.columns:
            category_stats = df.groupby('Category').agg({
                'QtyOnHand': lambda x: pd.to_numeric(x, errors='coerce').sum(),
                'SKU': 'count',
                'RetailPrice': lambda x: (pd.to_numeric(x, errors='coerce').fillna(0) *
                                        pd.to_numeric(df.loc[x.index, 'QtyOnHand'], errors='coerce').fillna(0)).sum()
            }).to_dict('index')

            for category, stats in category_stats.items():
                categories[category] = {
                    'sku_count': stats['SKU'],
                    'total_on_hand': stats['QtyOnHand'],
                    'total_value': stats['RetailPrice']
                }

        return {
            'total_skus': int(total_skus),
            'total_on_hand': int(total_on_hand),
            'total_sold': int(total_sold),
            'total_value': float(total_value),
            'low_stock_count': int(low_stock_count),
            'out_of_stock_count': int(out_of_stock_count),
            'categories': categories,
            'calculated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
