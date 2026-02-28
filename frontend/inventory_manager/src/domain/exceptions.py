class NegativeInventoryError(Exception):
    """Raised when an operation would reduce inventory below zero and negatives are not allowed."""


class InvalidInventorySchemaError(Exception):
    """Raised when the inventory DataFrame does not contain required columns."""
