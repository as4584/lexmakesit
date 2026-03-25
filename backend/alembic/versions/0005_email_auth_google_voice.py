"""add email auth fields and google voice number

Revision ID: 0005_email_auth_google_voice
Revises: 0004_voice_settings
Create Date: 2026-03-25 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '0005_email_auth_google_voice'
down_revision = '0004_voice_settings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Email auth fields on users ---
    op.add_column('users', sa.Column('email', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('users', sa.Column('email_verification_token', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('password_reset_token', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('password_reset_expires', sa.DateTime(), nullable=True))

    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_email_verification_token', 'users', ['email_verification_token'])
    op.create_index('ix_users_password_reset_token', 'users', ['password_reset_token'])

    # --- Google Voice on tenants ---
    op.add_column('tenants', sa.Column('google_voice_number', sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column('tenants', 'google_voice_number')

    op.drop_index('ix_users_password_reset_token', table_name='users')
    op.drop_index('ix_users_email_verification_token', table_name='users')
    op.drop_index('ix_users_email', table_name='users')

    op.drop_column('users', 'password_reset_expires')
    op.drop_column('users', 'password_reset_token')
    op.drop_column('users', 'email_verification_token')
    op.drop_column('users', 'email_verified')
    op.drop_column('users', 'email')
