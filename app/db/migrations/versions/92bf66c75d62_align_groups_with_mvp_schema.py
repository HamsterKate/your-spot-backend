"""align groups with MVP schema

Revision ID: 92bf66c75d62
Revises: 5fcc882b8bec
Create Date: 2026-10-15 21:08:25.471614
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "92bf66c75d62"
down_revision: Union[str, Sequence[str], None] = "5fcc882b8bec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "groups",
        sa.Column("creator_id", sa.UUID(), nullable=True),
    )

    op.execute("""
        UPDATE groups
        SET creator_id = group_members.user_id
        FROM group_members
        WHERE group_members.group_id = groups.id
          AND group_members.role = 'OWNER'
        """)

    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM groups
                WHERE creator_id IS NULL
            ) THEN
                RAISE EXCEPTION
                    'Cannot migrate groups without an owner membership';
            END IF;
        END $$;
        """)

    op.alter_column(
        "groups",
        "creator_id",
        existing_type=sa.UUID(),
        nullable=False,
    )
    op.alter_column(
        "groups",
        "name",
        existing_type=sa.VARCHAR(length=100),
        type_=sa.String(length=150),
        existing_nullable=False,
    )
    op.alter_column(
        "groups",
        "description",
        existing_type=sa.VARCHAR(length=500),
        type_=sa.Text(),
        existing_nullable=True,
    )
    op.create_index(
        "ix_groups_creator_id",
        "groups",
        ["creator_id"],
        unique=False,
    )
    op.create_foreign_key(
        "groups_creator_id_fkey",
        "groups",
        "users",
        ["creator_id"],
        ["id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        "group_members_group_id_user_id_unique",
        "group_members",
        type_="unique",
    )
    op.drop_index(
        "ix_group_members_group_id",
        table_name="group_members",
    )
    op.drop_constraint(
        "group_members_pkey",
        "group_members",
        type_="primary",
    )
    op.drop_column("group_members", "id")
    op.create_primary_key(
        "group_members_pkey",
        "group_members",
        ["group_id", "user_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "group_members_pkey",
        "group_members",
        type_="primary",
    )
    op.add_column(
        "group_members",
        sa.Column("id", sa.UUID(), nullable=True),
    )
    op.execute("""
        UPDATE group_members
        SET id = md5(random()::text || clock_timestamp()::text)::uuid
        """)
    op.alter_column(
        "group_members",
        "id",
        existing_type=sa.UUID(),
        nullable=False,
    )
    op.create_primary_key(
        "group_members_pkey",
        "group_members",
        ["id"],
    )
    op.create_index(
        "ix_group_members_group_id",
        "group_members",
        ["group_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "group_members_group_id_user_id_unique",
        "group_members",
        ["group_id", "user_id"],
    )

    op.drop_constraint(
        "groups_creator_id_fkey",
        "groups",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_groups_creator_id",
        table_name="groups",
    )
    op.alter_column(
        "groups",
        "description",
        existing_type=sa.Text(),
        type_=sa.VARCHAR(length=500),
        existing_nullable=True,
    )
    op.alter_column(
        "groups",
        "name",
        existing_type=sa.String(length=150),
        type_=sa.VARCHAR(length=100),
        existing_nullable=False,
    )
    op.drop_column("groups", "creator_id")
