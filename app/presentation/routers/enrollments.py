from fastapi import APIRouter, Depends, Request, status
from fastapi.exceptions import HTTPException

from app.application.ports.auth import CurrentUser
from app.application.use_cases.enrollment import EnrollmentUseCases
from app.config.config import get_settings
from app.infrastructure.auth.usermanagement_directory import UserManagementDirectory
from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.presentation.dependencies.auth import get_current_user, require_content_editor
from app.presentation.schemas.content import ApiResponse
from app.presentation.schemas.enrollment import (
    BulkEnrollRequest,
    BulkEnrollResponse,
    EnrollmentComplete,
    EnrollmentCreate,
    EnrollmentRead,
)

admin_router = APIRouter(prefix="/api/admin/courses/{course_slug}/enrollments", tags=["Admin Enrollment"])
learner_router = APIRouter(prefix="/api/learner/courses/{course_slug}/enrollments", tags=["Learner Enrollment"])


def _directory() -> UserManagementDirectory:
    """Factory terpisah agar contract tests bisa memonkeypatch resolusi email."""
    return UserManagementDirectory(get_settings().usermanagement)


def use_cases(uow: SqlModelUnitOfWork) -> EnrollmentUseCases:
    return EnrollmentUseCases(lambda: uow, user_directory=_directory())


def enrollment_read(enrollment) -> EnrollmentRead:
    return EnrollmentRead.model_validate(enrollment, from_attributes=True)


def _authorize_self_or_editor(user: CurrentUser, target_user_id: str) -> None:
    if user.is_superuser or user.has_any_role(("admin", "instructor")) or user.id == target_user_id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


async def enroll_course(
    course_slug: str,
    payload: EnrollmentCreate,
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    _authorize_self_or_editor(user, payload.user_id)
    editor = user.is_superuser or user.has_any_role(("admin", "instructor"))
    enrollment = await use_cases(uow).enroll(course_slug, payload.user_id, enrolled_at=payload.enrolled_at if editor else None)
    return ApiResponse(data=enrollment_read(enrollment), meta={"resource": "enrollment"})


@admin_router.post("", response_model=ApiResponse[EnrollmentRead], status_code=status.HTTP_201_CREATED)
async def admin_enroll_course(
    course_slug: str,
    payload: EnrollmentCreate,
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    enrollment = await use_cases(uow).enroll(course_slug, payload.user_id, enrolled_at=payload.enrolled_at)
    return ApiResponse(data=enrollment_read(enrollment), meta={"resource": "enrollment"})


@learner_router.post("", response_model=ApiResponse[EnrollmentRead], status_code=status.HTTP_201_CREATED)
async def learner_enroll_course(
    course_slug: str,
    payload: EnrollmentCreate,
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    if payload.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Learners can only enroll themselves")
    enrollment = await use_cases(uow).enroll(course_slug, user.id)
    return ApiResponse(data=enrollment_read(enrollment), meta={"resource": "enrollment"})


@learner_router.get("/me", response_model=ApiResponse[EnrollmentRead | None])
async def get_my_enrollment(
    course_slug: str,
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    enrollment = await use_cases(uow).my_enrollment(course_slug, user.id)
    return ApiResponse(data=enrollment_read(enrollment) if enrollment is not None else None, meta={"resource": "enrollment"})


async def list_enrollments(
    course_slug: str,
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    live = await use_cases(uow).list_course_enrollments(course_slug)
    return ApiResponse(data=[enrollment_read(e) for e in live], meta={"resource": "enrollments"})


@admin_router.get("", response_model=ApiResponse[list[EnrollmentRead]])
async def list_admin_course_enrollments(
    course_slug: str,
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    live = await use_cases(uow).list_course_enrollments(course_slug)
    return ApiResponse(data=[enrollment_read(e) for e in live], meta={"resource": "enrollments"})


@admin_router.post("/{user_id}/complete", response_model=ApiResponse[EnrollmentRead])
async def complete_enrollment(
    course_slug: str,
    user_id: str,
    payload: EnrollmentComplete,
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    enrollment = await use_cases(uow).complete(course_slug, user_id, completed_at=payload.completed_at)
    return ApiResponse(data=enrollment_read(enrollment), meta={"resource": "enrollment"})


async def withdraw_enrollment(
    course_slug: str,
    user_id: str,
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    _authorize_self_or_editor(user, user_id)
    enrollment = await use_cases(uow).withdraw(course_slug, user_id)
    return ApiResponse(data=enrollment_read(enrollment), meta={"resource": "enrollment"})


@admin_router.post("/{user_id}/withdraw", response_model=ApiResponse[EnrollmentRead])
async def admin_withdraw_enrollment(
    course_slug: str,
    user_id: str,
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    enrollment = await use_cases(uow).withdraw(course_slug, user_id)
    return ApiResponse(data=enrollment_read(enrollment), meta={"resource": "enrollment"})


@learner_router.post("/{user_id}/withdraw", response_model=ApiResponse[EnrollmentRead])
async def learner_withdraw_enrollment(
    course_slug: str,
    user_id: str,
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    if user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Learners can only withdraw their own enrollment")
    enrollment = await use_cases(uow).withdraw(course_slug, user.id)
    return ApiResponse(data=enrollment_read(enrollment), meta={"resource": "enrollment"})


@admin_router.post("/bulk", response_model=ApiResponse[BulkEnrollResponse], status_code=status.HTTP_207_MULTI_STATUS)
async def bulk_enroll_course(
    course_slug: str,
    payload: BulkEnrollRequest,
    request: Request,
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    authorization = request.headers.get("authorization")
    result = await use_cases(uow).bulk_enroll(
        course_slug,
        [item.model_dump() for item in payload.users],
        authorization=authorization,
    )
    return ApiResponse(
        data=BulkEnrollResponse(
            enrolled=[enrollment_read(e) for e in result.enrolled],
            skipped=result.skipped,
            failed=result.failed,
        ),
        meta={"resource": "bulk_enrollment"},
    )
