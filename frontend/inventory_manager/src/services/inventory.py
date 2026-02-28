"""
Compatibility shim to preserve legacy import path `services.inventory`.
Re-exports InventoryService from `src.domain.inventory`.
"""
from src.domain.inventory import InventoryService

__all__ = ["InventoryService"]
