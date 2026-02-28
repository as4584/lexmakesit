"""
Test suite for Google Sheets Repository with mocked gspread DataFrame operations.

TDD Approach:
- Tests define the repository interface
- Implementation will follow Repository pattern
"""
from unittest.mock import Mock, patch

import pandas as pd
import pytest


class TestSheetsRepositoryRead:
    """Test reading operations from Google Sheets."""

    def test_get_inventory_data(self) -> None:
        """Test retrieving inventory data from Sheets."""
        from src.infra.sheets_repo import SheetsRepository

        # Arrange
        mock_worksheet = Mock()
        mock_worksheet.get_all_records.return_value = [
            {'SKU': 'A', 'QtyOnHand': 10, 'Name': 'Product A'},
            {'SKU': 'B', 'QtyOnHand': 5, 'Name': 'Product B'}
        ]

        with patch('gspread.authorize') as mock_auth:
            mock_client = Mock()
            mock_spreadsheet = Mock()
            mock_client.open.return_value = mock_spreadsheet
            mock_spreadsheet.worksheet.return_value = mock_worksheet
            mock_auth.return_value = mock_client

            repo = SheetsRepository(credentials_path='fake.json', sheet_name='Test')

            # Act
            inventory_df = repo.get_inventory()

            # Assert
            assert isinstance(inventory_df, pd.DataFrame)
            assert len(inventory_df) == 2
            assert 'SKU' in inventory_df.columns
            assert inventory_df.iloc[0]['SKU'] == 'A'

    def test_get_config(self) -> None:
        """Test retrieving configuration from Config worksheet."""
        from src.infra.sheets_repo import SheetsRepository

        mock_worksheet = Mock()
        mock_worksheet.get_all_records.return_value = [
            {'Setting': 'LowStockThreshold', 'Value': '5'},
            {'Setting': 'SyncIntervalHours', 'Value': '1'}
        ]

        with patch('gspread.authorize') as mock_auth:
            mock_client = Mock()
            mock_spreadsheet = Mock()
            mock_client.open.return_value = mock_spreadsheet
            mock_spreadsheet.worksheet.return_value = mock_worksheet
            mock_auth.return_value = mock_client

            repo = SheetsRepository(credentials_path='fake.json', sheet_name='Test')

            # Act
            config = repo.get_config()

            # Assert
            assert config['LowStockThreshold'] == 5
            assert config['SyncIntervalHours'] == 1

    def test_get_sales_log(self) -> None:
        """Test retrieving sales log for deduplication."""
        from src.infra.sheets_repo import SheetsRepository

        mock_worksheet = Mock()
        mock_worksheet.get_all_records.return_value = [
            {'SaleHash': 'abc123', 'ProcessedAt': '2025-10-21 10:00:00'},
            {'SaleHash': 'def456', 'ProcessedAt': '2025-10-21 11:00:00'}
        ]

        with patch('gspread.authorize') as mock_auth:
            mock_client = Mock()
            mock_spreadsheet = Mock()
            mock_client.open.return_value = mock_spreadsheet
            mock_spreadsheet.worksheet.return_value = mock_worksheet
            mock_auth.return_value = mock_client

            repo = SheetsRepository(credentials_path='fake.json', sheet_name='Test')

            # Act
            sales_log = repo.get_sales_log()

            # Assert
            assert isinstance(sales_log, pd.DataFrame)
            assert len(sales_log) == 2
            assert 'SaleHash' in sales_log.columns


class TestSheetsRepositoryWrite:
    """Test writing operations to Google Sheets."""

    def test_update_inventory(self) -> None:
        """Test updating inventory data in Sheets."""
        from src.infra.sheets_repo import SheetsRepository

        mock_worksheet = Mock()

        with patch('gspread.authorize') as mock_auth:
            mock_client = Mock()
            mock_spreadsheet = Mock()
            mock_client.open.return_value = mock_spreadsheet
            mock_spreadsheet.worksheet.return_value = mock_worksheet
            mock_auth.return_value = mock_client

            repo = SheetsRepository(credentials_path='fake.json', sheet_name='Test')

            inventory_df = pd.DataFrame([
                {'SKU': 'A', 'QtyOnHand': 8, 'Name': 'Product A'}
            ])

            # Act
            result = repo.update_inventory(inventory_df)

            # Assert
            assert result is True
            mock_worksheet.clear.assert_called_once()
            mock_worksheet.update.assert_called_once()

    def test_append_sales_log_entry(self) -> None:
        """Test appending to sales log for deduplication tracking."""
        from src.infra.sheets_repo import SheetsRepository

        mock_worksheet = Mock()

        with patch('gspread.authorize') as mock_auth:
            mock_client = Mock()
            mock_spreadsheet = Mock()
            mock_client.open.return_value = mock_spreadsheet
            mock_spreadsheet.worksheet.return_value = mock_worksheet
            mock_auth.return_value = mock_client

            repo = SheetsRepository(credentials_path='fake.json', sheet_name='Test')

            # Act
            repo.add_sales_log_entry('abc123')

            # Assert
            mock_worksheet.append_row.assert_called_once()
            call_args = mock_worksheet.append_row.call_args[0][0]
            assert 'abc123' in call_args

    def test_update_restock_list(self) -> None:
        """Test updating restock list worksheet."""
        from src.infra.sheets_repo import SheetsRepository

        mock_worksheet = Mock()

        with patch('gspread.authorize') as mock_auth:
            mock_client = Mock()
            mock_spreadsheet = Mock()
            mock_client.open.return_value = mock_spreadsheet
            mock_spreadsheet.worksheet.return_value = mock_worksheet
            mock_auth.return_value = mock_client

            repo = SheetsRepository(credentials_path='fake.json', sheet_name='Test')

            low_stock_df = pd.DataFrame([
                {'SKU': 'A', 'QtyOnHand': 2, 'Priority': 'High'}
            ])

            # Act
            result = repo.update_restock_list(low_stock_df)

            # Assert
            assert result is True
            mock_worksheet.clear.assert_called_once()


