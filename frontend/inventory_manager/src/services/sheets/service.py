"""
Google Sheets service for inventory management.
Handles all interactions with Google Sheets as the source of truth.
"""
import os
from datetime import datetime
from typing import Any

import pandas as pd

import services.sheets as sheets_pkg


class SheetsService:
    """Service for Google Sheets operations."""

    def __init__(self):
        """Initialize Google Sheets client."""
        self.service_account_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
        self.sheet_name = os.getenv('GOOGLE_SHEET_NAME', 'Live ATS Inventory')
        self.client = None
        self.workbook = None
        self._connect()

    def _connect(self) -> None:
        """Connect to Google Sheets API."""
        try:
            if not self.service_account_path or not os.path.exists(self.service_account_path):
                raise ValueError(f"Service account file not found: {self.service_account_path}")

            # Set up credentials with required scopes
            scopes = [
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]

            credentials = sheets_pkg.Credentials.from_service_account_file(
                self.service_account_path,
                scopes=scopes
            )

            self.client = sheets_pkg.gspread.authorize(credentials)
            self.workbook = self.client.open(self.sheet_name)

        except Exception as e:
            print(f"Failed to connect to Google Sheets: {e}")
            # For development, continue without connection
            self.client = None
            self.workbook = None

    def get_or_create_worksheet(self, worksheet_name: str, headers: list[str]) -> Any | None:
        """Get existing worksheet or create new one with headers."""
        if not self.workbook:
            return None

        try:
            worksheet = self.workbook.worksheet(worksheet_name)
        except sheets_pkg.gspread.WorksheetNotFound:
            # Create new worksheet
            worksheet = self.workbook.add_worksheet(
                title=worksheet_name,
                rows=1000,
                cols=len(headers)
            )
            # Add headers
            worksheet.insert_row(headers, 1)

        return worksheet

    def get_inventory_data(self) -> pd.DataFrame:
        """Get all inventory data from the Inventory worksheet."""
        headers = [
            'ItemID', 'SKU', 'Name', 'Category', 'Color', 'Size',
            'Barcode', 'RetailPrice', 'QtyOnHand', 'QtySold',
            'Location', 'LastUpdated'
        ]

        worksheet = self.get_or_create_worksheet('Inventory', headers)

        if not worksheet:
            # Return mock data for development
            return pd.DataFrame([
                {
                    'ItemID': '1001',
                    'SKU': 'JD1-BLK-10',
                    'Name': 'Air Jordan 1 Black',
                    'Category': 'Sneakers',
                    'Color': 'Black',
                    'Size': '10',
                    'Barcode': '123456789',
                    'RetailPrice': 170.00,
                    'QtyOnHand': 8,
                    'QtySold': 2,
                    'Location': 'A1',
                    'LastUpdated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            ])

        try:
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
        except Exception as e:
            print(f"Error reading inventory data: {e}")
            return pd.DataFrame(columns=headers)

    def update_inventory_data(self, df: pd.DataFrame) -> bool:
        """Update the Inventory worksheet with new data."""
        headers = [
            'ItemID', 'SKU', 'Name', 'Category', 'Color', 'Size',
            'Barcode', 'RetailPrice', 'QtyOnHand', 'QtySold',
            'Location', 'LastUpdated'
        ]

        worksheet = self.get_or_create_worksheet('Inventory', headers)

        if not worksheet:
            print("Cannot update inventory - no worksheet connection")
            return False

        try:
            # Clear existing data (except headers)
            worksheet.clear()
            worksheet.insert_row(headers, 1)

            # Convert DataFrame to list of lists
            data_rows = df.values.tolist()

            # Insert all data at once for better performance
            if data_rows:
                worksheet.insert_rows(data_rows, 2)

            return True
        except Exception as e:
            print(f"Error updating inventory data: {e}")
            return False

    def get_config(self) -> dict[str, Any]:
        """Get configuration values from Config worksheet."""
        headers = ['Setting', 'Value', 'Description']
        worksheet = self.get_or_create_worksheet('Config', headers)

        if not worksheet:
            # Return default config
            return {'LowStockThreshold': 5}

        try:
            data = worksheet.get_all_records()
            config = {}
            for row in data:
                if row['Setting'] and row['Value']:
                    config[row['Setting']] = row['Value']

            # Ensure default values
            if 'LowStockThreshold' not in config:
                config['LowStockThreshold'] = 5

            return config
        except Exception as e:
            print(f"Error reading config: {e}")
            return {'LowStockThreshold': 5}

    def update_config(self, config: dict[str, Any]) -> bool:
        """Update configuration values in Config worksheet."""
        headers = ['Setting', 'Value', 'Description']
        worksheet = self.get_or_create_worksheet('Config', headers)

        if not worksheet:
            return False

        try:
            # Clear and rebuild config
            worksheet.clear()
            worksheet.insert_row(headers, 1)

            default_configs = [
                ['LowStockThreshold', config.get('LowStockThreshold', 5), 'Minimum quantity before item appears in restock list']
            ]

            for setting, value, description in default_configs:
                worksheet.insert_row([setting, value, description])

            return True
        except Exception as e:
            print(f"Error updating config: {e}")
            return False

    def get_sales_log(self) -> pd.DataFrame:
        """Get sales log for deduplication."""
        headers = ['SaleHash', 'ProcessedAt', 'SaleDate', 'Amount']
        worksheet = self.get_or_create_worksheet('SalesLog', headers)

        if not worksheet:
            return pd.DataFrame(columns=headers)

        try:
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
        except Exception as e:
            print(f"Error reading sales log: {e}")
            return pd.DataFrame(columns=headers)

    def add_sales_log_entry(self, sale_hash: str, sale_date: str, amount: float) -> bool:
        """Add entry to sales log for deduplication."""
        headers = ['SaleHash', 'ProcessedAt', 'SaleDate', 'Amount']
        worksheet = self.get_or_create_worksheet('SalesLog', headers)

        if not worksheet:
            return False

        try:
            worksheet.insert_row([
                sale_hash,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                sale_date,
                amount
            ])
            return True
        except Exception as e:
            print(f"Error adding sales log entry: {e}")
            return False

    def update_restock_list(self, low_stock_df: pd.DataFrame) -> bool:
        """Update the RestockList worksheet with low stock items."""
        headers = ['SKU', 'Name', 'Category', 'QtyOnHand', 'Threshold', 'Location', 'UpdatedAt']
        worksheet = self.get_or_create_worksheet('RestockList', headers)

        if not worksheet:
            return False

        try:
            # Clear existing data
            worksheet.clear()
            worksheet.insert_row(headers, 1)

            # Add current timestamp
            restock_data = low_stock_df.copy()
            restock_data['UpdatedAt'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Convert to list of lists and insert
            data_rows = restock_data.values.tolist()
            if data_rows:
                worksheet.insert_rows(data_rows, 2)

            return True
        except Exception as e:
            print(f"Error updating restock list: {e}")
            return False

    def backup_to_csv(self, df: pd.DataFrame, filename: str) -> bool:
        """Export DataFrame to CSV backup."""
        try:
            backup_path = f"backups/{filename}"
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            df.to_csv(backup_path, index=False)
            print(f"Backup created: {backup_path}")
            return True
        except Exception as e:
            print(f"Error creating backup: {e}")
            return False
