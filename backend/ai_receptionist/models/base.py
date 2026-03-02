"""
Shared SQLAlchemy declarative base.

All ORM models must import Base from here so Alembic autogenerate
can discover every table through a single MetaData instance.
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()
