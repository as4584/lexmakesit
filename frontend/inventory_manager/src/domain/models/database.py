"""
Database models for Hype Resale Item Manager.
SQLAlchemy ORM models for products, variants, consignors, sales, and reserves.
"""
import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class AuthStatus(enum.Enum):
    """Authentication status for variants."""
    VERIFIED = "verified"
    UNIDENTIFIED = "unidentified"
    PENDING = "pending"
    NOT_REQUIRED = "not_required"


class Condition(enum.Enum):
    """Item condition grades."""
    DEADSTOCK = "deadstock"  # Brand new, unworn
    VNDS = "vnds"  # Very near deadstock
    NEW = "new"  # New with defects
    EXCELLENT = "excellent"  # 9/10
    GOOD = "good"  # 7-8/10
    FAIR = "fair"  # 5-6/10
    POOR = "poor"  # Below 5/10


class ReserveStatus(enum.Enum):
    """Reserve/hold status."""
    ACTIVE = "active"
    EXPIRED = "expired"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SaleChannel(enum.Enum):
    """Sales channels."""
    IN_STORE = "in_store"
    ONLINE = "online"
    MARKETPLACE = "marketplace"
    WHOLESALE = "wholesale"


class Product(Base):
    """
    Product master record (brand + model + colorway).
    Follows Lightspeed matrix variant model.
    """
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    brand = Column(String(100), nullable=False, index=True)
    model = Column(String(200), nullable=False, index=True)
    colorway = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False, index=True)  # Sneakers, Apparel, Accessories
    season = Column(String(20))  # FW23, SS24, etc.
    thumbnail_url = Column(String(500))
    description = Column(Text)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    variants = relationship("Variant", back_populates="product", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Product {self.brand} {self.model} - {self.colorway}>"

    @property
    def display_name(self):
        return f"{self.brand} {self.model} - {self.colorway}"

    @property
    def total_inventory(self):
        return sum(v.qty_on_hand for v in self.variants)


class Variant(Base):
    """
    Product variant (size + color matrix).
    Individual SKU with pricing, inventory, and authentication.
    """
    __tablename__ = 'variants'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False, index=True)

    # Matrix attributes
    size = Column(String(20), nullable=False, index=True)  # US 7, S, M, L, etc.
    color = Column(String(50))  # For apparel with multiple colorways

    # Identifiers
    sku = Column(String(50), unique=True, nullable=False, index=True)
    barcode = Column(String(50), unique=True, index=True)
    epc = Column(String(100), unique=True, index=True)  # RFID tag
    rfid_tagged = Column(Boolean, default=False)

    # Condition and pricing
    condition = Column(SQLEnum(Condition), default=Condition.EXCELLENT, nullable=False)
    buy_price = Column(Float, nullable=False)  # What we paid
    list_price = Column(Float, nullable=False)  # What we're asking

    # Inventory
    qty_on_hand = Column(Integer, default=1, nullable=False)
    qty_sold = Column(Integer, default=0, nullable=False)
    qty_reserved = Column(Integer, default=0, nullable=False)

    # Authentication
    auth_status = Column(SQLEnum(AuthStatus), default=AuthStatus.NOT_REQUIRED, nullable=False)
    auth_certificate_url = Column(String(500))
    auth_date = Column(DateTime)

    # Consignment
    consignor_id = Column(Integer, ForeignKey('consignors.id'), index=True)
    commission_percent = Column(Float)  # Overrides consignor default if set

    # Photos
    photo_urls = Column(Text)  # JSON array of photo URLs

    # Metadata
    location = Column(String(50))  # Shelf/bin location
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    product = relationship("Product", back_populates="variants")
    consignor = relationship("Consignor", back_populates="variants")
    sales = relationship("Sale", back_populates="variant")
    reserves = relationship("Reserve", back_populates="variant")

    def __repr__(self):
        return f"<Variant {self.sku} - Size {self.size}>"

    @property
    def available_qty(self):
        """Quantity available for sale (not reserved or sold)."""
        return max(0, self.qty_on_hand - self.qty_reserved)

    @property
    def is_available(self):
        """Check if variant is available for purchase."""
        return self.available_qty > 0

    @property
    def margin(self):
        """Profit margin percentage."""
        if self.buy_price == 0:
            return 0
        return ((self.list_price - self.buy_price) / self.buy_price) * 100

    @property
    def profit(self):
        """Gross profit per unit."""
        return self.list_price - self.buy_price


