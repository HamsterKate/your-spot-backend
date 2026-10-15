"""align users with MVP schema

Revision ID: 5fcc882b8bec
Revises: 31c420c1dd83
Create Date: 2026-10-15 19:45:32.390525

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "5fcc882b8bec"
down_revision: Union[str, Sequence[str], None] = "31c420c1dd83"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "users",
        "first_name",
        existing_type=sa.VARCHAR(length=100),
        existing_nullable=False,
        new_column_name="display_name",
    )
    op.alter_column(
        "users",
        "display_name",
        existing_type=sa.VARCHAR(length=100),
        type_=sa.String(length=50),
        existing_nullable=False,
    )
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.VARCHAR(length=255),
        existing_nullable=False,
        new_column_name="password_hash",
    )
    op.alter_column(
        "users",
        "email",
        existing_type=sa.VARCHAR(length=255),
        nullable=False,
    )
    op.drop_constraint(
        "users_email_or_phone_required",
        "users",
        type_="check",
    )
    op.drop_constraint("users_phone_key", "users", type_="unique")
    op.drop_constraint("users_username_key", "users", type_="unique")
    op.drop_column("users", "phone")
    op.drop_column("users", "username")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "users",
        sa.Column("username", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("phone", sa.String(length=20), nullable=True),
    )
    op.execute("UPDATE users SET username = 'legacy_' || id::text")
    op.alter_column(
        "users",
        "username",
        existing_type=sa.VARCHAR(length=50),
        nullable=False,
    )
    op.create_unique_constraint("users_username_key", "users", ["username"])
    op.create_unique_constraint("users_phone_key", "users", ["phone"])
    op.alter_column(
        "users",
        "email",
        existing_type=sa.VARCHAR(length=255),
        nullable=True,
    )
    op.alter_column(
        "users",
        "display_name",
        existing_type=sa.VARCHAR(length=50),
        type_=sa.String(length=100),
        existing_nullable=False,
        new_column_name="first_name",
    )
    op.alter_column(
        "users",
        "password_hash",
        existing_type=sa.VARCHAR(length=255),
        existing_nullable=False,
        new_column_name="hashed_password",
    )
    op.create_check_constraint(
        "users_email_or_phone_required",
        "users",
        "email IS NOT NULL OR phone IS NOT NULL",
    )
