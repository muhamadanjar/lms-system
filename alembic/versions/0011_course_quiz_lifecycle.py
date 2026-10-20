"""course-owned quizzes with optional section association

Revision ID: 0011_course_quiz_lifecycle
Revises: 0010_add_sequence_course
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0011_course_quiz_lifecycle"
down_revision: Union[str, None] = "0010_add_sequence_course"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("quizzes", sa.Column("course_id", sa.Uuid(), nullable=True))
    op.add_column("quizzes", sa.Column("title", sa.String(length=255), nullable=False, server_default="Quiz"))
    op.add_column("quizzes", sa.Column("description", sa.Text(), nullable=True))
    op.execute("UPDATE quizzes SET course_id = modules.course_id, title = sections.title, description = sections.description, status = sections.status FROM sections JOIN modules ON modules.id = sections.module_id WHERE quizzes.section_id = sections.id")
    op.alter_column("quizzes", "course_id", nullable=False)
    op.create_foreign_key("fk_quizzes_course_id_courses", "quizzes", "courses", ["course_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_quizzes_course_id", "quizzes", ["course_id"], unique=False)
    op.create_index("uq_quizzes_course_slug", "quizzes", ["course_id", "slug"], unique=True)
    op.drop_constraint("fk_quizzes_section_id_sections", "quizzes", type_="foreignkey")
    op.alter_column("quizzes", "section_id", nullable=True)
    op.create_foreign_key("fk_quizzes_section_id_sections", "quizzes", "sections", ["section_id"], ["id"], ondelete="SET NULL")
    op.execute("DELETE FROM content_slug_registry WHERE content_kind = 'quiz'")


def downgrade() -> None:
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM quizzes WHERE section_id IS NULL) THEN
                RAISE EXCEPTION 'Cannot downgrade while standalone quizzes exist; relink or remove them first';
            END IF;
            IF EXISTS (SELECT 1 FROM quizzes q JOIN content_slug_registry r ON r.slug = q.slug WHERE r.content_id <> q.id) THEN
                RAISE EXCEPTION 'Cannot downgrade while Quiz slugs overlap other content slugs';
            END IF;
        END $$
    """)
    op.execute("INSERT INTO content_slug_registry (slug, content_id, content_kind, created_at) SELECT slug, id, 'quiz', CURRENT_TIMESTAMP FROM quizzes")
    op.drop_constraint("fk_quizzes_section_id_sections", "quizzes", type_="foreignkey")
    op.alter_column("quizzes", "section_id", nullable=False)
    op.create_foreign_key("fk_quizzes_section_id_sections", "quizzes", "sections", ["section_id"], ["id"], ondelete="CASCADE")
    op.drop_index("uq_quizzes_course_slug", table_name="quizzes")
    op.drop_index("ix_quizzes_course_id", table_name="quizzes")
    op.drop_constraint("fk_quizzes_course_id_courses", "quizzes", type_="foreignkey")
    op.drop_column("quizzes", "description")
    op.drop_column("quizzes", "title")
    op.drop_column("quizzes", "course_id")
