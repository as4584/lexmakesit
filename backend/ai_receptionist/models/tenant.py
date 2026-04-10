"""
Tenant model – represents a business / organisation.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ai_receptionist.models.base import Base


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)  # slug, e.g. "innovation"
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # display name
    owner_user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    plan: Mapped[str] = mapped_column(String(50), nullable=False, default="starter")

    # Voice settings
    tts_provider: Mapped[str] = mapped_column(
        String(50), nullable=False, default="openai"
    )  # 'openai' | 'elevenlabs'
    openai_voice: Mapped[str | None] = mapped_column(
        String(50), nullable=True, default="shimmer"
    )  # one of alloy/ash/coral/echo/onyx/sage/shimmer/verse
    elevenlabs_voice_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # selected library voice
    elevenlabs_voice_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    elevenlabs_voice_preview_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    custom_clone_voice_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # 1 clone per account
    custom_clone_voice_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    google_voice_number: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # optional forwarding number

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Tenant(id='{self.id}', plan='{self.plan}')>"
