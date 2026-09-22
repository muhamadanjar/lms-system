from fastapi import APIRouter, Depends, Query, Response, status

from app.application.ports.auth import CurrentUser
from app.application.use_cases.content_crud import ContentCrudUseCases
from app.domain.entities.course import Course
from app.domain.value_objects.content import ContentStatus
from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.presentation.dependencies.auth import get_current_user, require_content_editor
from app.presentation.schemas.content import (
    ApiResponse,
    CourseCreate,
    CourseRead,
    CourseUpdate,
    PaginationQuery,
    course_read,
)

router = APIRouter(prefix="/api/courses", tags=["Courses"])


def use_cases(uow: SqlModelUnitOfWork) -> ContentCrudUseCases:
    return ContentCrudUseCases(lambda: uow)


def can_manage(user: CurrentUser) -> bool:
    return user.has_any_role(("admin", "instructor"))


def read_filter(query: PaginationQuery, user: CurrentUser) -> tuple[ContentStatus | None, bool]:
    if can_manage(user):
        return query.status, query.include_archived
    return ContentStatus.PUBLISHED, False


@router.get("", response_model=ApiResponse[list[CourseRead]])
async def list_courses(
    query: PaginationQuery = Depends(),
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    status_filter, include_archived = read_filter(query, user)
    items, total = await use_cases(uow).list_courses(status_filter, include_archived, (query.page - 1) * query.page_size, query.page_size)
    return ApiResponse(data=[course_read(item) for item in items], meta={"page": query.page, "page_size": query.page_size, "total": total})


@router.post("", response_model=ApiResponse[CourseRead], status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreate,
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    course = await use_cases(uow).create_course(Course(title=payload.title, description=payload.description, slug=payload.slug, status=payload.status))
    return ApiResponse(data=course_read(course), meta={"resource": "course"})


@router.get("/{course_slug}", response_model=ApiResponse[CourseRead])
async def get_course(
    course_slug: str,
    include_archived: bool = Query(default=False),
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    hierarchy = await use_cases(uow).get_course(course_slug, include_archived=include_archived and can_manage(user))
    if not can_manage(user) and hierarchy.course.status is not ContentStatus.PUBLISHED:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="course not found")
    return ApiResponse(data=course_read(hierarchy.course, hierarchy.modules, hierarchy.sections_by_module), meta={})


@router.patch("/{course_slug}", response_model=ApiResponse[CourseRead])
async def update_course(
    course_slug: str,
    payload: CourseUpdate,
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    course = await use_cases(uow).update_course(course_slug, payload.model_dump(exclude_unset=True))
    return ApiResponse(data=course_read(course), meta={"resource": "course"})


@router.delete("/{course_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_slug: str,
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    await use_cases(uow).delete_course(course_slug)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
