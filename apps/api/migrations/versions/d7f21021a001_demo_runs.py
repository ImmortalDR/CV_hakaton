"""Independent synthetic demo runs; existing accounts and history preserved."""
from alembic import op
import sqlalchemy as sa

revision = 'd7f21021a001'
down_revision = 'c6a10321d001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('demo_runs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('token_hash', sa.String(64), nullable=False, unique=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    op.add_column('users', sa.Column('demo_run_id', sa.String(36), nullable=True))
    op.create_foreign_key('fk_users_demo_run', 'users', 'demo_runs', ['demo_run_id'], ['id'])
    op.create_index('ix_users_demo_run_id', 'users', ['demo_run_id'])


def downgrade():
    op.drop_index('ix_users_demo_run_id', table_name='users')
    op.drop_constraint('fk_users_demo_run', 'users', type_='foreignkey')
    op.drop_column('users', 'demo_run_id')
    op.drop_table('demo_runs')
