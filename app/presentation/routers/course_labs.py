from fastapi import APIRouter, Depends, status
from fastapi.exceptions import HTTPException

from app.application.ports.auth import CurrentUser
from app.application.use_cases.lab_enrollment import LabEnrollmentUseCases
from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.presentation.dependencies.auth import get_current_user, require_content_editor
from app.presentation.schemas.content import ApiResponse
from app.presentation.schemas.lab_access import CourseLabAccessRead, EnrollmentCreate

router = APIRouter(prefix="/api/courses/{course_slug}/lab", tags=["CourseLabs"])


def use_cases(uow: SqlModelUnitOfWork) -> LabEnrollmentUseCases:
    return LabEnrollmentUseCases(lambda: uow)


def access_read(access) -> CourseLabAccessRead:
    return CourseLabAccessRead.model_validate(access, from_attributes=True)


def _authorize_enrollment(user: CurrentUser, target_user_id: str) -> None:
    if user.is_superuser or user.has_any_role(("admin", "instructor")) or user.id == target_user_id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


@router.get("/my-lab", response_model=ApiResponse[CourseLabAccessRead | None])
async def get_my_lab_access(
    course_slug: str,
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    access = await use_cases(uow).my_access(course_slug, user.id)
    return ApiResponse(data=access_read(access) if access is not None else None, meta={"resource": "course_lab_access"})


@router.post("/enroll", response_model=ApiResponse[CourseLabAccessRead], status_code=status.HTTP_201_CREATED)
async def enroll_lab(
    course_slug: str,
    payload: EnrollmentCreate,
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    _authorize_enrollment(user, payload.user_id)
    access = await use_cases(uow).enroll(course_slug, payload.user_id)
    return ApiResponse(data=access_read(access), meta={"resource": "course_lab_access"})


@router.delete("/release/{user_id}", response_model=ApiResponse[CourseLabAccessRead])
async def release_lab(
    course_slug: str,
    user_id: str,
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    _authorize_enrollment(user, user_id)
    access = await use_cases(uow).release(course_slug, user_id)
    return ApiResponse(data=access_read(access), meta={"resource": "course_lab_access"})


@router.get("/accesses", response_model=ApiResponse[list[CourseLabAccessRead]])
async def list_lab_accesses(
    course_slug: str,
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    live = await use_cases(uow).list_course_accesses(course_slug)
    return ApiResponse(data=[access_read(a) for a in live], meta={"resource": "course_lab_accesses"})
