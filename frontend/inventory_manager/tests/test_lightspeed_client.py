"""
Test suite for Lightspeed API Gateway/Adapter with focus on pagination, retries, and rate limiting.

This module follows TDD principles:
- Red: Write failing tests first
- Green: Implement minimal code to pass
- Refactor: Improve code while keeping tests green
"""
from datetime import datetime
from unittest.mock import Mock, patch

import pytest
import requests

# These tests are written BEFORE the refactored lightspeed_client.py exists
# Following TDD: Red phase - tests will fail initially


class TestLightspeedGatewayPagination:
    """Test pagination handling in Lightspeed API Gateway."""

    def test_paginate_single_page(self) -> None:
        """Test pagination with results that fit in a single page."""
        # Arrange
        from src.infra.lightspeed_client import LightspeedGateway

        mock_response = {
            'data': [
                {'id': '1', 'name': 'Product 1'},
                {'id': '2', 'name': 'Product 2'},
            ],
            'meta': {'total': 2, 'per_page': 250}
        }

        with patch('src.infra.lightspeed_client.requests.Session.get') as mock_get:
            mock_get.return_value.json.return_value = mock_response
            mock_get.return_value.status_code = 200

            gateway = LightspeedGateway(api_token='test_token', account_domain='test')

            # Act
            results = list(gateway._paginate('products'))

            # Assert
            assert len(results) == 2
            assert results[0]['id'] == '1'
            assert results[1]['id'] == '2'
            assert mock_get.call_count == 1

    def test_paginate_multiple_pages(self) -> None:
        """Test pagination across multiple pages."""
        # Arrange
        from src.infra.lightspeed_client import LightspeedGateway

        page1 = {'data': [{'id': str(i)} for i in range(250)]}
        page2 = {'data': [{'id': str(i)} for i in range(250, 400)]}
        page3 = {'data': []}  # Empty page indicates end

        with patch('src.infra.lightspeed_client.requests.Session.get') as mock_get:
            mock_get.return_value.json.side_effect = [page1, page2, page3]
            mock_get.return_value.status_code = 200

            gateway = LightspeedGateway(api_token='test_token', account_domain='test')

            # Act
            results = list(gateway._paginate('products'))

            # Assert
            assert len(results) == 400
            assert mock_get.call_count == 3

            # Verify pagination parameters
            calls = mock_get.call_args_list
            assert calls[0][1]['params']['offset'] == 0
            assert calls[1][1]['params']['offset'] == 250
            assert calls[2][1]['params']['offset'] == 500

    def test_paginate_empty_results(self) -> None:
        """Test pagination with no results."""
        from src.infra.lightspeed_client import LightspeedGateway

        with patch('src.infra.lightspeed_client.requests.Session.get') as mock_get:
            mock_get.return_value.json.return_value = {'data': []}
            mock_get.return_value.status_code = 200

            gateway = LightspeedGateway(api_token='test_token', account_domain='test')

            # Act
            results = list(gateway._paginate('products'))

            # Assert
            assert len(results) == 0
            assert mock_get.call_count == 1


