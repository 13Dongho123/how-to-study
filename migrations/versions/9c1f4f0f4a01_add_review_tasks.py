"""add review_tasks

Revision ID: 9c1f4f0f4a01
Revises: 2f87bc9361b1
Create Date: 2026-03-03 22:44:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9c1f4f0f4a01"
down_revision = "2f87bc9361b1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "review_tasks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="scheduled"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "question_id",
            "scheduled_date",
            name="uq_review_task_user_question_date",
        ),
    )
    op.create_index("ix_review_tasks_user_date", "review_tasks", ["user_id", "scheduled_date"], unique=False)
    op.create_index("ix_review_tasks_user_question", "review_tasks", ["user_id", "question_id"], unique=False)


def downgrade():
    op.drop_index("ix_review_tasks_user_question", table_name="review_tasks")
    op.drop_index("ix_review_tasks_user_date", table_name="review_tasks")
    op.drop_table("review_tasks")
