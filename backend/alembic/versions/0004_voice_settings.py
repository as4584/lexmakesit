"""add voice settings columns to tenants

Revision ID: 0004_voice_settings
Revises: 0003_users_tenants_phones
Create Date: 2026-03-01 19:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0004_voice_settings'
down_revision = '0003_users_tenants_phones'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('tenants', sa.Column('tts_provider', sa.String(50), nullable=False, server_default='openai'))
    op.add_column('tenants', sa.Column('elevenlabs_voice_id', sa.String(255), nullable=True))
    op.add_column('tenants', sa.Column('elevenlabs_voice_name', sa.String(255), nullable=True))
    op.add_column('tenants', sa.Column('elevenlabs_voice_preview_url', sa.Text, nullable=True))
    op.add_column('tenants', sa.Column('custom_clone_voice_id', sa.String(255), nullable=True))
    op.add_column('tenants', sa.Column('custom_clone_voice_name', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('tenants', 'custom_clone_voice_name')
    op.drop_column('tenants', 'custom_clone_voice_id')
    op.drop_column('tenants', 'elevenlabs_voice_preview_url')
    op.drop_column('tenants', 'elevenlabs_voice_name')
    op.drop_column('tenants', 'elevenlabs_voice_id')
    op.drop_column('tenants', 'tts_provider')
