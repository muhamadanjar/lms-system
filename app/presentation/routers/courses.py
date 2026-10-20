from fastapi import APIRouter, Depends, Query, Response, status
from uuid import UUID

from app.application.ports.auth import CurrentUser
from app.application.use_cases.learner_progress import LearnerProgressUseCases
from app.application.use_cases.content_crud import ContentCrudUseCases
from app.domain.entities.course import Course
from app.domain.entities.enrollment import EnrollmentStatus
from app.domain.value_objects.content import ContentStatus
from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.presentation.dependencies.auth import (
    get_current_user,
    require_content_editor,
    require_roles,
)
from app.presentation.schemas.content import (
    ApiResponse,
    CourseCreate,
    CourseRead,
    CourseUpdate,
    PaginationQuery,
    course_read,
)
from app.presentation.schemas.learner_progress import (
    CourseProgressRead,
    CourseWatchPositionRead,
    CourseWatchPositionWrite,
    course_progress_read,
)

admin_router = APIRouter(prefix="/api/admin/courses", tags=["Admin Courses"])
learner_router = APIRouter(prefix="/api/learner/courses", tags=["Learner Courses"])


def use_cases(uow: SqlModelUnitOfWork) -> ContentCrudUseCases:
    return ContentCrudUseCases(lambda: uow)


def can_manage(user: CurrentUser) -> bool:
    return user.is_superuser or user.has_any_role(("admin", "instructor"))


async def require_learner_enrollment(uow: SqlModelUnitOfWork, user: CurrentUser, course_id: UUID) -> None:
    enrollment = await uow.enrollments.get_live(user.id, course_id)
    if enrollment is not None:
        return
    history = await uow.enrollments.list_history(user.id, course_id)
    if history and history[0].status == EnrollmentStatus.COMPLETED:
        return
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="course not found")


def read_filter(query: PaginationQuery, user: CurrentUser) -> tuple[ContentStatus | None, bool]:
    if can_manage(user):
        return query.status, query.include_archived
    return ContentStatus.PUBLISHED, False


async def list_courses(
    query: PaginationQuery = Depends(),
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    status_filter, include_archived = read_filter(query, user)
    items, total = await use_cases(uow).list_courses(status_filter, include_archived, (query.page - 1) * query.page_size, query.page_size)
    return ApiResponse(data=[course_read(item) for item in items], meta={"page": query.page, "page_size": query.page_size, "total": total})


@admin_router.get("", response_model=ApiResponse[list[CourseRead]])
async def list_admin_courses(
    query: PaginationQuery = Depends(),
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    items, total = await use_cases(uow).list_courses(query.status, query.include_archived, (query.page - 1) * query.page_size, query.page_size)
    return ApiResponse(data=[course_read(item) for item in items], meta={"page": query.page, "page_size": query.page_size, "total": total})


@learner_router.get("", response_model=ApiResponse[list[CourseRead]])
async def list_learner_courses(
    query: PaginationQuery = Depends(),
    _user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    items, total = await use_cases(uow).list_courses(ContentStatus.PUBLISHED, False, (query.page - 1) * query.page_size, query.page_size)
    return ApiResponse(data=[course_read(item) for item in items], meta={"page": query.page, "page_size": query.page_size, "total": total})


@admin_router.post("", response_model=ApiResponse[CourseRead], status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreate,
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    course = await use_cases(uow).create_course(Course(title=payload.title, description=payload.description, slug=payload.slug, status=payload.status, progression_mode=payload.progression_mode, completion_mode=payload.completion_mode))
    return ApiResponse(data=course_read(course), meta={"resource": "course"})


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
    if not can_manage(user):
        await require_learner_enrollment(uow, user, hierarchy.course.id)
    modules = hierarchy.modules
    sections_by_module = hierarchy.sections_by_module
    access = {}
    if not can_manage(user):
        modules = [module for module in hierarchy.modules if module.status is ContentStatus.PUBLISHED]
        sections_by_module = {
            module.id: [section for section in hierarchy.sections_by_module.get(module.id, []) if section.status is ContentStatus.PUBLISHED]
            for module in modules
        }
        sections = [section for group in sections_by_module.values() for section in group]
        access = await LearnerProgressUseCases(lambda: uow).section_access_map(user.id, hierarchy.course.id, sections)
        for section in sections:
            if not access.get(section.id, False):
                section.body = None
    return ApiResponse(data=course_read(hierarchy.course, modules, sections_by_module, access), meta={})


@admin_router.get("/{course_slug}", response_model=ApiResponse[CourseRead])
async def get_admin_course(
    course_slug: str,
    include_archived: bool = Query(default=False),
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    hierarchy = await use_cases(uow).get_course(course_slug, include_archived=include_archived)
    return ApiResponse(data=course_read(hierarchy.course, hierarchy.modules, hierarchy.sections_by_module), meta={})


@learner_router.get("/{course_slug}", response_model=ApiResponse[CourseRead])
async def get_learner_course(
    course_slug: str,
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    hierarchy = await use_cases(uow).get_course(course_slug)
    if hierarchy.course.status is not ContentStatus.PUBLISHED:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="course not found")
    await require_learner_enrollment(uow, user, hierarchy.course.id)
    modules = [module for module in hierarchy.modules if module.status is ContentStatus.PUBLISHED]
    sections_by_module = {
        module.id: [section for section in hierarchy.sections_by_module.get(module.id, []) if section.status is ContentStatus.PUBLISHED]
        for module in modules
    }
    sections = [section for group in sections_by_module.values() for section in group]
    access = await LearnerProgressUseCases(lambda: uow).section_access_map(user.id, hierarchy.course.id, sections)
    for section in sections:
        if not access.get(section.id, False):
            section.body = None
    return ApiResponse(data=course_read(hierarchy.course, modules, sections_by_module, access), meta={})


@learner_router.get("/{course_slug}/progress", response_model=ApiResponse[CourseProgressRead])
async def get_course_progress(
    course_slug: str,
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    progress = await LearnerProgressUseCases(lambda: uow).course_progress(course_slug, user.id)
    return ApiResponse(data=course_progress_read(progress), meta={})


@learner_router.put(
    "/{course_slug}/progress/position",
    response_model=ApiResponse[CourseWatchPositionRead],
)
async def put_course_progress_position(
    course_slug: str,
    payload: CourseWatchPositionWrite,
    user: CurrentUser = Depends(require_roles("learner")),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    position = await LearnerProgressUseCases(lambda: uow).record_position(
        course_slug, user.id, payload.module_slug, payload.section_slug
    )
    return ApiResponse(
        data=CourseWatchPositionRead(**position.__dict__),
        meta={},
    )


@admin_router.patch("/{course_slug}", response_model=ApiResponse[CourseRead])
async def update_course(
    course_slug: str,
    payload: CourseUpdate,
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    course = await use_cases(uow).update_course(course_slug, payload.model_dump(exclude_unset=True))
    return ApiResponse(data=course_read(course), meta={"resource": "course"})


@admin_router.delete("/{course_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_slug: str,
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    await use_cases(uow).delete_course(course_slug)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
