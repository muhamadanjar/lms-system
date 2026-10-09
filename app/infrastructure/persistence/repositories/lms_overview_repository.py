from dataclasses import dataclass

from sqlmodel import func, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.value_objects.content import ContentStatus
from app.infrastructure.persistence.models.collect_task import CollectTask as CollectTaskRow
from app.infrastructure.persistence.models.course import Course as CourseRow
from app.infrastructure.persistence.models.enrollment import Enrollment as EnrollmentRow
from app.infrastructure.persistence.models.module import Module as ModuleRow
from app.infrastructure.persistence.models.quiz_sitting import QuizSitting as QuizSittingRow
from app.infrastructure.persistence.models.quiz_sitting_question import QuizSittingQuestion as SittingQuestionRow
from app.infrastructure.persistence.models.section import Section as SectionRow
from app.infrastructure.persistence.models.section_completion import SectionCompletion as CompletionRow

PENDING_REVIEW_STATUSES = ("SUBMITTED", "IN_REVIEW")


@dataclass(frozen=True)
class LmsOverviewValues:
    """Read model: enam angka KPI overview, dihitung on-demand."""

    total_courses: int
    unique_learners: int
    active_enrollments: int
    pending_reviews: int
    section_completion_ratio: float
    avg_quiz_score_pct: float


class SqlModelLmsOverviewRepository:
    """Agregat read-only lintas tabel untuk halaman overview (bukan transaksi bisnis)."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def overview(self) -> LmsOverviewValues:
        total_courses = (await self.session.exec(select(func.count()).select_from(CourseRow))).one()
        unique_learners = (await self.session.exec(select(func.count(func.distinct(EnrollmentRow.user_id))))).one()
        active_enrollments = (
            await self.session.exec(
                select(func.count()).select_from(EnrollmentRow).where(EnrollmentRow.status == "ENROLLED")
            )
        ).one()
        pending_reviews = (
            await self.session.exec(
                select(func.count())
                .select_from(CollectTaskRow)
                .where(CollectTaskRow.status.in_(PENDING_REVIEW_STATUSES))
            )
        ).one()
        section_completion_ratio = await self._section_completion_ratio()
        avg_quiz_score_pct = await self._avg_quiz_score_pct()
        return LmsOverviewValues(
            total_courses=total_courses,
            unique_learners=unique_learners,
            active_enrollments=active_enrollments,
            pending_reviews=pending_reviews,
            section_completion_ratio=section_completion_ratio,
            avg_quiz_score_pct=avg_quiz_score_pct,
        )

    async def _section_completion_ratio(self) -> float:
        """% completion pada section milik course PUBLISHED; 0.0 bila belum ada section published."""
        published = str(ContentStatus.PUBLISHED)
        denominator = (
            await self.session.exec(
                select(func.count())
                .select_from(SectionRow)
                .join(ModuleRow, SectionRow.module_id == ModuleRow.id)
                .join(CourseRow, ModuleRow.course_id == CourseRow.id)
                .where(CourseRow.status == published)
            )
        ).one()
        if denominator == 0:
            return 0.0
        numerator = (
            await self.session.exec(
                select(func.count())
                .select_from(CompletionRow)
                .join(SectionRow, CompletionRow.section_id == SectionRow.id)
                .join(ModuleRow, SectionRow.module_id == ModuleRow.id)
                .join(CourseRow, ModuleRow.course_id == CourseRow.id)
                .where(CourseRow.status == published)
            )
        ).one()
        return round(numerator * 100.0 / denominator, 1)

    async def _avg_quiz_score_pct(self) -> float:
        """Rata-rata skor % atas finalized sitting = SUM(total_score)/SUM(jumlah soal)×100."""
        score_sum, _attempts = (
            await self.session.exec(
                select(func.sum(QuizSittingRow.total_score), func.count())
                .select_from(QuizSittingRow)
                .where(QuizSittingRow.total_score.is_not(None))
            )
        ).one()
        if not score_sum:
            return 0.0
        question_rows = (
            select(SittingQuestionRow.sitting_id, func.count().label("total"))
            .group_by(SittingQuestionRow.sitting_id)
            .subquery()
        )
        question_sum = (
            await self.session.exec(
                select(func.coalesce(func.sum(question_rows.c.total), 0))
                .select_from(question_rows)
                .join(QuizSittingRow, question_rows.c.sitting_id == QuizSittingRow.id)
                .where(QuizSittingRow.total_score.is_not(None))
            )
        ).one()
        if not question_sum:
            return 0.0
        return round(float(score_sum) * 100.0 / float(question_sum), 1)
