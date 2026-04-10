"""
PhoneNumber model – tracks Twilio numbers assigned to tenants.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ai_receptionist.models.base import Base


class PhoneNumber(Base):
    __tablename__ = "phone_numbers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("tenants.id"), nullable=False, index=True
    )
    phone_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # E.164
    twilio_sid: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    friendly_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self) -> str:
        return f"<PhoneNumber(number='{self.phone_number}', tenant='{self.tenant_id}')>"
