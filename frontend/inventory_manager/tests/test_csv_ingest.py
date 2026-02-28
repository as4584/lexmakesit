"""
Tests for CSV ingestion and data processing.
"""
import os
import tempfile

import pandas as pd

from services.csv_ingest import CSVIngestService


class TestCSVIngestService:
    """Test cases for CSV ingestion service."""

    def test_validate_products_csv_structure_valid(self):
        """Test validation of valid products CSV structure."""
        service = CSVIngestService()

        valid_df = pd.DataFrame({
            'ItemID': ['1001', '1002'],
            'SKU': ['TEST-001', 'TEST-002'],
            'Name': ['Test Product 1', 'Test Product 2'],
            'Category': ['Sneakers', 'Clothing'],
            'RetailPrice': [100.0, 200.0]
        })

        result = service.validate_csv_structure(valid_df, 'products')

        assert result['valid'] is True
        assert len(result['errors']) == 0
        assert result['row_count'] == 2

    def test_validate_products_csv_structure_missing_columns(self):
        """Test validation with missing required columns."""
        service = CSVIngestService()

        invalid_df = pd.DataFrame({
            'SKU': ['TEST-001'],
            'Name': ['Test Product']
            # Missing ItemID, Category, RetailPrice
        })

        result = service.validate_csv_structure(invalid_df, 'products')

        assert result['valid'] is False
        assert len(result['errors']) > 0
        assert 'Missing required columns' in result['errors'][0]

    def test_validate_sales_csv_structure_valid(self):
        """Test validation of valid sales CSV structure."""
        service = CSVIngestService()

        valid_df = pd.DataFrame({
            'Date': ['2025-10-09', '2025-10-08'],
            'SKU': ['TEST-001', 'TEST-002'],
            'Quantity': [1, 2],
            'UnitPrice': [100.0, 50.0]
        })

        result = service.validate_csv_structure(valid_df, 'sales')

        assert result['valid'] is True
        assert len(result['errors']) == 0

    def test_validate_empty_csv(self):
        """Test validation of empty CSV."""
        service = CSVIngestService()

        empty_df = pd.DataFrame()

        result = service.validate_csv_structure(empty_df, 'products')

        assert result['valid'] is False
        assert 'CSV file is empty' in result['errors'][0]

    def test_clean_product_data(self):
        """Test product data cleaning and standardization."""
        service = CSVIngestService()

        raw_df = pd.DataFrame({
            'Item ID': ['1001', '1002'],  # Different column name
            'SKU': [' test-001 ', 'TEST-002'],  # Whitespace and case
            'Product Name': ['Test Product 1', 'Test Product 2'],  # Different column name
            'Retail Price': ['$100.00', '200'],  # Currency symbol
            'Category': [' sneakers', 'CLOTHING '],  # Case and whitespace
        })

        cleaned_df = service.clean_product_data(raw_df)

        # Check column standardization
        assert 'ItemID' in cleaned_df.columns
        assert 'Name' in cleaned_df.columns
        assert 'RetailPrice' in cleaned_df.columns

        # Check data cleaning
        assert cleaned_df['SKU'].iloc[0] == 'TEST-001'
        assert cleaned_df['RetailPrice'].iloc[0] == 100.0
        assert cleaned_df['Category'].iloc[0] == 'Sneakers'

        # Check default columns added
        assert 'Color' in cleaned_df.columns
        assert 'Size' in cleaned_df.columns
        assert 'LastUpdated' in cleaned_df.columns

    def test_clean_sales_data(self):
        """Test sales data cleaning and standardization."""
        service = CSVIngestService()

        raw_df = pd.DataFrame({
            'Sale Date': ['2025-10-09', '10/08/2025'],
            'SKU': [' test-001 ', 'TEST-002'],
            'Qty': ['1', '2'],
            'Unit Price': ['$100.00', '50.50']
        })

        cleaned_df = service.clean_sales_data(raw_df)

        # Check column standardization
        assert 'Date' in cleaned_df.columns
        assert 'Quantity' in cleaned_df.columns
        assert 'UnitPrice' in cleaned_df.columns

        # Check data cleaning
        assert cleaned_df['SKU'].iloc[0] == 'TEST-001'
        assert cleaned_df['Quantity'].iloc[0] == 1.0
        assert cleaned_df['UnitPrice'].iloc[0] == 100.0

        # Check calculated fields
        assert 'Total' in cleaned_df.columns
        assert 'SaleHash' in cleaned_df.columns

    def test_extract_variant_info_from_sku(self):
        """Test extraction of size and color from SKU."""
        service = CSVIngestService()

        df = pd.DataFrame({
            'SKU': ['JD1-BLK-10', 'HOODIE-RED-L', 'SHOE-WHT-9.5'],
            'Name': ['Jordan 1', 'Red Hoodie', 'White Shoe'],
            'Size': ['', '', ''],
            'Color': ['', '', '']
        })

        result_df = service._extract_variant_info(df)

        # Check size extraction
        assert result_df.iloc[0]['Size'] == '10'
        assert result_df.iloc[1]['Size'] == 'L'
        assert result_df.iloc[2]['Size'] == '9.5'

        # Check color extraction
        assert result_df.iloc[0]['Color'] == 'Black'
        assert result_df.iloc[1]['Color'] == 'Red'
        assert result_df.iloc[2]['Color'] == 'White'

    def test_generate_sale_hash(self):
        """Test sale hash generation for deduplication."""
        service = CSVIngestService()

        sale_row1 = pd.Series({
            'Date': '2025-10-09',
            'SKU': 'TEST-001',
            'Quantity': 1,
            'UnitPrice': 100.0
        })

        sale_row2 = pd.Series({
            'Date': '2025-10-09',
            'SKU': 'TEST-001',
            'Quantity': 1,
            'UnitPrice': 100.0
        })

        sale_row3 = pd.Series({
            'Date': '2025-10-09',
            'SKU': 'TEST-001',
            'Quantity': 2,  # Different quantity
            'UnitPrice': 100.0
        })

        hash1 = service._generate_sale_hash(sale_row1)
        hash2 = service._generate_sale_hash(sale_row2)
        hash3 = service._generate_sale_hash(sale_row3)

        # Same data should generate same hash
        assert hash1 == hash2

        # Different data should generate different hash
        assert hash1 != hash3

        # Hash should be consistent format
        assert len(hash1) == 32  # MD5 hash length

    def test_process_products_csv_file(self):
        """Test processing a products CSV file."""
        service = CSVIngestService()

        # Create temporary CSV file
        csv_content = """ItemID,SKU,Name,Category,RetailPrice
1001,TEST-001,Test Product 1,Sneakers,100.00
1002,TEST-002,Test Product 2,Clothing,200.00"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_file = f.name

        try:
            result = service.process_products_csv(temp_file)

            assert result['success'] is True
            assert result['row_count'] == 2
            assert isinstance(result['data'], pd.DataFrame)
            assert len(result['data']) == 2

        finally:
            os.unlink(temp_file)

    def test_process_sales_csv_file(self):
        """Test processing a sales CSV file."""
        service = CSVIngestService()

        # Create temporary CSV file
        csv_content = """Date,SKU,Quantity,UnitPrice
