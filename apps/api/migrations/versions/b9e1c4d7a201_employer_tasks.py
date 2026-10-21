"""Add consented periodic employer tasks without changing historical assessments."""
from alembic import op
import sqlalchemy as sa

revision = 'b9e1c4d7a201'
down_revision = 'f8a2ba6fc338'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('task_plans',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('company_id',sa.String(36),sa.ForeignKey('companies.id'),nullable=False),
        sa.Column('candidate_id',sa.String(36),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('request_id',sa.String(36),nullable=False),
        sa.Column('title',sa.String(160),nullable=False),
        sa.Column('prompt',sa.String(4000),nullable=False),
        sa.Column('rubric',sa.String(2000),nullable=False),
        sa.Column('interval_days',sa.Integer(),nullable=False),
        sa.Column('response_days',sa.Integer(),nullable=False),
        sa.Column('version',sa.Integer(),nullable=False),
        sa.Column('status',sa.String(20),nullable=False),
        sa.Column('next_issue_at',sa.DateTime(timezone=True)),
        sa.Column('consent_at',sa.DateTime(timezone=True)),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.UniqueConstraint('company_id','request_id'),
        sa.CheckConstraint('interval_days BETWEEN 1 AND 365'),
        sa.CheckConstraint('response_days BETWEEN 1 AND interval_days'),
        sa.CheckConstraint("status IN ('awaiting','active','paused','closed')"))
    op.create_index('ix_task_plans_company_id','task_plans',['company_id'])
    op.create_index('ix_task_plans_candidate_id','task_plans',['candidate_id'])
    op.create_table('task_assignments',
        sa.Column('id',sa.String(36),primary_key=True),
        sa.Column('plan_id',sa.String(36),sa.ForeignKey('task_plans.id'),nullable=False),
        sa.Column('sequence',sa.Integer(),nullable=False),
        sa.Column('version',sa.Integer(),nullable=False),
        sa.Column('title',sa.String(160),nullable=False),
        sa.Column('prompt',sa.String(4000),nullable=False),
        sa.Column('rubric',sa.String(2000),nullable=False),
        sa.Column('status',sa.String(20),nullable=False),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('due_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('answer',sa.String(6000)),
        sa.Column('submitted_at',sa.DateTime(timezone=True)),
        sa.Column('score',sa.Integer()),
        sa.Column('feedback',sa.String(2000)),
        sa.Column('reviewed_at',sa.DateTime(timezone=True)),
        sa.UniqueConstraint('plan_id','sequence'),
        sa.CheckConstraint('score IS NULL OR score BETWEEN 0 AND 100'),
        sa.CheckConstraint("status IN ('issued','viewed','submitted','reviewed','expired','cancelled')"))
    op.create_index('ix_task_assignments_plan_id','task_assignments',['plan_id'])


def downgrade():
    op.drop_table('task_assignments')
    op.drop_table('task_plans')
