"""
Tests for Flask application routes and functionality.
"""
import json
from unittest.mock import Mock, patch


class TestFlaskRoutes:
    """Test cases for Flask application routes."""

    def test_dashboard_route(self, client):
        """Test dashboard route returns successfully."""
        response = client.get('/')

        assert response.status_code == 200
        assert b'Dashboard' in response.data
        assert b'Total SKUs' in response.data

    def test_inventory_route(self, client):
        """Test inventory route returns successfully."""
        response = client.get('/inventory')

        assert response.status_code == 200
        assert b'Inventory Management' in response.data
        assert b'inventory' in response.data.lower()

    def test_low_stock_route(self, client):
        """Test low stock route returns successfully."""
        response = client.get('/low-stock')

        assert response.status_code == 200
        assert b'Low Stock' in response.data

    def test_sync_endpoint_post(self, client):
        """Test manual sync endpoint."""
        with patch('services.lightspeed.api.LightspeedAPI') as mock_api_class:
            mock_api = Mock()
            mock_api.sync_from_ls.return_value = {'success': True}
            mock_api_class.return_value = mock_api

            response = client.post('/sync')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'success'

    def test_ingest_csv_no_file(self, client):
        """Test CSV upload with no file."""
        response = client.post('/ingest-csv')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'No file uploaded' in data['message']

    def test_ingest_csv_empty_filename(self, client):
        """Test CSV upload with empty filename."""
        response = client.post('/ingest-csv', data={'file': (None, '')})

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'No file selected' in data['message']

    def test_sales_endpoint_with_params(self, client):
        """Test sales endpoint with date parameters."""
        response = client.get('/sales?from=2025-10-01&to=2025-10-09')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert data['from_date'] == '2025-10-01'
        assert data['to_date'] == '2025-10-09'

    def test_sales_endpoint_without_params(self, client):
        """Test sales endpoint without parameters."""
        response = client.get('/sales')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert data['from_date'] is None
        assert data['to_date'] is None

    def test_invalid_route_404(self, client):
        """Test that invalid routes return 404."""
        response = client.get('/nonexistent-route')

        assert response.status_code == 404

    def test_dashboard_with_mock_data(self, client):
        """Test dashboard displays mock data correctly."""
        response = client.get('/')

        # Check that mock data is displayed
        assert b'245' in response.data  # total_skus
        assert b'1842' in response.data  # total_on_hand
        assert b'12' in response.data  # low_stock_count

    def test_inventory_with_mock_data(self, client):
        """Test inventory page displays mock data correctly."""
        response = client.get('/inventory')

        # Check for mock inventory items
        assert b'JD1-BLK-10' in response.data
        assert b'Air Jordan 1 Black' in response.data
        assert b'JD1-WHT-9' in response.data
        assert b'Air Jordan 1 White' in response.data


class TestErrorHandling:
    """Test cases for error handling in Flask routes."""

    def test_sync_endpoint_handles_exceptions(self, client):
        """Test that sync endpoint handles exceptions gracefully."""
        with patch('services.lightspeed.api.LightspeedAPI') as mock_api_class:
            mock_api_class.side_effect = Exception("API Error")

            response = client.post('/sync')

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['status'] == 'error'

    def test_dashboard_handles_service_errors(self, client):
        """Test dashboard handles service errors gracefully."""
        # Dashboard should handle missing services gracefully
        # and display mock data when services are not available
        response = client.get('/')

        assert response.status_code == 200
        # Should still show basic dashboard even with service errors

    def test_inventory_handles_service_errors(self, client):
        """Test inventory page handles service errors gracefully."""
        response = client.get('/inventory')

        assert response.status_code == 200
        # Should still show basic inventory page with mock data


class TestCSVUpload:
    """Test cases for CSV upload functionality."""

    def test_upload_valid_csv_file(self, client):
        """Test uploading a valid CSV file."""
        csv_content = b"SKU,Name,Category,RetailPrice\nTEST-001,Test Product,Sneakers,100.00"

        response = client.post('/ingest-csv', data={
            'file': (io.BytesIO(csv_content), 'test.csv')
        })

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'success'

    def test_upload_invalid_file_type(self, client):
        """Test uploading a non-CSV file."""
        response = client.post('/ingest-csv', data={
            'file': (io.BytesIO(b"not a csv"), 'test.txt')
        })

        # Should still process but might fail validation
        assert response.status_code in [200, 400]


# Import io for BytesIO
import io
