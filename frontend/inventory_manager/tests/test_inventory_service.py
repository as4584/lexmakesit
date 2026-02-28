"""
Test suite for Inventory Service with focus on sales reconciliation, idempotency, and low-stock detection.

TDD Approach:
- Tests written first to define expected behavior
- Implementation will be created in src/services/inventory_service.py
"""
from datetime import datetime

import pandas as pd
import pytest


class TestInventoryServiceSalesReconciliation:
    """Test sales reconciliation logic."""

    def test_apply_sales_reduces_quantity(self) -> None:
        """Test that applying sales correctly reduces on-hand quantity."""
        from src.domain.models import Product, Sale
        from src.services.inventory_service import InventoryService

        # Arrange
        service = InventoryService()
        product = Product(
            sku='TEST-001',
            name='Test Product',
            qty_on_hand=10,
            qty_sold=5
        )
        sale = Sale(
            sku='TEST-001',
            quantity=3,
            date=datetime.now()
        )

        # Act
        updated_product = service.apply_sale(product, sale)

        # Assert
        assert updated_product.qty_on_hand == 7  # 10 - 3
        assert updated_product.qty_sold == 8      # 5 + 3

    def test_apply_sales_batch(self) -> None:
        """Test applying multiple sales at once."""
        from src.services.inventory_service import InventoryService

        service = InventoryService()

        inventory_df = pd.DataFrame([
            {'SKU': 'A', 'QtyOnHand': 20, 'QtySold': 5},
            {'SKU': 'B', 'QtyOnHand': 15, 'QtySold': 10}
        ])

        sales_df = pd.DataFrame([
            {'SKU': 'A', 'Quantity': 3},
            {'SKU': 'A', 'Quantity': 2},
            {'SKU': 'B', 'Quantity': 5}
        ])

        # Act
        updated_inventory = service.apply_sales_batch(inventory_df, sales_df)

        # Assert
        product_a = updated_inventory[updated_inventory['SKU'] == 'A'].iloc[0]
        assert product_a['QtyOnHand'] == 15  # 20 - 5
        assert product_a['QtySold'] == 10    # 5 + 5

        product_b = updated_inventory[updated_inventory['SKU'] == 'B'].iloc[0]
        assert product_b['QtyOnHand'] == 10  # 15 - 5
        assert product_b['QtySold'] == 15    # 10 + 5

    def test_negative_inventory_prevention(self) -> None:
        """Test that inventory doesn't go below zero."""
        from src.domain.exceptions import NegativeInventoryError
        from src.services.inventory_service import InventoryService

        service = InventoryService()

        inventory_df = pd.DataFrame([
            {'SKU': 'A', 'QtyOnHand': 2, 'QtySold': 0}
        ])

        sales_df = pd.DataFrame([
            {'SKU': 'A', 'Quantity': 5}  # Trying to sell more than available
        ])

        # Act & Assert
        with pytest.raises(NegativeInventoryError) as exc_info:
            service.apply_sales_batch(inventory_df, sales_df, allow_negative=False)

        assert 'SKU A' in str(exc_info.value)


