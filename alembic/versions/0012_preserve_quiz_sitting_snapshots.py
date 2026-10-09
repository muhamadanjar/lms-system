"""preserve quiz sitting snapshots after authoring changes

Revision ID: 0012_quiz_snapshot_fks
Revises: 0011_course_quiz_lifecycle
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0012_quiz_snapshot_fks"
down_revision: Union[str, None] = "0011_course_quiz_lifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("fk_sitting_questions_source_question", "quiz_sitting_questions", type_="foreignkey")
    op.drop_constraint("fk_sitting_options_source_answer", "quiz_sitting_options", type_="foreignkey")


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM quiz_sitting_questions s LEFT JOIN questions q ON q.id = s.source_question_id WHERE q.id IS NULL)
               OR EXISTS (SELECT 1 FROM quiz_sitting_options s LEFT JOIN answers a ON a.id = s.source_answer_id WHERE a.id IS NULL) THEN
                RAISE EXCEPTION 'Cannot restore snapshot-source foreign keys after their authored rows were deleted';
            END IF;
        END $$
    """)
    op.create_foreign_key("fk_sitting_questions_source_question", "quiz_sitting_questions", "questions", ["source_question_id"], ["id"])
    op.create_foreign_key("fk_sitting_options_source_answer", "quiz_sitting_options", "answers", ["source_answer_id"], ["id"])
