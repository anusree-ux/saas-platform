"""add idempotency key to events

Revision ID: 43d97ca46bd9
Revises: c6694750d5d3
Create Date: 2026-08-13 21:05:44.868997

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '43d97ca46bd9'
down_revision: Union[str, Sequence[str], None] = 'c6694750d5d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column(
            "idempotency_key",
            sa.String(length=255),
            nullable=True,
        ),
    )

    # Give existing events a unique temporary value
    op.execute(
        """
        UPDATE events
        SET idempotency_key = 'legacy-' || id::text
        WHERE idempotency_key IS NULL
        """
    )

    op.alter_column(
        "events",
        "idempotency_key",
        nullable=False,
    )

    op.create_unique_constraint(
        "uq_events_tenant_idempotency_key",
        "events",
        ["tenant_id", "idempotency_key"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_events_tenant_idempotency_key",
        "events",
        type_="unique",
    )

    op.drop_column(
        "events",
        "idempotency_key",
    )