class TestInventoryServiceIdempotency:
    """Test idempotent operations to prevent double-processing."""

    def test_duplicate_sale_detection(self) -> None:
        """Test that duplicate sales are not applied twice."""
        from src.services.inventory_service import InventoryService

        service = InventoryService()

        inventory_df = pd.DataFrame([
            {'SKU': 'A', 'QtyOnHand': 10, 'QtySold': 0}
        ])

        # Same sale applied twice (same hash)
        sales_df = pd.DataFrame([
            {'SKU': 'A', 'Quantity': 2, 'SaleHash': 'abc123', 'Date': '2025-10-21'},
            {'SKU': 'A', 'Quantity': 2, 'SaleHash': 'abc123', 'Date': '2025-10-21'},
        ])

        # Act
        updated_inventory = service.apply_sales_batch(inventory_df, sales_df)

        # Assert - should only apply once
        assert updated_inventory.loc[0, 'QtyOnHand'] == 8  # 10 - 2 (not 10 - 4)
        assert updated_inventory.loc[0, 'QtySold'] == 2

    def test_sale_hash_generation(self) -> None:
        """Test consistent hash generation for deduplication."""
        from src.services.inventory_service import generate_sale_hash

        sale1 = {
            'SKU': 'TEST-001',
            'Quantity': 3,
            'Date': '2025-10-21',
            'UnitPrice': 99.99
        }

        sale2 = {
            'SKU': 'TEST-001',
            'Quantity': 3,
            'Date': '2025-10-21',
            'UnitPrice': 99.99
        }

        sale3 = {
            'SKU': 'TEST-001',
            'Quantity': 5,  # Different quantity
            'Date': '2025-10-21',
            'UnitPrice': 99.99
        }

        # Act
        hash1 = generate_sale_hash(sale1)
        hash2 = generate_sale_hash(sale2)
        hash3 = generate_sale_hash(sale3)

        # Assert
        assert hash1 == hash2  # Same sale = same hash
        assert hash1 != hash3  # Different sale = different hash

    def test_idempotent_sync_operation(self) -> None:
        """Test that running sync multiple times doesn't duplicate data."""
        from src.services.inventory_service import InventoryService

        service = InventoryService()

        initial_state = pd.DataFrame([
            {'SKU': 'A', 'QtyOnHand': 10, 'QtySold': 0}
        ])

        sales = pd.DataFrame([
            {'SKU': 'A', 'Quantity': 2, 'SaleHash': 'sync1'}
        ])

        # Act - run sync twice
        result1 = service.sync_with_deduplication(initial_state, sales)
        result2 = service.sync_with_deduplication(result1, sales)

        # Assert - second sync should not change anything
        assert result1.equals(result2)
        assert result1.loc[0, 'QtyOnHand'] == 8


class TestInventoryServiceLowStockDetection:
    """Test low stock detection and alerting."""

    def test_detect_low_stock_items(self) -> None:
        """Test identification of items below threshold."""
        from src.services.inventory_service import InventoryService

        service = InventoryService()

        inventory_df = pd.DataFrame([
            {'SKU': 'A', 'QtyOnHand': 2, 'Name': 'Product A'},   # Low
            {'SKU': 'B', 'QtyOnHand': 10, 'Name': 'Product B'},  # OK
            {'SKU': 'C', 'QtyOnHand': 0, 'Name': 'Product C'},   # Critical
            {'SKU': 'D', 'QtyOnHand': 5, 'Name': 'Product D'},   # At threshold
        ])

        # Act
        low_stock = service.detect_low_stock(inventory_df, threshold=5)

        # Assert
        assert len(low_stock) == 3  # A, C, D
        assert 'A' in low_stock['SKU'].values
        assert 'C' in low_stock['SKU'].values
        assert 'D' in low_stock['SKU'].values
        assert 'B' not in low_stock['SKU'].values

    def test_low_stock_priority_levels(self) -> None:
        """Test that low stock items are categorized by priority."""
        from src.services.inventory_service import InventoryService

        service = InventoryService()

        inventory_df = pd.DataFrame([
            {'SKU': 'A', 'QtyOnHand': 0},   # Critical
            {'SKU': 'B', 'QtyOnHand': 1},   # High
            {'SKU': 'C', 'QtyOnHand': 3},   # Medium
        ])

        # Act
        low_stock = service.detect_low_stock_with_priority(inventory_df, threshold=5)

        # Assert
        critical = low_stock[low_stock['Priority'] == 'Critical']
        high = low_stock[low_stock['Priority'] == 'High']
        medium = low_stock[low_stock['Priority'] == 'Medium']

        assert len(critical) == 1
        assert len(high) == 1
        assert len(medium) == 1

    def test_restock_recommendation(self) -> None:
        """Test automated restock quantity recommendations."""
        from src.services.inventory_service import InventoryService

        service = InventoryService()

        inventory_df = pd.DataFrame([
            {'SKU': 'A', 'QtyOnHand': 2, 'QtySold': 20, 'Category': 'Sneakers'},
        ])

        # Act - recommend based on sales velocity
        recommendations = service.generate_restock_recommendations(inventory_df)

        # Assert
        assert len(recommendations) == 1
        assert recommendations.loc[0, 'RecommendedQty'] > 0
        assert recommendations.loc[0, 'Reason'] is not None