2025-10-09,TEST-001,1,100.00
2025-10-08,TEST-002,2,50.00"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_file = f.name

        try:
            result = service.process_sales_csv(temp_file)

            assert result['success'] is True
            assert result['row_count'] == 2
            assert isinstance(result['data'], pd.DataFrame)
            assert 'SaleHash' in result['data'].columns

        finally:
            os.unlink(temp_file)

    def test_process_invalid_csv_file(self):
        """Test processing an invalid CSV file."""
        service = CSVIngestService()

        # Create temporary CSV file with missing columns
        csv_content = """SKU,Name
TEST-001,Test Product 1"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_file = f.name

        try:
            result = service.process_products_csv(temp_file)

            assert result['success'] is False
            assert len(result['errors']) > 0

        finally:
            os.unlink(temp_file)

    def test_detect_csv_type(self):
        """Test automatic CSV type detection."""
        service = CSVIngestService()

        # Products CSV
        products_df = pd.DataFrame({
            'SKU': ['TEST-001'],
            'Name': ['Test Product'],
            'Category': ['Sneakers'],
            'RetailPrice': [100.0]
        })

        # Sales CSV
        sales_df = pd.DataFrame({
            'Date': ['2025-10-09'],
            'SKU': ['TEST-001'],
            'Quantity': [1],
            'UnitPrice': [100.0]
        })

        # Unknown CSV
        unknown_df = pd.DataFrame({
            'RandomColumn': ['value']
        })

        assert service.detect_csv_type(products_df) == 'products'
        assert service.detect_csv_type(sales_df) == 'sales'
        assert service.detect_csv_type(unknown_df) == 'unknown'

    def test_handle_malformed_csv(self):
        """Test handling of malformed CSV data."""
        service = CSVIngestService()

        # Test with non-existent file
        result = service.process_products_csv('non_existent_file.csv')

        assert result['success'] is False
        assert len(result['errors']) > 0

    def test_duplicate_sku_warning(self):
        """Test that duplicate SKUs generate warnings."""
        service = CSVIngestService()

        df_with_duplicates = pd.DataFrame({
            'ItemID': ['1001', '1002'],
            'SKU': ['DUPLICATE', 'DUPLICATE'],  # Duplicate SKUs
            'Name': ['Product 1', 'Product 2'],
            'Category': ['Sneakers', 'Clothing'],
            'RetailPrice': [100.0, 200.0]
        })

        result = service.validate_csv_structure(df_with_duplicates, 'products')

        assert result['valid'] is True  # Still valid but should have warnings
        assert len(result['warnings']) > 0
        assert 'duplicate SKUs' in result['warnings'][0]
