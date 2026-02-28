"""
Test configuration and fixtures for inventory manager tests.
"""
import os
import sys
import time
from datetime import datetime

import pandas as pd
import pytest

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def sample_inventory_data():
    """Sample inventory data for testing."""
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
            'LastUpdated': '2025-10-09 12:00:00'
        },
        {
            'ItemID': '1002',
            'SKU': 'JD1-WHT-9',
            'Name': 'Air Jordan 1 White',
            'Category': 'Sneakers',
            'Color': 'White',
            'Size': '9',
            'Barcode': '123456790',
            'RetailPrice': 170.00,
            'QtyOnHand': 3,
            'QtySold': 7,
            'Location': 'A2',
            'LastUpdated': '2025-10-09 12:00:00'
        },
        {
            'ItemID': '1003',
            'SKU': 'HOODIE-BLK-M',
            'Name': 'Supreme Box Logo Hoodie',
            'Category': 'Clothing',
            'Color': 'Black',
            'Size': 'M',
            'Barcode': '567890842',
            'RetailPrice': 350.00,
            'QtyOnHand': 12,
            'QtySold': 22,
            'Location': 'E1',
            'LastUpdated': '2025-10-09 12:00:00'
        }
    ])


@pytest.fixture
def sample_sales_data():
    """Sample sales data for testing."""
    return pd.DataFrame([
        {
            'Date': '2025-10-08',
            'SKU': 'JD1-BLK-10',
            'Quantity': 1,
            'UnitPrice': 170.00,
            'Total': 170.00,
            'SaleHash': 'abc123'
        },
        {
            'Date': '2025-10-08',
            'SKU': 'JD1-WHT-9',
            'Quantity': 2,
            'UnitPrice': 170.00,
            'Total': 340.00,
            'SaleHash': 'def456'
        },
        {
            'Date': '2025-10-09',
            'SKU': 'HOODIE-BLK-M',
            'Quantity': 1,
            'UnitPrice': 350.00,
            'Total': 350.00,
            'SaleHash': 'ghi789'
        }
    ])


@pytest.fixture
def mock_sheets_service():
    """Mock Google Sheets service for testing."""
    from unittest.mock import Mock

    mock_service = Mock()
    mock_service.get_config.return_value = {'LowStockThreshold': 5}
    mock_service.get_inventory_data.return_value = pd.DataFrame()
    mock_service.update_inventory_data.return_value = True
    mock_service.get_sales_log.return_value = pd.DataFrame()
    mock_service.add_sales_log_entry.return_value = True
    mock_service.update_restock_list.return_value = True

    return mock_service


@pytest.fixture
def mock_lightspeed_api():
    """Mock Lightspeed API service for testing."""
    from unittest.mock import Mock

    mock_api = Mock()
    mock_api.get_products.return_value = []
    mock_api.get_sales.return_value = []
    mock_api.sync_from_ls.return_value = {
        'products_count': 0,
        'inventory_items': 0,
        'recent_sales': 0,
        'sync_time': datetime.now().isoformat()
    }

    return mock_api


@pytest.fixture
def app():
    """Create Flask app for testing."""
    import os
    os.environ['FLASK_ENV'] = 'testing'

    from app import app
    app.config['TESTING'] = True

    with app.test_client(), app.app_context():
        yield app


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


# Global anti-hang: disable sleeps during tests when PYTEST_RUNNING is set
@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    import os

    if os.environ.get("PYTEST_RUNNING"):
        monkeypatch.setattr(time, "sleep", lambda *_: None)