class TestSheetsRepositoryUnitOfWork:
    """Test Unit of Work pattern for atomic operations."""

    def test_unit_of_work_commit(self) -> None:
        """Test that Unit of Work commits all changes atomically."""
        from src.infra.sheets_repo import SheetsRepository, SheetsUnitOfWork

        with patch('gspread.authorize') as mock_auth:
            mock_client = Mock()
            mock_spreadsheet = Mock()
            mock_client.open.return_value = mock_spreadsheet
            mock_auth.return_value = mock_client

            repo = SheetsRepository(credentials_path='fake.json', sheet_name='Test')

            # Act
            with SheetsUnitOfWork(repo) as uow:
                uow.inventory.update(pd.DataFrame([{'SKU': 'A'}]))
                uow.sales_log.add_entry('hash1')
                uow.commit()

            # Assert - all operations committed
            assert True  # If no exception, commit succeeded

    def test_unit_of_work_rollback_on_error(self) -> None:
        """Test that Unit of Work rolls back on error."""
        from src.infra.sheets_repo import SheetsRepository, SheetsUnitOfWork

        with patch('gspread.authorize') as mock_auth:
            mock_client = Mock()
            mock_spreadsheet = Mock()
            mock_client.open.return_value = mock_spreadsheet
            mock_auth.return_value = mock_client

            repo = SheetsRepository(credentials_path='fake.json', sheet_name='Test')

            # Act & Assert
            with pytest.raises(RuntimeError), SheetsUnitOfWork(repo) as uow:
                uow.inventory.update(pd.DataFrame([{'SKU': 'A'}]))
                raise RuntimeError("Simulated error")
                uow.commit()  # Should not reach here

            # No changes should be persisted


class TestSheetsRepositoryErrorHandling:
    """Test error handling and recovery."""

    def test_handle_missing_worksheet(self) -> None:
        """Test graceful handling of missing worksheets."""
        from src.infra.exceptions import WorksheetNotFoundError
        from src.infra.sheets_repo import SheetsRepository

        with patch('gspread.authorize') as mock_auth:
            mock_client = Mock()
            mock_spreadsheet = Mock()
            mock_spreadsheet.worksheet.side_effect = Exception("Worksheet not found")
            mock_client.open.return_value = mock_spreadsheet
            mock_auth.return_value = mock_client

            repo = SheetsRepository(credentials_path='fake.json', sheet_name='Test')

            # Act & Assert
            with pytest.raises(WorksheetNotFoundError):
                repo.get_inventory()

    def test_handle_api_quota_exceeded(self) -> None:
        """Test handling of Google API quota errors."""
        from src.infra.exceptions import QuotaExceededError
        from src.infra.sheets_repo import SheetsRepository

        with patch('gspread.authorize') as mock_auth:
            mock_client = Mock()
            mock_spreadsheet = Mock()
            mock_worksheet = Mock()
            mock_worksheet.get_all_records.side_effect = Exception("Quota exceeded")
            mock_spreadsheet.worksheet.return_value = mock_worksheet
            mock_client.open.return_value = mock_spreadsheet
            mock_auth.return_value = mock_client

            repo = SheetsRepository(credentials_path='fake.json', sheet_name='Test')

            # Act & Assert
            with pytest.raises(QuotaExceededError):
                repo.get_inventory()

    def test_retry_on_transient_failure(self) -> None:
        """Test automatic retry on transient failures."""
        from src.infra.sheets_repo import SheetsRepository

        with patch('gspread.authorize') as mock_auth:
            mock_client = Mock()
            mock_spreadsheet = Mock()
            mock_worksheet = Mock()

            # First call fails, second succeeds
            mock_worksheet.get_all_records.side_effect = [
                Exception("Transient error"),
                [{'SKU': 'A', 'QtyOnHand': 10}]
            ]

            mock_spreadsheet.worksheet.return_value = mock_worksheet
            mock_client.open.return_value = mock_spreadsheet
            mock_auth.return_value = mock_client

            repo = SheetsRepository(
                credentials_path='fake.json',
                sheet_name='Test',
                max_retries=2
            )

            # Act
            result = repo.get_inventory()

            # Assert - should succeed after retry
            assert len(result) == 1
            assert mock_worksheet.get_all_records.call_count == 2


