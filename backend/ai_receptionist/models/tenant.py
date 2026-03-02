"""
Tenant model – represents a business / organisation.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey

from ai_receptionist.models.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String(255), primary_key=True)              # slug, e.g. "innovation"
    name = Column(String(255), nullable=False)               # display name
    owner_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan = Column(String(50), nullable=False, default="starter")

    # Voice settings
    tts_provider = Column(String(50), nullable=False, default="openai")       # 'openai' | 'elevenlabs'
    elevenlabs_voice_id = Column(String(255), nullable=True)                   # selected library voice
    elevenlabs_voice_name = Column(String(255), nullable=True)
    elevenlabs_voice_preview_url = Column(Text, nullable=True)
    custom_clone_voice_id = Column(String(255), nullable=True)                 # 1 clone per account
    custom_clone_voice_name = Column(String(255), nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Tenant(id='{self.id}', plan='{self.plan}')>"