class TestInventoryServiceDataValidation:
    """Test data validation and integrity checks."""

    def test_validate_inventory_schema(self) -> None:
        """Test that inventory data matches expected schema."""
        from src.domain.exceptions import InvalidInventorySchemaError
        from src.services.inventory_service import InventoryService

        service = InventoryService()

        # Missing required columns
        invalid_df = pd.DataFrame([
            {'SKU': 'A', 'Name': 'Product'}  # Missing QtyOnHand, etc.
        ])

        # Act & Assert
        with pytest.raises(InvalidInventorySchemaError):
            service.validate_inventory_schema(invalid_df)

    def test_validate_price_consistency(self) -> None:
        """Test that retail prices are valid."""
        from src.services.inventory_service import InventoryService

        service = InventoryService()

        inventory_df = pd.DataFrame([
            {'SKU': 'A', 'RetailPrice': -10.00},  # Negative price
            {'SKU': 'B', 'RetailPrice': 0},       # Zero price
            {'SKU': 'C', 'RetailPrice': 99.99},   # Valid
        ])

        # Act
        validation_result = service.validate_prices(inventory_df)

        # Assert
        assert len(validation_result['invalid_prices']) == 2
        assert 'A' in validation_result['invalid_prices']['SKU'].values
        assert 'B' in validation_result['invalid_prices']['SKU'].values


class TestInventoryServiceSorting:
    """Test inventory sorting functionality."""

    def test_auto_sort_by_category_name_size(self) -> None:
        """Test standard sorting: Category -> Name -> Size."""
        from src.services.inventory_service import InventoryService

        service = InventoryService()

        inventory_df = pd.DataFrame([
            {'SKU': 'C', 'Category': 'Sneakers', 'Name': 'Air Jordan', 'Size': '11'},
            {'SKU': 'A', 'Category': 'Accessories', 'Name': 'Hat', 'Size': 'OS'},
            {'SKU': 'B', 'Category': 'Sneakers', 'Name': 'Air Jordan', 'Size': '9'},
        ])

        # Act
        sorted_df = service.auto_sort(inventory_df)

        # Assert
        assert sorted_df.iloc[0]['SKU'] == 'A'  # Accessories first
        assert sorted_df.iloc[1]['SKU'] == 'B'  # Sneakers, size 9
        assert sorted_df.iloc[2]['SKU'] == 'C'  # Sneakers, size 11


# Fixtures for inventory service tests
@pytest.fixture
def sample_inventory() -> pd.DataFrame:
    """Sample inventory for testing."""
    return pd.DataFrame([
        {
            'ItemID': '1',
            'SKU': 'SHOE-001',
            'Name': 'Test Shoe',
            'Category': 'Sneakers',
            'Color': 'Black',
            'Size': '10',
            'Barcode': '12345',
            'RetailPrice': 150.00,
            'QtyOnHand': 5,
            'QtySold': 10,
            'Location': 'A1',
            'LastUpdated': datetime.now().isoformat()
        }
    ])


@pytest.fixture
def sample_sales() -> pd.DataFrame:
    """Sample sales for testing."""
    return pd.DataFrame([
        {
            'Date': datetime.now().strftime('%Y-%m-%d'),
            'SKU': 'SHOE-001',
            'Quantity': 2,
            'UnitPrice': 150.00,
            'Total': 300.00,
            'SaleHash': 'test_hash_001'
        }
    ])