class TestLightspeedGatewayRetry:
    """Test retry logic with exponential backoff."""

    def test_retry_on_rate_limit_429(self) -> None:
        """Test automatic retry when hitting rate limit (429 status)."""
        from src.infra.lightspeed_client import LightspeedGateway

        with patch('src.infra.lightspeed_client.requests.Session.get') as mock_get:
            # First call: rate limited
            rate_limit_response = Mock()
            rate_limit_response.status_code = 429
            rate_limit_response.headers = {'Retry-After': '2'}
            rate_limit_response.raise_for_status.side_effect = requests.exceptions.HTTPError()

            # Second call: success
            success_response = Mock()
            success_response.status_code = 200
            success_response.json.return_value = {'data': [{'id': '1'}]}

            mock_get.side_effect = [rate_limit_response, success_response]

            with patch('time.sleep') as mock_sleep:
                gateway = LightspeedGateway(api_token='test_token', account_domain='test')

                # Act
                result = gateway._make_request_with_retry('products')

                # Assert
                assert result is not None
                assert len(result['data']) == 1
                assert mock_get.call_count == 2
                mock_sleep.assert_called_once_with(2)  # Retry-After header

    def test_exponential_backoff_on_transient_errors(self) -> None:
        """Test exponential backoff for transient errors."""
        from src.infra.lightspeed_client import LightspeedGateway

        with patch('src.infra.lightspeed_client.requests.Session.get') as mock_get:
            # Simulate transient failures
            mock_get.side_effect = [
                requests.exceptions.ConnectionError(),
                requests.exceptions.Timeout(),
                Mock(status_code=200, json=lambda: {'data': [{'id': '1'}]})
            ]

            with patch('time.sleep') as mock_sleep:
                gateway = LightspeedGateway(
                    api_token='test_token',
                    account_domain='test',
                    max_retries=3
                )

                # Act
                result = gateway._make_request_with_retry('products')

                # Assert
                assert result is not None
                assert mock_get.call_count == 3

                # Verify exponential backoff: 1s, 2s
                assert mock_sleep.call_count == 2
                assert mock_sleep.call_args_list[0][0][0] == 1
                assert mock_sleep.call_args_list[1][0][0] == 2

    def test_max_retries_exceeded(self) -> None:
        """Test that retries stop after max attempts."""
        from src.infra.exceptions import LightspeedAPIError
        from src.infra.lightspeed_client import LightspeedGateway

        with patch('src.infra.lightspeed_client.requests.Session.get') as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError()

            with patch('time.sleep'):
                gateway = LightspeedGateway(
                    api_token='test_token',
                    account_domain='test',
                    max_retries=3
                )

                # Act & Assert
                with pytest.raises(LightspeedAPIError):
                    gateway._make_request_with_retry('products')

                assert mock_get.call_count == 3


