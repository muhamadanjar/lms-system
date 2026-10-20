from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.presentation.dependencies.auth import require_content_editor
from app.presentation.schemas.content import ApiResponse
from app.presentation.schemas.enrollment import AdminEnrollmentRead

admin_router = APIRouter(prefix="/api/admin/enrollments", tags=["Admin Enrollment"])


@admin_router.get("", response_model=ApiResponse[list[AdminEnrollmentRead]])
async def list_all_enrollments(
    search: str | None = Query(default=None, max_length=120),
    course_slug: str | None = Query(default=None, max_length=160),
    enrolled_from: datetime | None = None,
    enrolled_to: datetime | None = None,
    status: Literal["ENROLLED", "COMPLETED", "WITHDRAWN"] | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _user=Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    async with uow:
        rows, total = await uow.enrollments.list_admin(
            search=search,
            course_slug=course_slug,
            enrolled_from=enrolled_from,
            enrolled_to=enrolled_to,
            status=status,
            offset=(page - 1) * page_size,
            limit=page_size,
        )
    return ApiResponse(
        data=[
            AdminEnrollmentRead.model_validate(
                {
                    **enrollment.__dict__,
                    "course_slug": slug,
                    "course_title": title,
                }
            )
            for enrollment, slug, title in rows
        ],
        meta={"page": page, "page_size": page_size, "total": total, "resource": "enrollments"},
    )
