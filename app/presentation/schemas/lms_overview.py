from pydantic import BaseModel


class LmsOverviewRead(BaseModel):
    """KPI agregat lintas course untuk halaman overview admin."""

    total_courses: int
    unique_learners: int
    active_enrollments: int
    pending_reviews: int
    section_completion_ratio: float
    avg_quiz_score_pct: float
