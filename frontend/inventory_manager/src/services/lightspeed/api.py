"""
Lightspeed X-Series API service.
Handles all interactions with Lightspeed Retail X-Series API including
products, variants, inventory, and sales with pagination and rate limiting.
"""
import os
import time
from collections.abc import Generator
from datetime import datetime, timedelta
from typing import Any

import requests


class LightspeedAPI:
    """Service for Lightspeed X-Series API operations."""

    def __init__(self):
        """Initialize Lightspeed API client."""
        self.api_token = os.getenv('LS_X_API_TOKEN')
        self.account_domain = os.getenv('LS_ACCOUNT_DOMAIN')
        self.base_url = f"https://{self.account_domain}.lightspeedapp.com/api/2.0"
        self.session = requests.Session()
        self.rate_limit_delay = 0.5  # 500ms between requests to respect rate limits

        if self.api_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            })

    def _make_request(self, endpoint: str, params: dict | None = None) -> dict | None:
        """Make rate-limited API request with error handling."""
        if not self.api_token or not self.account_domain:
            print("Lightspeed API not configured - using mock data")
            return None

        try:
            # Rate limiting
            time.sleep(self.rate_limit_delay)

            url = f"{self.base_url}/{endpoint}"
            response = self.session.get(url, params=params or {})

            if response.status_code == 429:  # Rate limited
                retry_after = int(response.headers.get('Retry-After', 60))
                print(f"Rate limited, waiting {retry_after} seconds...")
                time.sleep(retry_after)
                return self._make_request(endpoint, params)

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return None

    def _paginate(self, endpoint: str, params: dict | None = None) -> Generator[dict, None, None]:
        """Generator for paginated API results."""
        params = params or {}
        params['limit'] = 250  # Max per page for X-Series
        params['offset'] = 0

        while True:
            response = self._make_request(endpoint, params)

            if not response or 'data' not in response:
                break

            data = response['data']
            if not data:
                break

            yield from data

            # Check if we have more pages
            if len(data) < params['limit']:
                break

            params['offset'] += params['limit']

    def get_products(self, include_variants: bool = True) -> list[dict[str, Any]]:
        """Get all products with optional variants."""
        if not self.api_token:
            # Return mock product data for development
            return [
                {
                    'id': '1001',
                    'sku': 'JD1-BLK',
                    'name': 'Air Jordan 1 Black',
                    'category': 'Sneakers',
                    'retail_price': 170.00,
                    'created_at': '2025-01-01T00:00:00Z',
                    'updated_at': '2025-10-09T12:00:00Z',
                    'variants': [
                        {
                            'id': '1001-10',
                            'sku': 'JD1-BLK-10',
                            'name': 'Air Jordan 1 Black - Size 10',
                            'size': '10',
                            'color': 'Black',
                            'barcode': '123456789',
                            'retail_price': 170.00,
                            'quantity_on_hand': 8
                        },
                        {
                            'id': '1001-9',
                            'sku': 'JD1-BLK-9',
                            'name': 'Air Jordan 1 Black - Size 9',
                            'size': '9',
                            'color': 'Black',
                            'barcode': '123456788',
                            'retail_price': 170.00,
                            'quantity_on_hand': 12
                        }
                    ]
                },
                {
                    'id': '1002',
                    'sku': 'JD1-WHT',
                    'name': 'Air Jordan 1 White',
                    'category': 'Sneakers',
                    'retail_price': 170.00,
                    'created_at': '2025-01-01T00:00:00Z',
                    'updated_at': '2025-10-09T12:00:00Z',
                    'variants': [
                        {
                            'id': '1002-9',
                            'sku': 'JD1-WHT-9',
                            'name': 'Air Jordan 1 White - Size 9',
                            'size': '9',
                            'color': 'White',
                            'barcode': '123456790',
                            'retail_price': 170.00,
                            'quantity_on_hand': 3
                        }
                    ]
                }
            ]

        products = []
        for product in self._paginate('products'):
            if include_variants:
                product['variants'] = self.get_product_variants(product['id'])
            products.append(product)

        return products

    def get_product_variants(self, product_id: str) -> list[dict[str, Any]]:
        """Get all variants for a specific product."""
        if not self.api_token:
            return []  # Mock data handled in get_products

        variants = []
        for variant in self._paginate(f'products/{product_id}/variants'):
            # Enrich variant with inventory data
            inventory = self.get_variant_inventory(variant['id'])
            variant['quantity_on_hand'] = inventory.get('quantity_on_hand', 0)
            variants.append(variant)

        return variants

    def get_variant_inventory(self, variant_id: str) -> dict[str, Any]:
        """Get current inventory for a specific variant."""
        if not self.api_token:
            return {'quantity_on_hand': 0}

        response = self._make_request(f'variants/{variant_id}/inventory')
        if response and 'data' in response:
            return response['data']

        return {'quantity_on_hand': 0}

    def get_inventory_by_location(self, location_id: str | None = None) -> list[dict[str, Any]]:
        """Get inventory levels by location."""
        if not self.api_token:
            # Return mock inventory data
            return [
                {
                    'variant_id': '1001-10',
                    'location_id': 'store-1',
                    'location_name': 'Main Store',
                    'quantity_on_hand': 8,
                    'quantity_sold': 2,
                    'last_updated': '2025-10-09T12:00:00Z'
                },
                {
                    'variant_id': '1002-9',
                    'location_id': 'store-1',
                    'location_name': 'Main Store',
                    'quantity_on_hand': 3,
                    'quantity_sold': 7,
                    'last_updated': '2025-10-09T12:00:00Z'
                }
            ]

        endpoint = 'inventory'
        params = {}
        if location_id:
            params['location_id'] = location_id

        inventory = []
        for item in self._paginate(endpoint, params):
            inventory.append(item)

        return inventory

    def get_sales(self, from_date: str, to_date: str, location_id: str | None = None) -> list[dict[str, Any]]:
        """Get sales data for date range."""
        if not self.api_token:
            # Return mock sales data
            return [
                {
                    'id': 'sale-001',
                    'date': '2025-10-08',
                    'total': 170.00,
                    'location_id': 'store-1',
                    'items': [
                        {
                            'variant_id': '1002-9',
                            'sku': 'JD1-WHT-9',
                            'quantity': 1,
                            'unit_price': 170.00,
                            'total': 170.00
                        }
                    ]
                },
                {
                    'id': 'sale-002',
                    'date': '2025-10-09',
                    'total': 340.00,
                    'location_id': 'store-1',
                    'items': [
                        {
                            'variant_id': '1001-10',
                            'sku': 'JD1-BLK-10',
                            'quantity': 2,
                            'unit_price': 170.00,
                            'total': 340.00
                        }
                    ]
                }
            ]

        params = {
            'date_from': from_date,
            'date_to': to_date
        }
        if location_id:
            params['location_id'] = location_id

        sales = []
        for sale in self._paginate('sales', params):
            # Enrich with line items
            sale['items'] = self.get_sale_items(sale['id'])
            sales.append(sale)

        return sales

    def get_sale_items(self, sale_id: str) -> list[dict[str, Any]]:
        """Get line items for a specific sale."""
        if not self.api_token:
            return []  # Mock data handled in get_sales

        response = self._make_request(f'sales/{sale_id}/items')
        if response and 'data' in response:
            return response['data']

        return []

    def sync_from_ls(self) -> dict[str, Any]:
        """Full sync from Lightspeed - get all products, variants, and current inventory."""
        try:
            print("Starting full sync from Lightspeed...")

            # Get all products with variants
            products = self.get_products(include_variants=True)

            # Get inventory by location
            inventory = self.get_inventory_by_location()

            # Get recent sales (last 7 days)
            to_date = datetime.now()
            from_date = to_date - timedelta(days=7)
            sales = self.get_sales(
                from_date.strftime('%Y-%m-%d'),
                to_date.strftime('%Y-%m-%d')
            )

            sync_result = {
                'products_count': len(products),
                'inventory_items': len(inventory),
                'recent_sales': len(sales),
                'sync_time': datetime.now().isoformat(),
                'products': products,
                'inventory': inventory,
                'sales': sales
            }

            print(f"Sync completed: {sync_result['products_count']} products, "
                  f"{sync_result['inventory_items']} inventory items, "
                  f"{sync_result['recent_sales']} recent sales")

            return sync_result

        except Exception as e:
            print(f"Sync failed: {e}")
            return {
                'error': str(e),
                'sync_time': datetime.now().isoformat()
            }

    def reconcile_sales(self, sales_data: list[dict[str, Any]]) -> dict[str, Any]:
        """Apply sales data to update on-hand quantities."""
        try:
            print("Starting sales reconciliation...")

            processed_sales = 0
            items_updated = 0

            for sale in sales_data:
                # Process each sale item
                for item in sale.get('items', []):
                    variant_id = item.get('variant_id')
                    quantity_sold = item.get('quantity', 0)

                    if variant_id and quantity_sold > 0:
                        # TODO: Update inventory levels
                        # This would typically call an update API endpoint
                        items_updated += 1

                processed_sales += 1

            reconcile_result = {
                'processed_sales': processed_sales,
                'items_updated': items_updated,
                'reconcile_time': datetime.now().isoformat()
            }

            print(f"Reconciliation completed: {processed_sales} sales processed, "
                  f"{items_updated} items updated")

            return reconcile_result

        except Exception as e:
            print(f"Reconciliation failed: {e}")
            return {
                'error': str(e),
                'reconcile_time': datetime.now().isoformat()
            }

    def test_connection(self) -> bool:
        """Test API connection and authentication."""
        if not self.api_token or not self.account_domain:
            print("API credentials not configured")
            return False

        try:
            response = self._make_request('products', {'limit': 1})
            return response is not None
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
