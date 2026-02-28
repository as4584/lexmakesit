from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Product:
	sku: str
	name: str
	qty_on_hand: int = 0
	qty_sold: int = 0
	category: str | None = None
	retail_price: float | None = None


@dataclass
class Sale:
	sku: str
	quantity: int
	date: datetime
	unit_price: float | None = None
	sale_hash: str | None = None
