from dataclasses import asdict

from fastapi import APIRouter, Depends

from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.presentation.dependencies.auth import require_content_editor
from app.presentation.schemas.content import ApiResponse
from app.presentation.schemas.lms_overview import LmsOverviewRead

# Prefix terpisah: /api/admin/courses/overview akan ketelan route /{course_slug}.
admin_lms_router = APIRouter(prefix="/api/admin/lms", tags=["Admin LMS Overview"])


@admin_lms_router.get("/overview", response_model=ApiResponse[LmsOverviewRead])
async def lms_overview(
    _user=Depends(require_content_editor),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    """Enam KPI agregat lintas course untuk halaman overview admin."""
    async with uow:
        values = await uow.overviews.overview()
    return ApiResponse(
        data=LmsOverviewRead.model_validate(asdict(values)),
        meta={"resource": "lms_overview"},
    )
