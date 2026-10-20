from fastapi import APIRouter, Depends, Query, Response, status

from app.application.ports.auth import CurrentUser
from app.application.use_cases.learner_progress import LearnerProgressUseCases
from app.application.use_cases.content_crud import ContentCrudUseCases
from app.domain.value_objects.content import ContentStatus
from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.presentation.dependencies.auth import get_current_user, require_content_editor
from app.presentation.routers.courses import can_manage, require_learner_enrollment, use_cases
from app.presentation.schemas.content import ApiResponse, ModuleCreate, ModuleRead, ModuleUpdate, OrderRequest, PaginationQuery, module_read

admin_router = APIRouter(prefix="/api/admin/courses/{course_slug}/modules", tags=["Admin Modules"])
learner_router = APIRouter(prefix="/api/learner/courses/{course_slug}/modules", tags=["Learner Modules"])


def read_filter(query: PaginationQuery, user: CurrentUser) -> tuple[ContentStatus | None, bool]:
    return (query.status, query.include_archived) if can_manage(user) else (ContentStatus.PUBLISHED, False)


async def list_modules(
    course_slug: str,
    query: PaginationQuery = Depends(),
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    status_filter, include_archived = read_filter(query, user)
    modules, total, course = await use_cases(uow).list_modules(course_slug, status_filter, include_archived, (query.page - 1) * query.page_size, query.page_size)
    if not can_manage(user) and course.status is not ContentStatus.PUBLISHED:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="course not found")
    if not can_manage(user):
        await require_learner_enrollment(uow, user, course.id)
    if not can_manage(user):
        modules = [module for module in modules if module.status is ContentStatus.PUBLISHED]
    return ApiResponse(data=[module_read(module) for module in modules], meta={"page": query.page, "page_size": query.page_size, "total": total})


@admin_router.get("", response_model=ApiResponse[list[ModuleRead]])
async def list_admin_modules(
    course_slug: str,
    query: PaginationQuery = Depends(),
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    modules, total, _course = await use_cases(uow).list_modules(
        course_slug,
        query.status,
        query.include_archived,
        (query.page - 1) * query.page_size,
        query.page_size,
    )
    return ApiResponse(data=[module_read(module) for module in modules], meta={"page": query.page, "page_size": query.page_size, "total": total})


@learner_router.get("", response_model=ApiResponse[list[ModuleRead]])
async def list_learner_modules(
    course_slug: str,
    query: PaginationQuery = Depends(),
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    modules, total, course = await use_cases(uow).list_modules(
        course_slug,
        ContentStatus.PUBLISHED,
        False,
        (query.page - 1) * query.page_size,
        query.page_size,
    )
    if course.status is not ContentStatus.PUBLISHED:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="course not found")
    await require_learner_enrollment(uow, user, course.id)
    return ApiResponse(data=[module_read(module) for module in modules], meta={"page": query.page, "page_size": query.page_size, "total": total})


@admin_router.post("", response_model=ApiResponse[ModuleRead], status_code=status.HTTP_201_CREATED)
async def create_module(
    course_slug: str,
    payload: ModuleCreate,
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    module = await use_cases(uow).create_module(course_slug, title=payload.title, description=payload.description, slug=payload.slug, position=payload.position, status=payload.status)
    return ApiResponse(data=module_read(module), meta={"resource": "module"})


@admin_router.put("/order", response_model=ApiResponse[dict[str, str]])
async def reorder_modules(
    course_slug: str,
    payload: OrderRequest,
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    modules, _, _ = await use_cases(uow).list_modules(course_slug, None, True, 0, 100000)
    by_slug = {module.slug: module.id for module in modules}
    if set(item.slug for item in payload.items) != set(by_slug):
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="order items must contain exactly the course modules")
    ordered_ids = [by_slug[item.slug] for item in sorted(payload.items, key=lambda item: item.position)]
    await use_cases(uow).reorder_modules(course_slug, ordered_ids)
    return ApiResponse(data={"status": "reordered"}, meta={})


async def get_module(
    course_slug: str,
    module_slug: str,
    include_archived: bool = Query(default=False),
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    course, module, sections = await use_cases(uow).get_module(course_slug, module_slug, include_archived=include_archived and can_manage(user))
    if not can_manage(user) and (course.status is not ContentStatus.PUBLISHED or module.status is not ContentStatus.PUBLISHED):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="module not found")
    if not can_manage(user):
        await require_learner_enrollment(uow, user, course.id)
        sections = [section for section in sections if section.status is ContentStatus.PUBLISHED]
        access = await LearnerProgressUseCases(lambda: uow).section_access_map(user.id, course.id, sections)
        for section in sections:
            if not access.get(section.id, False):
                section.body = None
    else:
        access = {}
    return ApiResponse(data=module_read(module, sections, access), meta={})


@admin_router.get("/{module_slug}", response_model=ApiResponse[ModuleRead])
async def get_admin_module(
    course_slug: str,
    module_slug: str,
    include_archived: bool = Query(default=False),
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    _course, module, sections = await use_cases(uow).get_module(
        course_slug, module_slug, include_archived=include_archived
    )
    return ApiResponse(data=module_read(module, sections), meta={})


@learner_router.get("/{module_slug}", response_model=ApiResponse[ModuleRead])
async def get_learner_module(
    course_slug: str,
    module_slug: str,
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    # include_archived=True: fetch first, then 404 below when not published.
    course, module, sections = await use_cases(uow).get_module(course_slug, module_slug, include_archived=True)
    if course.status is not ContentStatus.PUBLISHED or module.status is not ContentStatus.PUBLISHED:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="module not found")
    await require_learner_enrollment(uow, user, course.id)
    sections = [section for section in sections if section.status is ContentStatus.PUBLISHED]
    access = await LearnerProgressUseCases(lambda: uow).section_access_map(user.id, course.id, sections)
    for section in sections:
        if not access.get(section.id, False):
            section.body = None
    return ApiResponse(data=module_read(module, sections, access), meta={})


@admin_router.patch("/{module_slug}", response_model=ApiResponse[ModuleRead])
async def update_module(
    course_slug: str,
    module_slug: str,
    payload: ModuleUpdate,
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    module = await use_cases(uow).update_module(course_slug, module_slug, payload.model_dump(exclude_unset=True))
    return ApiResponse(data=module_read(module), meta={"resource": "module"})


@admin_router.delete("/{module_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_module(
    course_slug: str,
    module_slug: str,
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    await use_cases(uow).delete_module(course_slug, module_slug)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
