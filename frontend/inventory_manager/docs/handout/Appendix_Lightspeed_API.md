# Appendix – Lightspeed API

## Official documentation
- https://x-series-support.lightspeedhq.com/hc/en-us
- https://x-series-support.lightspeedhq.com/hc/en-us/articles/4404455214105-Getting-started-with-the-API

## Planned endpoints
- GET /products (with variants)
- GET /inventory
- GET /sales?from&to

## Field mapping
- Product.id → ItemID
- Product.sku → SKU
- Product.name → Name
- Product.category → Category
- Variant attributes → Color, Size
- Product.barcode → Barcode
- Product.retail_price → RetailPrice
- Inventory.quantity_on_hand → QtyOnHand
- Inventory.quantity_sold → QtySold
- Inventory.location_id → Location
- Inventory.last_updated → LastUpdated
