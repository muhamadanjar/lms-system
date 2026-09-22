from fastapi import APIRouter, Depends, Query, Response, status

from app.application.ports.auth import CurrentUser
from app.domain.value_objects.content import ContentStatus
from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.presentation.dependencies.auth import get_current_user, require_content_editor
from app.presentation.routers.courses import can_manage, use_cases
from app.presentation.schemas.content import ApiResponse, OrderRequest, PaginationQuery, SectionCreate, SectionRead, SectionUpdate, section_read

router = APIRouter(prefix="/api/courses/{course_slug}/modules/{module_slug}/sections", tags=["Sections"])


@router.get("", response_model=ApiResponse[list[SectionRead]])
async def list_sections(
    course_slug: str,
    module_slug: str,
    query: PaginationQuery = Depends(),
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    status_filter = query.status if can_manage(user) else ContentStatus.PUBLISHED
    sections, total, course, module = await use_cases(uow).list_sections(course_slug, module_slug, status_filter, query.include_archived and can_manage(user), (query.page - 1) * query.page_size, query.page_size)
    if not can_manage(user) and (course.status is not ContentStatus.PUBLISHED or module.status is not ContentStatus.PUBLISHED):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="module not found")
    if not can_manage(user):
        sections = [section for section in sections if section.status is ContentStatus.PUBLISHED]
    return ApiResponse(data=[section_read(section) for section in sections], meta={"page": query.page, "page_size": query.page_size, "total": total})


@router.post("", response_model=ApiResponse[SectionRead], status_code=status.HTTP_201_CREATED)
async def create_section(
    course_slug: str,
    module_slug: str,
    payload: SectionCreate,
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    section = await use_cases(uow).create_section(course_slug, module_slug, title=payload.title, description=payload.description, slug=payload.slug, position=payload.position, status=payload.status, content_type=payload.content_type, body=payload.body)
    return ApiResponse(data=section_read(section), meta={"resource": "section"})


@router.put("/order", response_model=ApiResponse[dict[str, str]])
async def reorder_sections(
    course_slug: str,
    module_slug: str,
    payload: OrderRequest,
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    sections, _, _, _ = await use_cases(uow).list_sections(course_slug, module_slug, None, True, 0, 100000)
    by_slug = {section.slug: section.id for section in sections}
    if set(item.slug for item in payload.items) != set(by_slug):
        from fastapi import HTTPException
        raise HTTPException(status_code=422, detail="order items must contain exactly the module sections")
    ordered_ids = [by_slug[item.slug] for item in sorted(payload.items, key=lambda item: item.position)]
    await use_cases(uow).reorder_sections(course_slug, module_slug, ordered_ids)
    return ApiResponse(data={"status": "reordered"}, meta={})


@router.get("/{section_slug}", response_model=ApiResponse[SectionRead])
async def get_section(
    course_slug: str,
    module_slug: str,
    section_slug: str,
    include_archived: bool = Query(default=False),
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    course, module, section = await use_cases(uow).get_section(course_slug, module_slug, section_slug, include_archived and can_manage(user))
    if not can_manage(user) and (course.status is not ContentStatus.PUBLISHED or module.status is not ContentStatus.PUBLISHED or section.status is not ContentStatus.PUBLISHED):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="section not found")
    return ApiResponse(data=section_read(section), meta={})


@router.patch("/{section_slug}", response_model=ApiResponse[SectionRead])
async def update_section(
    course_slug: str,
    module_slug: str,
    section_slug: str,
    payload: SectionUpdate,
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    section = await use_cases(uow).update_section(course_slug, module_slug, section_slug, payload.model_dump(exclude_unset=True))
    return ApiResponse(data=section_read(section), meta={"resource": "section"})


@router.delete("/{section_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_section(
    course_slug: str,
    module_slug: str,
    section_slug: str,
    _user: CurrentUser = Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    await use_cases(uow).delete_section(course_slug, module_slug, section_slug)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
