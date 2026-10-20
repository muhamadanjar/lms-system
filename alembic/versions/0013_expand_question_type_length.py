"""allow canonical question type values

Revision ID: 0013_question_type_length
Revises: 0012_quiz_snapshot_fks
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0013_question_type_length"
down_revision: Union[str, None] = "0012_quiz_snapshot_fks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "questions",
        "question_type",
        existing_type=sa.String(length=10),
        type_=sa.String(length=12),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM questions WHERE length(question_type) > 10) THEN
                RAISE EXCEPTION 'Cannot shrink question_type to 10 characters while longer values exist';
            END IF;
        END $$
    """)
    op.alter_column(
        "questions",
        "question_type",
        existing_type=sa.String(length=12),
        type_=sa.String(length=10),
        existing_nullable=False,
    )
