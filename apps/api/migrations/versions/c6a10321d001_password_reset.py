"""Single-use hashed password recovery links."""
from alembic import op
import sqlalchemy as sa
revision = 'c6a10321d001'
down_revision = 'b9e1c4d7a201'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('password_resets',
        sa.Column('token_hash', sa.String(64), primary_key=True),
        sa.Column('user_id', sa.String(36), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=False))
    op.create_index('ix_password_resets_user_id', 'password_resets', ['user_id'])

def downgrade():
    op.drop_table('password_resets')
