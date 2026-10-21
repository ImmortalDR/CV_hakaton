"""Shared demo inactivity clock and immutable initial example snapshot."""
from alembic import op
import sqlalchemy as sa
revision = 'e8f21021a001'
down_revision = 'd7f21021a001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('demo_workspace',
        sa.Column('id', sa.String(20), primary_key=True),
        sa.Column('baseline', sa.JSON(), nullable=False),
        sa.Column('last_activity', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_reset', sa.DateTime(timezone=True), nullable=True),
        sa.Column('generation', sa.Integer(), nullable=False))


def downgrade():
    op.drop_table('demo_workspace')