class Consignor(Base):
    """
    Consignment seller/partner.
    Tracks items, sales, and payouts.
    """
    __tablename__ = 'consignors'

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, index=True)
    phone = Column(String(20))

    # Consignment terms
    default_commission_percent = Column(Float, default=20.0, nullable=False)  # Store takes 20%
    auto_payout_threshold = Column(Float, default=500.0)  # Auto payout when balance exceeds

    # Financials
    balance = Column(Float, default=0.0, nullable=False)  # Current amount owed
    lifetime_payouts = Column(Float, default=0.0, nullable=False)

    # Portal access
    portal_access_code = Column(String(50), unique=True)  # Simple code for seller portal

    # Status
    active = Column(Boolean, default=True, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    notes = Column(Text)

    # Relationships
    variants = relationship("Variant", back_populates="consignor")
    sales = relationship("Sale", back_populates="consignor")
    payouts = relationship("Payout", back_populates="consignor")

    def __repr__(self):
        return f"<Consignor {self.name} - Balance: ${self.balance:.2f}>"


class Sale(Base):
    """
    Sales transaction record.
    Tracks channel, pricing, fees, and consignment splits.
    """
    __tablename__ = 'sales'

    id = Column(Integer, primary_key=True)
    variant_id = Column(Integer, ForeignKey('variants.id'), nullable=False, index=True)
    consignor_id = Column(Integer, ForeignKey('consignors.id'), index=True)

    # Sale details
    quantity = Column(Integer, default=1, nullable=False)
    channel = Column(SQLEnum(SaleChannel), default=SaleChannel.IN_STORE, nullable=False)
    sale_price = Column(Float, nullable=False)  # Actual sale price per unit

    # Fees and splits
    platform_fees = Column(Float, default=0.0)  # Marketplace/payment fees
    consignor_split = Column(Float, default=0.0)  # Amount owed to consignor
    store_profit = Column(Float, nullable=False)  # Store's take

    # Payment
    payment_method = Column(String(50))
    transaction_id = Column(String(100))

    # Customer info (optional)
    customer_name = Column(String(200))
    customer_email = Column(String(200))

    # Metadata
    clerk_id = Column(String(50))  # Who processed the sale
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    notes = Column(Text)

    # Relationships
    variant = relationship("Variant", back_populates="sales")
    consignor = relationship("Consignor", back_populates="sales")

    def __repr__(self):
        return f"<Sale {self.id} - ${self.sale_price} on {self.timestamp}>"


class Reserve(Base):
    """
    Reserve/hold system for omnichannel inventory.
    Prevents double-selling during try-on or online cart.
    """
    __tablename__ = 'reserves'

    id = Column(Integer, primary_key=True)
    variant_id = Column(Integer, ForeignKey('variants.id'), nullable=False, index=True)

    # Reserve details
    status = Column(SQLEnum(ReserveStatus), default=ReserveStatus.ACTIVE, nullable=False, index=True)
    quantity = Column(Integer, default=1, nullable=False)
    channel = Column(SQLEnum(SaleChannel), nullable=False)

    # Timing
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    hold_until = Column(DateTime, nullable=False, index=True)  # Auto-release time
    released_at = Column(DateTime)

    # Who/what reserved it
    clerk_id = Column(String(50))  # Staff member
    customer_name = Column(String(200))
    customer_email = Column(String(200))
    session_id = Column(String(100))  # Online cart session

    # Audit
    notes = Column(Text)
    manual_override = Column(Boolean, default=False)  # Was manually released early?

    # Relationships
    variant = relationship("Variant", back_populates="reserves")

    def __repr__(self):
        return f"<Reserve {self.id} - {self.status} until {self.hold_until}>"

    @property
    def is_active(self):
        """Check if reserve is still active."""
        return self.status == ReserveStatus.ACTIVE and datetime.utcnow() < self.hold_until

    @property
    def is_expired(self):
        """Check if reserve has expired."""
        return self.status == ReserveStatus.ACTIVE and datetime.utcnow() >= self.hold_until


class Payout(Base):
    """
    Consignment payout records.
    Tracks when and how much was paid to consignors.
    """
    __tablename__ = 'payouts'

    id = Column(Integer, primary_key=True)
    consignor_id = Column(Integer, ForeignKey('consignors.id'), nullable=False, index=True)

    # Payout details
    amount = Column(Float, nullable=False)
    method = Column(String(50))  # Check, Venmo, Bank transfer, etc.
    reference = Column(String(100))  # Check number, transaction ID

    # Timing
    date = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    processed_by = Column(String(100))

    # Audit
    notes = Column(Text)

    # Relationships
    consignor = relationship("Consignor", back_populates="payouts")

    def __repr__(self):
        return f"<Payout {self.id} - ${self.amount} to {self.consignor.name}>"


class AuditLog(Base):
    """
    Audit trail for important actions.
    Tracks who did what and when.
    """
    __tablename__ = 'audit_logs'

    id = Column(Integer, primary_key=True)

    # What happened
    action = Column(String(50), nullable=False, index=True)  # reserve_created, sale_completed, etc.
    entity_type = Column(String(50), nullable=False)  # variant, consignor, etc.
    entity_id = Column(Integer, nullable=False)

    # Details
    details = Column(Text)  # JSON with action details

    # Who and when
    user_id = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    ip_address = Column(String(50))

    def __repr__(self):
        return f"<AuditLog {self.action} on {self.entity_type} at {self.timestamp}>"


# Database initialization
def init_db(database_url='sqlite:///resale_manager.db'):
    """Initialize database and create all tables."""
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """Get database session."""
    Session = sessionmaker(bind=engine)
    return Session()
