"""
Tests for inventory business logic and reconciliation.
"""
import pandas as pd

from services.inventory import InventoryService


class TestInventoryService:
    """Test cases for InventoryService."""

    def test_auto_sort_by_category_name_size(self, sample_inventory_data, mock_sheets_service):
        """Test that inventory is sorted by Category -> Name -> Size."""
        service = InventoryService(mock_sheets_service)

        # Shuffle the data to test sorting
        shuffled_data = sample_inventory_data.sample(frac=1).reset_index(drop=True)
        sorted_data = service.auto_sort(shuffled_data)

        # Check that data is sorted correctly
        categories = sorted_data['Category'].tolist()
        sorted_data['Name'].tolist()
        sorted_data['Size'].tolist()

        # Verify categories are in order
        assert categories == sorted(categories)

        # Check that the sort is stable and correct
        assert len(sorted_data) == len(sample_inventory_data)

    def test_auto_sort_with_numeric_sizes(self, mock_sheets_service):
        """Test sorting with numeric shoe sizes."""
        service = InventoryService(mock_sheets_service)

        data = pd.DataFrame([
            {'Category': 'Sneakers', 'Name': 'Jordan', 'Size': '10.5'},
            {'Category': 'Sneakers', 'Name': 'Jordan', 'Size': '9'},
            {'Category': 'Sneakers', 'Name': 'Jordan', 'Size': '11'},
            {'Category': 'Sneakers', 'Name': 'Jordan', 'Size': '8.5'}
        ])

        sorted_data = service.auto_sort(data)
        expected_sizes = ['8.5', '9', '10.5', '11']

        assert sorted_data['Size'].tolist() == expected_sizes

    def test_auto_sort_with_clothing_sizes(self, mock_sheets_service):
        """Test sorting with clothing sizes (S, M, L, XL)."""
        service = InventoryService(mock_sheets_service)

        data = pd.DataFrame([
            {'Category': 'Clothing', 'Name': 'T-Shirt', 'Size': 'XL'},
            {'Category': 'Clothing', 'Name': 'T-Shirt', 'Size': 'S'},
            {'Category': 'Clothing', 'Name': 'T-Shirt', 'Size': 'L'},
            {'Category': 'Clothing', 'Name': 'T-Shirt', 'Size': 'M'}
        ])

        sorted_data = service.auto_sort(data)
        expected_sizes = ['S', 'M', 'L', 'XL']

        assert sorted_data['Size'].tolist() == expected_sizes

    def test_low_stock_filter_default_threshold(self, sample_inventory_data, mock_sheets_service):
        """Test low stock filtering with default threshold."""
        service = InventoryService(mock_sheets_service)

        low_stock_items = service.low_stock(sample_inventory_data)

        # Should return items with QtyOnHand <= 5
        assert len(low_stock_items) == 1  # Only JD1-WHT-9 with qty 3
        assert low_stock_items.iloc[0]['SKU'] == 'JD1-WHT-9'

    def test_low_stock_filter_custom_threshold(self, sample_inventory_data, mock_sheets_service):
        """Test low stock filtering with custom threshold."""
        service = InventoryService(mock_sheets_service)

        low_stock_items = service.low_stock(sample_inventory_data, threshold=10)

        # Should return items with QtyOnHand <= 10
        assert len(low_stock_items) == 2  # JD1-BLK-10 (8) and JD1-WHT-9 (3)

    def test_reconcile_sales_basic(self, sample_inventory_data, sample_sales_data, mock_sheets_service):
        """Test basic sales reconciliation."""
        service = InventoryService(mock_sheets_service)

        result = service.reconcile_sales(sample_inventory_data, sample_sales_data)

        assert result['success'] is True
        assert result['processed_sales'] > 0
        assert result['items_updated'] > 0
        assert 'updated_inventory' in result

    def test_reconcile_sales_prevents_negative_inventory(self, mock_sheets_service):
        """Test that reconciliation doesn't create negative inventory."""
        service = InventoryService(mock_sheets_service)

        inventory = pd.DataFrame([
            {'SKU': 'TEST-SKU', 'QtyOnHand': 2, 'QtySold': 0}
        ])

        sales = pd.DataFrame([
            {'SKU': 'TEST-SKU', 'Quantity': 5, 'SaleHash': 'test1'}
        ])

        result = service.reconcile_sales(inventory, sales)
        updated_inventory = result['updated_inventory']

        # Quantity should not go below 0
        assert updated_inventory[updated_inventory['SKU'] == 'TEST-SKU']['QtyOnHand'].iloc[0] == 0

    def test_reconcile_sales_deduplication(self, mock_sheets_service):
        """Test that duplicate sales are not processed twice."""
        service = InventoryService(mock_sheets_service)

        inventory = pd.DataFrame([
            {'SKU': 'TEST-SKU', 'QtyOnHand': 10, 'QtySold': 0}
        ])

        sales = pd.DataFrame([
            {'SKU': 'TEST-SKU', 'Quantity': 2, 'SaleHash': 'duplicate1'},
            {'SKU': 'TEST-SKU', 'Quantity': 2, 'SaleHash': 'duplicate1'}  # Same hash
        ])

        # Process first time
        result1 = service.reconcile_sales(inventory, sales)

        # Process again with same data (should skip duplicates)
        processed_hashes = ['duplicate1']
        result2 = service.reconcile_sales(result1['updated_inventory'], sales, processed_hashes)

        assert result2['skipped_duplicates'] == 2
        assert result2['items_updated'] == 0

    def test_reconcile_sales_missing_sku(self, mock_sheets_service):
        """Test reconciliation with SKU not in inventory."""
        service = InventoryService(mock_sheets_service)

        inventory = pd.DataFrame([
            {'SKU': 'EXISTING-SKU', 'QtyOnHand': 10, 'QtySold': 0}
        ])

        sales = pd.DataFrame([
            {'SKU': 'MISSING-SKU', 'Quantity': 1, 'SaleHash': 'test1'}
        ])

        result = service.reconcile_sales(inventory, sales)

        assert result['success'] is True
        assert len(result['errors']) > 0
        assert 'MISSING-SKU' in result['errors'][0]

    def test_calculate_inventory_metrics(self, sample_inventory_data, mock_sheets_service):
        """Test inventory metrics calculation."""
        service = InventoryService(mock_sheets_service)

        metrics = service.calculate_inventory_metrics(sample_inventory_data)

        assert metrics['total_skus'] == 3
        assert metrics['total_on_hand'] == 23  # 8 + 3 + 12
        assert metrics['total_sold'] == 31  # 2 + 7 + 22
        assert metrics['total_value'] > 0
        assert 'categories' in metrics
        assert 'Sneakers' in metrics['categories']
        assert 'Clothing' in metrics['categories']

    def test_generate_restock_suggestions(self, mock_sheets_service):
        """Test restock suggestions generation."""
        service = InventoryService(mock_sheets_service)

        low_stock_data = pd.DataFrame([
            {'SKU': 'OUT-OF-STOCK', 'Name': 'Test Product 1', 'QtyOnHand': 0, 'QtySold': 10, 'Threshold': 5},
            {'SKU': 'LOW-STOCK', 'Name': 'Test Product 2', 'QtyOnHand': 2, 'QtySold': 5, 'Threshold': 5},
            {'SKU': 'MEDIUM-STOCK', 'Name': 'Test Product 3', 'QtyOnHand': 4, 'QtySold': 2, 'Threshold': 5}
        ])

        suggestions = service.generate_restock_suggestions(low_stock_data)

        assert suggestions['total_items'] == 3
        assert suggestions['high_priority'] == 1  # Out of stock item

        # Check that suggestions are sorted by priority
        first_suggestion = suggestions['suggestions'][0]
        assert first_suggestion['priority'] == 'High'
        assert first_suggestion['current_qty'] == 0

    def test_empty_dataframe_handling(self, mock_sheets_service):
        """Test that methods handle empty DataFrames gracefully."""
        service = InventoryService(mock_sheets_service)
        empty_df = pd.DataFrame()

        # Test all methods with empty data
        sorted_empty = service.auto_sort(empty_df)
        assert sorted_empty.empty

        low_stock_empty = service.low_stock(empty_df)
        assert low_stock_empty.empty

        metrics_empty = service.calculate_inventory_metrics(empty_df)
        assert metrics_empty['total_skus'] == 0

        reconcile_result = service.reconcile_sales(empty_df, empty_df)
        assert reconcile_result['success'] is True
        assert reconcile_result['processed_sales'] == 0
