"""
Tests for Google Sheets service integration.
"""
from unittest.mock import Mock, patch

import pandas as pd
import pytest

from services.sheets import SheetsService


class TestSheetsService:
    """Test cases for Google Sheets service."""

    @patch('services.sheets.gspread')
    @patch('services.sheets.Credentials')
    def test_connect_with_valid_credentials(self, mock_credentials, mock_gspread):
        """Test connection with valid service account credentials."""
        # Mock the credentials and gspread client
        mock_creds = Mock()
        mock_credentials.from_service_account_file.return_value = mock_creds

        mock_client = Mock()
        mock_workbook = Mock()
        mock_gspread.authorize.return_value = mock_client
        mock_client.open.return_value = mock_workbook

        with patch.dict('os.environ', {
            'GOOGLE_SERVICE_ACCOUNT_JSON': '/path/to/service_account.json',
            'GOOGLE_SHEET_NAME': 'Test Sheet'
        }), patch('os.path.exists', return_value=True):
            service = SheetsService()

            assert service.client is not None
            assert service.workbook is not None

    @patch('services.sheets.gspread')
    def test_connect_without_credentials(self, mock_gspread):
        """Test connection without credentials fails gracefully."""
        with patch.dict('os.environ', {}, clear=True):
            service = SheetsService()

            assert service.client is None
            assert service.workbook is None

    def test_get_or_create_worksheet_existing(self):
        """Test getting an existing worksheet."""
        service = SheetsService()
        mock_workbook = Mock()
        mock_worksheet = Mock()

        mock_workbook.worksheet.return_value = mock_worksheet
        service.workbook = mock_workbook

        result = service.get_or_create_worksheet('TestSheet', ['Col1', 'Col2'])

        assert result == mock_worksheet
        mock_workbook.worksheet.assert_called_once_with('TestSheet')

    def test_get_or_create_worksheet_new(self):
        """Test creating a new worksheet when it doesn't exist."""
        service = SheetsService()
        mock_workbook = Mock()
        mock_worksheet = Mock()

        # Simulate worksheet not found, then create new one
        import gspread
        mock_workbook.worksheet.side_effect = gspread.WorksheetNotFound("Not found")
        mock_workbook.add_worksheet.return_value = mock_worksheet
        service.workbook = mock_workbook

        result = service.get_or_create_worksheet('NewSheet', ['Col1', 'Col2'])

        assert result == mock_worksheet
        mock_workbook.add_worksheet.assert_called_once()
        mock_worksheet.insert_row.assert_called_once_with(['Col1', 'Col2'], 1)

    def test_get_inventory_data_with_connection(self):
        """Test getting inventory data with active connection."""
        service = SheetsService()
        mock_worksheet = Mock()

        # Mock worksheet data
        mock_data = [
            {
                'ItemID': '1001',
                'SKU': 'TEST-001',
                'Name': 'Test Product',
                'Category': 'Sneakers',
                'QtyOnHand': 10
            }
        ]
        mock_worksheet.get_all_records.return_value = mock_data

        with patch.object(service, 'get_or_create_worksheet', return_value=mock_worksheet):
            result = service.get_inventory_data()

            assert isinstance(result, pd.DataFrame)
            assert len(result) == 1
            assert result.iloc[0]['SKU'] == 'TEST-001'

    def test_get_inventory_data_without_connection(self):
        """Test getting inventory data without connection returns mock data."""
        service = SheetsService()
        service.workbook = None  # No connection

        result = service.get_inventory_data()

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1  # Mock data
        assert 'SKU' in result.columns

    def test_update_inventory_data_success(self):
        """Test successful inventory data update."""
        service = SheetsService()
        mock_worksheet = Mock()

        test_data = pd.DataFrame([
            {
                'ItemID': '1001',
                'SKU': 'TEST-001',
                'Name': 'Test Product',
                'QtyOnHand': 10
            }
        ])

        with patch.object(service, 'get_or_create_worksheet', return_value=mock_worksheet):
            result = service.update_inventory_data(test_data)

            assert result is True
            mock_worksheet.clear.assert_called_once()
            mock_worksheet.insert_row.assert_called()

    def test_update_inventory_data_no_connection(self):
        """Test inventory data update without connection."""
        service = SheetsService()
        service.workbook = None

        test_data = pd.DataFrame([{'SKU': 'TEST-001'}])

        result = service.update_inventory_data(test_data)

        assert result is False

    def test_get_config_default_values(self):
        """Test getting configuration with default values."""
        service = SheetsService()
        service.workbook = None  # No connection

        config = service.get_config()

        assert 'LowStockThreshold' in config
        assert config['LowStockThreshold'] == 5

    def test_get_config_from_worksheet(self):
        """Test getting configuration from worksheet."""
        service = SheetsService()
        mock_worksheet = Mock()

        mock_config_data = [
            {
                'Setting': 'LowStockThreshold',
                'Value': '10',
                'Description': 'Minimum stock level'
            }
        ]
        mock_worksheet.get_all_records.return_value = mock_config_data

        with patch.object(service, 'get_or_create_worksheet', return_value=mock_worksheet):
            config = service.get_config()

            assert config['LowStockThreshold'] == '10'

    def test_add_sales_log_entry(self):
        """Test adding sales log entry."""
        service = SheetsService()
        mock_worksheet = Mock()

        with patch.object(service, 'get_or_create_worksheet', return_value=mock_worksheet):
            result = service.add_sales_log_entry('hash123', '2025-10-09', 100.0)

            assert result is True
            mock_worksheet.insert_row.assert_called_once()

    def test_update_restock_list(self):
        """Test updating restock list."""
        service = SheetsService()
        mock_worksheet = Mock()

        low_stock_data = pd.DataFrame([
            {
                'SKU': 'TEST-001',
                'Name': 'Test Product',
                'QtyOnHand': 2,
                'Threshold': 5
            }
        ])

        with patch.object(service, 'get_or_create_worksheet', return_value=mock_worksheet):
            result = service.update_restock_list(low_stock_data)

            assert result is True
            mock_worksheet.clear.assert_called_once()

    @patch('os.makedirs')
    @patch('pandas.DataFrame.to_csv')
    def test_backup_to_csv(self, mock_to_csv, mock_makedirs):
        """Test CSV backup functionality."""
        service = SheetsService()

        test_data = pd.DataFrame([{'SKU': 'TEST-001'}])

        result = service.backup_to_csv(test_data, 'test_backup.csv')

        assert result is True
        mock_makedirs.assert_called_once()
        mock_to_csv.assert_called_once()

    def test_get_sales_log_empty(self):
        """Test getting empty sales log."""
        service = SheetsService()
        service.workbook = None  # No connection

        result = service.get_sales_log()

        assert isinstance(result, pd.DataFrame)
        assert result.empty
        assert 'SaleHash' in result.columns


class TestSheetsServiceIntegration:
    """Integration tests for Sheets service (would require actual Google Sheets setup)."""

    @pytest.mark.skip(reason="Requires actual Google Sheets credentials")
    def test_real_sheets_connection(self):
        """Test real connection to Google Sheets (requires setup)."""
        # This test would require actual service account credentials
        # and a test Google Sheet to be set up
        pass

    @pytest.mark.skip(reason="Requires actual Google Sheets credentials")
    def test_real_data_operations(self):
        """Test real data operations on Google Sheets (requires setup)."""
        # This test would perform actual read/write operations
        # on a test Google Sheet
        pass
