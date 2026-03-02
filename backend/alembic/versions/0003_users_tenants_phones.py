"""create users tenants phone_numbers tables

Revision ID: 0003_users_tenants_phones
Revises: 0002_google_oauth_tokens
Create Date: 2026-03-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0003_users_tenants_phones'
down_revision = '0002_google_oauth_tokens'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=True)

    # --- tenants ---
    op.create_table(
        'tenants',
        sa.Column('id', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('owner_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('plan', sa.String(length=50), nullable=False, server_default='starter'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- phone_numbers ---
    op.create_table(
        'phone_numbers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=255), sa.ForeignKey('tenants.id'), nullable=False),
        sa.Column('phone_number', sa.String(length=20), nullable=False),
        sa.Column('twilio_sid', sa.String(length=255), nullable=False),
        sa.Column('friendly_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_phone_numbers_tenant_id', 'phone_numbers', ['tenant_id'])
    op.create_index('ix_phone_numbers_phone_number', 'phone_numbers', ['phone_number'], unique=True)
    op.create_index('ix_phone_numbers_twilio_sid', 'phone_numbers', ['twilio_sid'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_phone_numbers_twilio_sid', table_name='phone_numbers')
    op.drop_index('ix_phone_numbers_phone_number', table_name='phone_numbers')
    op.drop_index('ix_phone_numbers_tenant_id', table_name='phone_numbers')
    op.drop_table('phone_numbers')
    op.drop_table('tenants')
    op.drop_index('ix_users_username', table_name='users')
    op.drop_table('users')
