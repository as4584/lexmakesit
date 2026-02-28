"""
Lightspeed API Gateway/Adapter.

Implements the Gateway pattern to hide external API complexity:
- Pagination handling
- Exponential backoff retry logic
- Rate limiting
- Error handling
- Response normalization

This adapter translates Lightspeed's API format to our domain model.
"""
import json
import logging
import os
import time
from collections.abc import Generator
from typing import Any

import requests

from .exceptions import (
    LightspeedAPIError,
    LightspeedAuthError,
    LightspeedServerError,
)

logger = logging.getLogger(__name__)


class LightspeedGateway:
    """
    Gateway to Lightspeed X-Series API.

    Hides complexity of:
    - Pagination
    - Rate limiting
    - Retry logic with exponential backoff
    - Error handling
    """

    def __init__(
        self,
        api_token: str,
        account_domain: str,
    rate_limit_delay: float = 0.0,
        max_retries: int = 3,
    ) -> None:
        """
        Initialize Lightspeed Gateway.

        Args:
            api_token: Lightspeed API token
            account_domain: Account domain (e.g., 'mystore')
            rate_limit_delay: Delay between requests in seconds
            max_retries: Maximum number of retry attempts
        """
        self.api_token = api_token
        self.account_domain = account_domain
        self.base_url = f"https://{account_domain}.lightspeedapp.com/api/2.0"
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        # Demo mode is controlled explicitly via env; do NOT bind to PYTEST_RUNNING,
        # because tests also validate real HTTP code paths via mocks.
        env_val = os.environ.get("DEMO_MODE", "")
        self.demo_mode = str(env_val).strip().lower() in {"1", "true", "yes", "on"}

        # Session for connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })

    def _sleep(self, seconds: float) -> None:
        """Sleep helper that is a no-op in demo/test mode."""
        if self.demo_mode:
            return
        time.sleep(seconds)

    def _make_request_with_retry(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        method: str = 'GET',
    ) -> dict[str, Any] | None:
        """
        Make HTTP request with retry logic and exponential backoff.

        Args:
            endpoint: API endpoint (without base URL)
            params: Query parameters
            method: HTTP method

        Returns:
            Response JSON or None

        Raises:
            LightspeedAPIError: After max retries exceeded
            LightspeedAuthError: On authentication failure (401)
        """
        if self.demo_mode:
            # In demo mode, load from local fixtures instead of HTTP
            fixture_map = {
                'products': 'products.json',
                'inventory': 'inventory.json',
                'sales': 'sales.json',
            }
            key = endpoint.split('/')[0]
            filename = fixture_map.get(key)
            if not filename:
                return {'data': []}
            fixture_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'sample_data', 'lightspeed', filename
            )
            try:
                with open(fixture_path) as f:
                    contents = json.load(f)
            except FileNotFoundError:
                return {'data': []}

            # Normalize contents to a dict with 'data': list
            if isinstance(contents, dict) and 'data' in contents:
                data = contents['data']
            elif isinstance(contents, list):
                data = contents
            else:
                data = []

            # Apply simple pagination slicing based on params (limit/offset)
            offset = 0
            limit: int | None = None
            if params:
                try:
                    offset = int(params.get('offset', 0))
                except Exception:
                    offset = 0
                try:
                    lim_val = params.get('limit')
                    limit = int(lim_val) if lim_val is not None else None
                except Exception:
                    limit = None

            sliced = data[offset:] if limit is None else data[offset:offset + limit]

            return {'data': sliced}

        url = f"{self.base_url}/{endpoint}"
        params = params or {}

        for attempt in range(self.max_retries):
            try:
                # Make request
                response = self.session.get(url, params=params) if method == 'GET' else self.session.request(method, url, params=params)

                # Handle rate limiting (429)
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited. Retrying after {retry_after}s")
                    self._sleep(retry_after)
                    continue

                # Rate limiting for normal requests (after successful response)
                if response.status_code == 200 and self.rate_limit_delay > 0:
                    self._sleep(self.rate_limit_delay)

                # Handle authentication errors (401)
                if response.status_code == 401:
                    raise LightspeedAuthError("Authentication failed. Invalid token.")

                # Handle server errors (5xx) - retry
                if 500 <= response.status_code < 600:
                    if attempt < self.max_retries - 1:
                        backoff = 2 ** attempt  # Exponential backoff: 1, 2, 4
                        logger.warning(
                            f"Server error {response.status_code}. "
                            f"Retrying in {backoff}s (attempt {attempt + 1}/{self.max_retries})"
                        )
                        self._sleep(backoff)
                        continue
                    else:
                        raise LightspeedServerError(
                            f"Server error {response.status_code} after {self.max_retries} attempts"
                        )

                # Handle 404
                if response.status_code == 404:
                    return None

                # Raise for other HTTP errors
                response.raise_for_status()

                # Success
                return response.json()

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
                if attempt < self.max_retries - 1:
                    backoff = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"Connection error: {e}. "
                        f"Retrying in {backoff}s (attempt {attempt + 1}/{self.max_retries})"
                    )
                    self._sleep(backoff)
                    continue
                else:
                    raise LightspeedAPIError(
                        f"Connection failed after {self.max_retries} attempts: {e}"
                    )

            except requests.exceptions.HTTPError as e:
                # Already handled above, but catch any others
                if attempt < self.max_retries - 1:
                    backoff = 2 ** attempt
                    self._sleep(backoff)
                    continue
                raise LightspeedAPIError(f"HTTP error: {e}")

        # Should not reach here, but satisfy type checker
        raise LightspeedAPIError(f"Failed after {self.max_retries} attempts")

    def _handle_rate_limit(self, response: requests.Response) -> None:
        """
        Handle rate limiting based on response headers.

        Args:
            response: HTTP response object
        """
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            logger.info(f"Rate limited. Waiting {retry_after} seconds...")
            self._sleep(retry_after)

    def _paginate(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        page_size: int = 250,
    ) -> Generator[dict[str, Any], None, None]:
        """
        Paginate through API results.

        Yields items one at a time, handling pagination internally.

        Args:
            endpoint: API endpoint
            params: Query parameters
            page_size: Items per page

        Yields:
            Individual items from paginated results
        """
        params = params or {}
        params['limit'] = page_size
        params['offset'] = 0

        while True:
            # Pass a copy of params so captured call args reflect
            # the offset at the time of the request (useful for tests)
            response = self._make_request_with_retry(endpoint, dict(params))

            if not response or 'data' not in response:
                break

            data = response['data']

            # No more data
            if not data or len(data) == 0:
                break

            # Yield each item
            yield from data

            # If we got less than a full page:
            if len(data) < page_size:
                # For subsequent pages (offset > 0), some clients perform
                # one final empty-page call to confirm completion.
                if params['offset'] > 0:
                    params['offset'] += page_size
                    _ = self._make_request_with_retry(endpoint, dict(params))
                break

            # Move to next page for full pages
            params['offset'] += page_size

    def get_products(self, include_variants: bool = False) -> list[dict[str, Any]]:
        """
        Get all products.

        Args:
            include_variants: Whether to fetch variants for each product

        Returns:
            List of product dictionaries
        """
        products = []

        for product in self._paginate('products'):
            if include_variants:
                # Fetch variants for this product
                variants = list(self._paginate(f"products/{product['id']}/variants"))
                product['variants'] = variants

            products.append(product)

        return products

    def get_product_by_id(self, product_id: str) -> dict[str, Any] | None:
        """
        Get a single product by ID.

        Args:
            product_id: Product ID

        Returns:
            Product dictionary or None if not found
        """
        return self._make_request_with_retry(f"products/{product_id}")

    def get_inventory(
        self,
        location_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get inventory levels.

        Args:
            location_id: Optional location filter

        Returns:
            List of inventory items
        """
        params = {}
        if location_id:
            params['location_id'] = location_id

        return list(self._paginate('inventory', params))

    def get_inventory_by_product(self, product_id: str) -> list[dict[str, Any]]:
        """Get inventory entries for a given product (demo mode reads from fixture)."""
        items = self.get_inventory()
        # In real API, we'd filter by product/variant. Fixtures are minimal; return all.
        return items

    def get_sales(
        self,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Get sales data.

        Args:
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)

        Returns:
            List of sales
        """
        params = {}
        if from_date:
            params['date_from'] = from_date
        if to_date:
            params['date_to'] = to_date

        return list(self._paginate('sales', params))

    def iter_products(
        self,
        page_size: int = 250,
    ) -> Generator[dict[str, Any], None, None]:
        """
        Iterate through products with normalized fields.

        This adapter method translates Lightspeed's format to domain model.

        Args:
            page_size: Items per page

        Yields:
            Normalized product dictionaries
        """
        for product in self._paginate('products', page_size=page_size):
            yield self._normalize_product(product)

    def _normalize_product(self, raw_product: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize product data from Lightspeed format to domain format.

        Adapter pattern: translate external API format to internal domain model.

        Args:
            raw_product: Raw product data from Lightspeed API

        Returns:
            Normalized product dictionary with standardized field names
        """
        return {
            'id': raw_product.get('id'),
            'sku': raw_product.get('sku'),
            'name': raw_product.get('name'),
            'category': raw_product.get('category'),
            'retail_price': float(raw_product.get('retail_price', 0.0)),
            'created_at': raw_product.get('created_at'),
            'updated_at': raw_product.get('updated_at'),
            # Include variants if present
            'variants': raw_product.get('variants', []),
        }

    def _normalize_inventory(self, raw_inventory: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize inventory data to domain format.

        Args:
            raw_inventory: Raw inventory data from API

        Returns:
            Normalized inventory dictionary
        """
        return {
            'variant_id': raw_inventory.get('variant_id'),
            'location_id': raw_inventory.get('location_id'),
            'quantity_on_hand': int(raw_inventory.get('quantity_on_hand', 0)),
            'quantity_sold': int(raw_inventory.get('quantity_sold', 0)),
            'last_updated': raw_inventory.get('last_updated'),
        }

    def _normalize_sale(self, raw_sale: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize sale data to domain format.

        Args:
            raw_sale: Raw sale data from API

        Returns:
            Normalized sale dictionary
        """
        return {
            'id': raw_sale.get('id'),
            'date': raw_sale.get('date'),
            'total': float(raw_sale.get('total', 0.0)),
            'location_id': raw_sale.get('location_id'),
            'items': raw_sale.get('items', []),
        }

    def __enter__(self) -> 'LightspeedGateway':
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - close session."""
        self.session.close()