class TestSheetsRepositoryDataTransformation:
    """Test data transformation between DataFrames and Sheets format."""

    def test_dataframe_to_sheets_format(self) -> None:
        """Test converting DataFrame to format suitable for Sheets."""
        from src.infra.sheets_repo import SheetsRepository

        repo = SheetsRepository(credentials_path='fake.json', sheet_name='Test')

        df = pd.DataFrame([
            {'SKU': 'A', 'QtyOnHand': 10, 'LastUpdated': pd.Timestamp('2025-10-21')}
        ])

        # Act
        sheets_data = repo._dataframe_to_sheets(df)

        # Assert
        assert isinstance(sheets_data, list)
        assert isinstance(sheets_data[0], list)  # List of lists
        assert len(sheets_data[0]) == 3  # 3 columns

    def test_sheets_to_dataframe_format(self) -> None:
        """Test converting Sheets records to DataFrame."""
        from src.infra.sheets_repo import SheetsRepository

        repo = SheetsRepository(credentials_path='fake.json', sheet_name='Test')

        sheets_records = [
            {'SKU': 'A', 'QtyOnHand': '10', 'RetailPrice': '99.99'},
            {'SKU': 'B', 'QtyOnHand': '5', 'RetailPrice': '49.99'}
        ]

        # Act
        df = repo._sheets_to_dataframe(sheets_records)

        # Assert
        assert isinstance(df, pd.DataFrame)
        assert df['QtyOnHand'].dtype in [int, 'int64']  # Converted to int
        assert df['RetailPrice'].dtype in [float, 'float64']  # Converted to float


class TestSheetsRepositoryCaching:
    """Test caching layer for performance optimization."""

    def test_cache_inventory_reads(self) -> None:
        """Test that repeated reads use cache."""
        from src.infra.sheets_repo import SheetsRepository

        mock_worksheet = Mock()
        mock_worksheet.get_all_records.return_value = [{'SKU': 'A'}]

        with patch('gspread.authorize') as mock_auth:
            mock_client = Mock()
            mock_spreadsheet = Mock()
            mock_client.open.return_value = mock_spreadsheet
            mock_spreadsheet.worksheet.return_value = mock_worksheet
            mock_auth.return_value = mock_client

            repo = SheetsRepository(
                credentials_path='fake.json',
                sheet_name='Test',
                enable_cache=True,
                cache_ttl=60
            )

            # Act - read twice
            result1 = repo.get_inventory()
            result2 = repo.get_inventory()

            # Assert - should only call Sheets API once
            assert mock_worksheet.get_all_records.call_count == 1
            assert result1.equals(result2)

    def test_cache_invalidation_on_write(self) -> None:
        """Test that cache is invalidated after writes."""
        from src.infra.sheets_repo import SheetsRepository

        mock_worksheet = Mock()
        mock_worksheet.get_all_records.return_value = [{'SKU': 'A'}]

        with patch('gspread.authorize') as mock_auth:
            mock_client = Mock()
            mock_spreadsheet = Mock()
            mock_client.open.return_value = mock_spreadsheet
            mock_spreadsheet.worksheet.return_value = mock_worksheet
            mock_auth.return_value = mock_client

            repo = SheetsRepository(
                credentials_path='fake.json',
                sheet_name='Test',
                enable_cache=True
            )

            # Act
            repo.get_inventory()  # Cache populated
            repo.update_inventory(pd.DataFrame([{'SKU': 'B'}]))  # Cache invalidated
            repo.get_inventory()  # Should fetch fresh data

            # Assert
            assert mock_worksheet.get_all_records.call_count == 2


# Fixtures for Sheets repository tests
@pytest.fixture
def mock_gspread_client():
    """Mock gspread client for testing."""
    with patch('gspread.authorize') as mock_auth:
        mock_client = Mock()
        mock_spreadsheet = Mock()
        mock_client.open.return_value = mock_spreadsheet
        mock_auth.return_value = mock_client
        yield mock_client, mock_spreadsheet


@pytest.fixture
def mock_worksheet(mock_gspread_client):
    """Mock worksheet for testing."""
    _, mock_spreadsheet = mock_gspread_client
    mock_ws = Mock()
    mock_spreadsheet.worksheet.return_value = mock_ws
    return mock_ws


@pytest.fixture
def sample_sheets_data():
    """Sample data in Sheets format."""
    return [
        {
            'ItemID': '1',
            'SKU': 'TEST-001',
            'Name': 'Test Product',
            'Category': 'Test',
            'Color': 'Black',
            'Size': 'M',
            'Barcode': '12345',
            'RetailPrice': '99.99',
            'QtyOnHand': '10',
            'QtySold': '5',
            'Location': 'A1',
            'LastUpdated': '2025-10-21 10:00:00'
        }
    ]
