from fastapi import APIRouter, Depends, Response, status

from app.application.use_cases.course_instructor import CourseInstructorUseCases
from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.presentation.dependencies.auth import require_roles
from app.presentation.schemas.content import ApiResponse
from app.presentation.schemas.course_instructor import CourseInstructorAssign, CourseInstructorRead

admin_router = APIRouter(prefix="/api/admin/courses/{course_slug}/instructors", tags=["Admin Course Instructors"])


@admin_router.get("", response_model=ApiResponse[list[CourseInstructorRead]])
async def list_instructors(
    course_slug: str,
    _user=Depends(require_roles("admin")),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    instructors = await CourseInstructorUseCases(lambda: uow).list_for_course(course_slug)
    return ApiResponse(
        data=[CourseInstructorRead.model_validate(item) for item in instructors],
        meta={"resource": "course_instructors"},
    )


@admin_router.post("", response_model=ApiResponse[CourseInstructorRead], status_code=status.HTTP_201_CREATED)
async def assign_instructor(
    course_slug: str,
    payload: CourseInstructorAssign,
    _user=Depends(require_roles("admin")),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    instructor = await CourseInstructorUseCases(lambda: uow).assign(course_slug, payload.user_id)
    return ApiResponse(data=CourseInstructorRead.model_validate(instructor), meta={"resource": "course_instructor"})


@admin_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_instructor(
    course_slug: str,
    user_id: str,
    _user=Depends(require_roles("admin")),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    await CourseInstructorUseCases(lambda: uow).remove(course_slug, user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
