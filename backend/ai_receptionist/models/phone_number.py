"""
PhoneNumber model – tracks Twilio numbers assigned to tenants.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey

from ai_receptionist.models.base import Base


class PhoneNumber(Base):
    __tablename__ = "phone_numbers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(255), ForeignKey("tenants.id"), nullable=False, index=True)
    phone_number = Column(String(20), unique=True, nullable=False)   # E.164
    twilio_sid = Column(String(255), unique=True, nullable=False)
    friendly_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<PhoneNumber(number='{self.phone_number}', tenant='{self.tenant_id}')>"
