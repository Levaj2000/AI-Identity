"""Add agent.eu_ai_act_risk_class for Annex III classification.

Dependency of #273 (compliance export scoping). Stores the EU AI Act
Annex III category code (e.g. '3(a)', '4(b)') or the 'not_in_scope'
sentinel for agents the deployer has evaluated and determined are not
high-risk. Nullable — null means not yet classified.

Validation of allowed values lives at the schema layer
(common/validation/eu_ai_act.py) so the canonical Annex III list can be
updated without a migration. The column is plain text here.

Revision ID: s0p1q2r3s4t5
Revises: r9o0p1q2r3s4
Create Date: 2026-04-23
"""

import sqlalchemy as sa

from alembic import op

revision = "s0p1q2r3s4t5"
down_revision = "r9o0p1q2r3s4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "agents",
        sa.Column("eu_ai_act_risk_class", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agents", "eu_ai_act_risk_class")
