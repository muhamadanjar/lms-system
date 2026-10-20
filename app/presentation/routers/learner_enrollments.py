from fastapi import APIRouter, Depends

from app.application.ports.auth import CurrentUser
from app.application.use_cases.enrollment import EnrollmentUseCases
from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.presentation.dependencies.auth import get_current_user
from app.presentation.schemas.content import ApiResponse
from app.presentation.schemas.enrollment import (
    LearnerCourseProgressRead,
    LearnerCourseRead,
    LearnerCourseReferenceRead,
    LearnerEnrollmentSummaryRead,
)

learner_router = APIRouter(prefix="/api/learner/enrollments", tags=["Learner Enrollment"])


def use_cases(uow: SqlModelUnitOfWork) -> EnrollmentUseCases:
    return EnrollmentUseCases(lambda: uow)


@learner_router.get("", response_model=ApiResponse[list[LearnerCourseRead]])
async def list_my_enrollments(
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    summaries = await use_cases(uow).my_course_summaries(user.id)
    return ApiResponse(
        data=[
            LearnerCourseRead(
                course=LearnerCourseReferenceRead(
                    slug=summary.course_slug,
                    title=summary.course_title,
                    description=summary.course_description,
                ),
                enrollment=LearnerEnrollmentSummaryRead(
                    status=summary.enrollment_status,
                    enrolled_at=summary.enrolled_at,
                    completed_at=summary.completed_at,
                ),
                progress=LearnerCourseProgressRead(
                    completed_sections=summary.completed_sections,
                    total_sections=summary.total_sections,
                    percentage=summary.percentage,
                    course_state=summary.course_state,
                ),
            )
            for summary in summaries
        ],
        meta={},
    )
