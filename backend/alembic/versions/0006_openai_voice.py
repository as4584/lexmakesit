"""add openai_voice and google_voice_number to tenants

Revision ID: 0006_openai_voice
Revises: 0005_email_auth_google_voice
Create Date: 2026-04-10 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.exc import ProgrammingError


revision = "0006_openai_voice"
down_revision = "0005_email_auth_google_voice"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # openai_voice may already exist on live if it was hotfixed manually
    op.execute(
        "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS openai_voice VARCHAR(50) DEFAULT 'shimmer'"
    )
    # google_voice_number is added by 0005 but included here as a safety guard
    # in case a DB was migrated directly from 0004 → 0006 skipping 0005
    op.execute(
        "ALTER TABLE tenants ADD COLUMN IF NOT EXISTS google_voice_number VARCHAR(20)"
    )


def downgrade() -> None:
    op.drop_column("tenants", "openai_voice")
    op.drop_column("tenants", "google_voice_number")