class TestLightspeedGatewayRateLimiting:
    """Test rate limiting behavior."""

    def test_rate_limit_delay_between_requests(self) -> None:
        """Test that gateway enforces delay between requests."""
        from src.infra.lightspeed_client import LightspeedGateway

        with patch('src.infra.lightspeed_client.requests.Session.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = {'data': []}

            with patch('time.sleep') as mock_sleep:
                gateway = LightspeedGateway(
                    api_token='test_token',
                    account_domain='test',
                    rate_limit_delay=0.5
                )

                # Act - make multiple requests
                gateway._make_request_with_retry('products')
                gateway._make_request_with_retry('inventory')

                # Assert - delay was enforced
                assert mock_sleep.call_count >= 2  # Once per request
                assert all(call[0][0] == 0.5 for call in mock_sleep.call_args_list)

    def test_respects_retry_after_header(self) -> None:
        """Test that Retry-After header overrides default delay."""
        from src.infra.lightspeed_client import LightspeedGateway

        with patch('src.infra.lightspeed_client.requests.Session.get') as mock_get:
            rate_limit = Mock()
            rate_limit.status_code = 429
            rate_limit.headers = {'Retry-After': '10'}

            success = Mock()
            success.status_code = 200
            success.json.return_value = {'data': []}

            mock_get.side_effect = [rate_limit, success]

            with patch('time.sleep') as mock_sleep:
                gateway = LightspeedGateway(api_token='test_token', account_domain='test')

                # Act
                gateway._make_request_with_retry('products')

                # Assert - should sleep for Retry-After duration
                assert any(call[0][0] == 10 for call in mock_sleep.call_args_list)


class TestLightspeedGatewayIntegration:
    """Integration tests for Gateway pattern."""

    def test_get_products_with_variants(self) -> None:
        """Test fetching products with variants through gateway."""
        from src.infra.lightspeed_client import LightspeedGateway

        with patch('src.infra.lightspeed_client.requests.Session.get') as mock_get:
            # Mock product response
            products_response = {
                'data': [
                    {'id': '1', 'name': 'Air Jordan 1', 'sku': 'AJ1'}
                ]
            }

            # Mock variants response
            variants_response = {
                'data': [
                    {'id': '1-1', 'sku': 'AJ1-10', 'size': '10'},
                    {'id': '1-2', 'sku': 'AJ1-11', 'size': '11'}
                ]
            }

            mock_get.return_value.status_code = 200
            mock_get.return_value.json.side_effect = [products_response, variants_response]

            gateway = LightspeedGateway(api_token='test_token', account_domain='test')

            # Act
            products = gateway.get_products(include_variants=True)

            # Assert
            assert len(products) == 1
            assert products[0]['name'] == 'Air Jordan 1'
            assert 'variants' in products[0]
            assert len(products[0]['variants']) == 2

    def test_gateway_hides_api_complexity(self) -> None:
        """Test that gateway abstracts away API complexity from consumers."""
        from src.infra.lightspeed_client import LightspeedGateway

        # Consumer shouldn't need to know about pagination, retries, rate limits
        gateway = LightspeedGateway(api_token='test_token', account_domain='test')

        # These methods should be simple to use
        assert hasattr(gateway, 'get_products')
        assert hasattr(gateway, 'get_inventory')
        assert hasattr(gateway, 'get_sales')

        # Internal complexity should be hidden
        assert hasattr(gateway, '_paginate')
        assert hasattr(gateway, '_make_request_with_retry')
        assert hasattr(gateway, '_handle_rate_limit')


class TestLightspeedGatewayErrorHandling:
    """Test error handling and recovery."""

    def test_authentication_error(self) -> None:
        """Test handling of authentication errors."""
        from src.infra.exceptions import LightspeedAuthError
        from src.infra.lightspeed_client import LightspeedGateway

        with patch('src.infra.lightspeed_client.requests.Session.get') as mock_get:
            mock_get.return_value.status_code = 401
            mock_get.return_value.raise_for_status.side_effect = requests.exceptions.HTTPError()

            gateway = LightspeedGateway(api_token='invalid_token', account_domain='test')

            # Act & Assert
            with pytest.raises(LightspeedAuthError):
                gateway.get_products()

    def test_not_found_error(self) -> None:
        """Test handling of 404 errors."""
        from src.infra.lightspeed_client import LightspeedGateway

        with patch('src.infra.lightspeed_client.requests.Session.get') as mock_get:
            mock_get.return_value.status_code = 404
            mock_get.return_value.json.return_value = {'error': 'Not found'}

            gateway = LightspeedGateway(api_token='test_token', account_domain='test')

            # Act
            result = gateway.get_product_by_id('nonexistent')

            # Assert
            assert result is None

    def test_server_error_with_retry(self) -> None:
        """Test that server errors (5xx) trigger retry logic."""
        from src.infra.lightspeed_client import LightspeedGateway

        with patch('src.infra.lightspeed_client.requests.Session.get') as mock_get:
            error_response = Mock()
            error_response.status_code = 500
            error_response.raise_for_status.side_effect = requests.exceptions.HTTPError()

            success_response = Mock()
            success_response.status_code = 200
            success_response.json.return_value = {'data': []}

            mock_get.side_effect = [error_response, success_response]

            with patch('time.sleep'):
                gateway = LightspeedGateway(api_token='test_token', account_domain='test')

                # Act
                result = gateway._make_request_with_retry('products')

                # Assert
                assert result is not None
                assert mock_get.call_count == 2


# Fixtures for Lightspeed tests
@pytest.fixture
def mock_lightspeed_response():
    """Mock successful Lightspeed API response."""
    return {
        'data': [
            {
                'id': '1001',
                'sku': 'TEST-SKU-001',
                'name': 'Test Product',
                'category': 'Test Category',
                'retail_price': 99.99,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        ],
        'meta': {
            'total': 1,
            'per_page': 250,
            'current_page': 1
        }
    }


@pytest.fixture
def lightspeed_gateway():
    """Create a Lightspeed gateway instance for testing."""
    from src.infra.lightspeed_client import LightspeedGateway
    return LightspeedGateway(
        api_token='test_token',
        account_domain='test.domain',
        rate_limit_delay=0.01,  # Fast for tests
        max_retries=3
    )
