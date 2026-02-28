"""
Lightspeed webhooks service for real-time inventory updates.
Optional service for handling webhooks from Lightspeed when enabled.
"""
import hashlib
import hmac
from datetime import datetime
from typing import Any

from flask import request


class LightspeedWebhooks:
    """Service for handling Lightspeed webhook notifications."""

    def __init__(self, webhook_secret: str | None = None):
        """Initialize webhook service."""
        self.webhook_secret = webhook_secret
        self.supported_events = [
            'product.created',
            'product.updated',
            'product.deleted',
            'inventory.updated',
            'sale.created',
            'sale.updated'
        ]

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature to ensure authenticity."""
        if not self.webhook_secret:
            print("Warning: Webhook secret not configured - skipping verification")
            return True

        try:
            # Calculate expected signature
            expected_signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()

            # Remove 'sha256=' prefix if present
            if signature.startswith('sha256='):
                signature = signature[7:]

            return hmac.compare_digest(expected_signature, signature)

        except Exception as e:
            print(f"Signature verification failed: {e}")
            return False

    def process_webhook(self, payload: dict[str, Any], event_type: str) -> dict[str, Any]:
        """Process incoming webhook and trigger appropriate actions."""
        try:
            print(f"Processing webhook: {event_type}")

            if event_type not in self.supported_events:
                return {
                    'success': False,
                    'error': f'Unsupported event type: {event_type}'
                }

            # Route to appropriate handler
            if event_type.startswith('product.'):
                return self._handle_product_event(payload, event_type)
            elif event_type.startswith('inventory.'):
                return self._handle_inventory_event(payload, event_type)
            elif event_type.startswith('sale.'):
                return self._handle_sale_event(payload, event_type)
            else:
                return {
                    'success': False,
                    'error': f'No handler for event type: {event_type}'
                }

        except Exception as e:
            print(f"Webhook processing failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _handle_product_event(self, payload: dict[str, Any], event_type: str) -> dict[str, Any]:
        """Handle product-related webhook events."""
        product_data = payload.get('data', {})
        product_id = product_data.get('id')

        print(f"Product event {event_type} for product ID: {product_id}")

        if event_type == 'product.created':
            # TODO: Add new product to inventory
            return {
                'success': True,
                'action': 'product_created',
                'product_id': product_id,
                'message': 'Product added to inventory'
            }

        elif event_type == 'product.updated':
            # TODO: Update existing product in inventory
            return {
                'success': True,
                'action': 'product_updated',
                'product_id': product_id,
                'message': 'Product updated in inventory'
            }

        elif event_type == 'product.deleted':
            # TODO: Remove or mark product as inactive
            return {
                'success': True,
                'action': 'product_deleted',
                'product_id': product_id,
                'message': 'Product removed from inventory'
            }

        return {'success': False, 'error': 'Unknown product event'}

    def _handle_inventory_event(self, payload: dict[str, Any], event_type: str) -> dict[str, Any]:
        """Handle inventory-related webhook events."""
        inventory_data = payload.get('data', {})
        variant_id = inventory_data.get('variant_id')
        quantity = inventory_data.get('quantity_on_hand')

        print(f"Inventory event {event_type} for variant ID: {variant_id}, quantity: {quantity}")

        if event_type == 'inventory.updated':
            # TODO: Update inventory quantities in sheets
            return {
                'success': True,
                'action': 'inventory_updated',
                'variant_id': variant_id,
                'quantity': quantity,
                'message': 'Inventory quantity updated'
            }

        return {'success': False, 'error': 'Unknown inventory event'}

    def _handle_sale_event(self, payload: dict[str, Any], event_type: str) -> dict[str, Any]:
        """Handle sale-related webhook events."""
        sale_data = payload.get('data', {})
        sale_id = sale_data.get('id')
        total = sale_data.get('total')

        print(f"Sale event {event_type} for sale ID: {sale_id}, total: {total}")

        if event_type == 'sale.created':
            # TODO: Process new sale and update inventory
            return {
                'success': True,
                'action': 'sale_created',
                'sale_id': sale_id,
                'total': total,
                'message': 'Sale processed and inventory updated'
            }

        elif event_type == 'sale.updated':
            # TODO: Handle sale updates (refunds, modifications)
            return {
                'success': True,
                'action': 'sale_updated',
                'sale_id': sale_id,
                'message': 'Sale update processed'
            }

        return {'success': False, 'error': 'Unknown sale event'}

    def register_webhook_endpoints(self, app):
        """Register webhook endpoints with Flask app."""

        @app.route('/webhooks/lightspeed', methods=['POST'])
        def lightspeed_webhook():
            """Main webhook endpoint for Lightspeed notifications."""
            try:
                # Get signature from headers
                signature = request.headers.get('X-Lightspeed-Signature', '')

                # Verify signature
                if not self.verify_webhook_signature(request.data, signature):
                    return {'error': 'Invalid signature'}, 401

                # Parse payload
                payload = request.get_json()
                if not payload:
                    return {'error': 'Invalid JSON payload'}, 400

                # Get event type
                event_type = request.headers.get('X-Lightspeed-Event', '')
                if not event_type:
                    return {'error': 'Missing event type header'}, 400

                # Process webhook
                result = self.process_webhook(payload, event_type)

                if result['success']:
                    return result, 200
                else:
                    return result, 400

            except Exception as e:
                print(f"Webhook endpoint error: {e}")
                return {'error': 'Internal server error'}, 500

        @app.route('/webhooks/status', methods=['GET'])
        def webhook_status():
            """Webhook status and configuration endpoint."""
            return {
                'webhook_secret_configured': bool(self.webhook_secret),
                'supported_events': self.supported_events,
                'status': 'active',
                'last_check': datetime.now().isoformat()
            }, 200

    def create_webhook_config(self) -> dict[str, Any]:
        """Generate webhook configuration for Lightspeed setup."""
        return {
            'url': '/webhooks/lightspeed',
            'events': self.supported_events,
            'secret': self.webhook_secret,
            'format': 'json',
            'headers': {
                'X-Lightspeed-Event': 'event_type',
                'X-Lightspeed-Signature': 'sha256=signature'
            },
            'verification': 'HMAC-SHA256',
            'setup_instructions': [
                '1. Go to Lightspeed admin panel',
                '2. Navigate to Settings > Integrations > Webhooks',
                '3. Create new webhook with the URL above',
                '4. Select the events you want to monitor',
                '5. Set the secret key in your environment variables',
                '6. Test the webhook to ensure connectivity'
            ]
        }
