"""
CSV ingestion service for processing Lightspeed exports.
Handles CSV parsing, validation, and data transformation.
"""
import hashlib
import re
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd


class CSVIngestService:
    """Service for processing CSV files from Lightspeed or manual uploads."""

    def __init__(self):
        """Initialize CSV ingestion service."""
        self.required_product_columns = [
            'ItemID', 'SKU', 'Name', 'Category', 'RetailPrice'
        ]
        self.required_sales_columns = [
            'Date', 'SKU', 'Quantity', 'UnitPrice'
        ]

    def validate_csv_structure(self, df: pd.DataFrame, csv_type: str) -> dict[str, Any]:
        """Validate CSV structure and required columns."""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'row_count': len(df)
        }

        # First, handle empty DataFrame explicitly to match expected error order
        if df.empty:
            validation_result['valid'] = False
            validation_result['errors'].append("CSV file is empty")

        if csv_type == 'products':
            required_cols = self.required_product_columns
        elif csv_type == 'sales':
            required_cols = self.required_sales_columns
        else:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Unknown CSV type: {csv_type}")
            return validation_result

        # Check for required columns
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Missing required columns: {missing_cols}")

        # Note: empty CSV already handled above to keep error ordering consistent

        # Check for duplicate SKUs in products
        if csv_type == 'products' and 'SKU' in df.columns:
            duplicates = df[df['SKU'].duplicated()]
            if not duplicates.empty:
                validation_result['warnings'].append(
                    f"Found {len(duplicates)} duplicate SKUs: {duplicates['SKU'].tolist()[:5]}"
                )

        return validation_result

    def clean_product_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize product data from CSV."""
        df_clean = df.copy()

        # Standardize column names
        column_mapping = {
            'Item ID': 'ItemID',
            'item_id': 'ItemID',
            'Product Name': 'Name',
            'product_name': 'Name',
            'Retail Price': 'RetailPrice',
            'retail_price': 'RetailPrice',
            'Price': 'RetailPrice',
            'Qty On Hand': 'QtyOnHand',
            'qty_on_hand': 'QtyOnHand',
            'Quantity': 'QtyOnHand',
            'Qty Sold': 'QtySold',
            'qty_sold': 'QtySold'
        }

        df_clean = df_clean.rename(columns=column_mapping)

        # Clean SKU field
        if 'SKU' in df_clean.columns:
            df_clean['SKU'] = df_clean['SKU'].astype(str).str.strip().str.upper()

        # Clean Name field
        if 'Name' in df_clean.columns:
            df_clean['Name'] = df_clean['Name'].astype(str).str.strip()

        # Clean Category field
        if 'Category' in df_clean.columns:
            df_clean['Category'] = df_clean['Category'].astype(str).str.strip().str.title()

        # Clean numeric fields
        numeric_fields = ['RetailPrice', 'QtyOnHand', 'QtySold']
        for field in numeric_fields:
            if field in df_clean.columns:
                # Remove currency symbols and convert to numeric
                df_clean[field] = df_clean[field].astype(str).str.replace(r'[$,]', '', regex=True)
                df_clean[field] = pd.to_numeric(df_clean[field], errors='coerce').fillna(0)

        # Add missing columns with defaults
        default_columns = {
            'Color': 'Unknown',
            'Size': 'OS',  # One Size
            'Barcode': '',
            'QtyOnHand': 0,
            'QtySold': 0,
            'Location': 'A1',
            'LastUpdated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        for col, default_val in default_columns.items():
            if col not in df_clean.columns:
                df_clean[col] = default_val

        # Extract size and color from SKU or Name if available
        df_clean = self._extract_variant_info(df_clean)

        return df_clean

    def clean_sales_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and standardize sales data from CSV."""
        df_clean = df.copy()

        # Standardize column names
        column_mapping = {
            'Sale Date': 'Date',
            'sale_date': 'Date',
            'Transaction Date': 'Date',
            'Unit Price': 'UnitPrice',
            'unit_price': 'UnitPrice',
            'Price': 'UnitPrice',
            'Qty': 'Quantity',
            'qty': 'Quantity'
        }

        df_clean = df_clean.rename(columns=column_mapping)

        # Clean date field
        if 'Date' in df_clean.columns:
            df_clean['Date'] = pd.to_datetime(df_clean['Date'], errors='coerce')
            df_clean = df_clean.dropna(subset=['Date'])
            df_clean['Date'] = df_clean['Date'].dt.strftime('%Y-%m-%d')

        # Clean SKU field
        if 'SKU' in df_clean.columns:
            df_clean['SKU'] = df_clean['SKU'].astype(str).str.strip().str.upper()

        # Clean numeric fields
        numeric_fields = ['Quantity', 'UnitPrice']
        for field in numeric_fields:
            if field in df_clean.columns:
                df_clean[field] = df_clean[field].astype(str).str.replace(r'[$,]', '', regex=True)
                df_clean[field] = pd.to_numeric(df_clean[field], errors='coerce').fillna(0)

        # Calculate total if not present
        if 'Total' not in df_clean.columns:
            df_clean['Total'] = df_clean['Quantity'] * df_clean['UnitPrice']

        # Add sale hash for deduplication
        df_clean['SaleHash'] = df_clean.apply(self._generate_sale_hash, axis=1)

        return df_clean

    def _extract_variant_info(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract size and color information from SKU or Name."""
        df_with_variants = df.copy()

        # Size patterns (common shoe sizes and clothing sizes)

        # Color patterns
        color_patterns = [
            r"(BLACK|WHITE|RED|BLUE|GREEN|YELLOW|ORANGE|PURPLE|PINK|BROWN|GRAY|GREY)",
            r"(BLK|WHT|RED|BLU|GRN|YEL|ORG|PUR|PNK|BRN|GRY)",
        ]

        for idx, row in df_with_variants.iterrows():
            sku = str(row.get("SKU", ""))
            name = str(row.get("Name", ""))
            search_text = f"{sku} {name}".upper()
            # Resolve row integer position for iat operations (type-checker friendly)
            row_loc = df_with_variants.index.get_loc(idx)
            # Guard against non-scalar locations (e.g., duplicate indices)
            if isinstance(row_loc, (np.ndarray, slice)):
                # Skip ambiguous index rows for safety
                continue
            row_pos = int(row_loc)

            # Extract size if missing/unknown (prefer parsing from SKU only)
            size_col_raw = (
                df_with_variants.columns.get_loc("Size") if "Size" in df_with_variants.columns else None
            )
            size_col_pos: int | None = size_col_raw if isinstance(size_col_raw, int) else None
            current_size = (
                str(df_with_variants.iat[row_pos, size_col_pos]) if size_col_pos is not None else ""
            )
            if current_size in ["OS", "Unknown", "", "nan"]:
                sku_text = sku.upper()
                # Prefer numeric sizes (with decimals) at the end of the SKU token stream
                numeric_matches = re.findall(r"(\d+(?:\.\d+)?)", sku_text)
                if numeric_matches:
                    if size_col_pos is not None:
                        df_with_variants.iat[row_pos, size_col_pos] = str(numeric_matches[-1])
                else:
                    # Fallback to clothing sizes if present
                    clothing_match = re.search(r"(XS|S|M|L|XL|XXL|XXXL)", sku_text)
                    if clothing_match and size_col_pos is not None:
                        df_with_variants.iat[row_pos, size_col_pos] = clothing_match.group(1)

            # Extract color if missing/unknown
            color_col_raw = (
                df_with_variants.columns.get_loc("Color") if "Color" in df_with_variants.columns else None
            )
            color_col_pos: int | None = color_col_raw if isinstance(color_col_raw, int) else None
            current_color = (
                str(df_with_variants.iat[row_pos, color_col_pos]) if color_col_pos is not None else ""
            )
            if current_color in ["Unknown", "", "nan"]:
                found_match = None
                for pattern in color_patterns:
                    m = re.search(pattern, search_text)
                    if m:
                        found_match = m
                        break
                if found_match:
                    color = found_match.group(1)
                    # Convert abbreviations to full names
                    color_map = {
                        "BLK": "Black",
                        "WHT": "White",
                        "BLU": "Blue",
                        "GRN": "Green",
                        "GRY": "Gray",
                        "GREY": "Gray",
                    }
                    if color_col_pos is not None:
                        df_with_variants.iat[row_pos, color_col_pos] = color_map.get(color, color.title())

        return df_with_variants

    def _generate_sale_hash(self, row: pd.Series) -> str:
        """Generate unique hash for sale record to prevent duplicates."""
        hash_data = f"{row.get('Date', '')}{row.get('SKU', '')}{row.get('Quantity', 0)}{row.get('UnitPrice', 0)}"
        return hashlib.md5(hash_data.encode()).hexdigest()

    def process_products_csv(self, file_path: str) -> dict[str, Any]:
        """Process products CSV file and return cleaned data."""
        try:
            # Read CSV file
            df = pd.read_csv(file_path)

            # Validate structure
            validation = self.validate_csv_structure(df, 'products')
            if not validation['valid']:
                return {
                    'success': False,
                    'errors': validation['errors'],
                    'warnings': validation.get('warnings', [])
                }

            # Clean data
            df_clean = self.clean_product_data(df)

            return {
                'success': True,
                'data': df_clean,
                'row_count': len(df_clean),
                'warnings': validation.get('warnings', [])
            }

        except Exception as e:
            return {
                'success': False,
                'errors': [f"Failed to process products CSV: {str(e)}"]
            }

    def process_sales_csv(self, file_path: str) -> dict[str, Any]:
        """Process sales CSV file and return cleaned data."""
        try:
            # Read CSV file
            df = pd.read_csv(file_path)

            # Validate structure
            validation = self.validate_csv_structure(df, 'sales')
            if not validation['valid']:
                return {
                    'success': False,
                    'errors': validation['errors'],
                    'warnings': validation.get('warnings', [])
                }

            # Clean data
            df_clean = self.clean_sales_data(df)

            return {
                'success': True,
                'data': df_clean,
                'row_count': len(df_clean),
                'warnings': validation.get('warnings', [])
            }

        except Exception as e:
            return {
                'success': False,
                'errors': [f"Failed to process sales CSV: {str(e)}"]
            }

    def detect_csv_type(self, df: pd.DataFrame) -> str:
        """Auto-detect CSV type based on column structure."""
        columns = set(df.columns)

        # Check for product indicators
        product_indicators = {'SKU', 'Name', 'Category', 'RetailPrice', 'ItemID'}
        if len(columns.intersection(product_indicators)) >= 3:
            return 'products'

        # Check for sales indicators
        sales_indicators = {'Date', 'SKU', 'Quantity', 'UnitPrice'}
        if len(columns.intersection(sales_indicators)) >= 3:
            return 'sales'

        return 'unknown'
