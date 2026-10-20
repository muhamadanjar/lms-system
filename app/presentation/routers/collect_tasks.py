from uuid import UUID
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response

from app.application.dto.task_file_upload import MAX_TASK_FILES_PER_SUBMISSION, MAX_TASK_FILE_BYTES, MAX_TASK_SUBMISSION_BYTES, TaskFileUpload
from app.application.ports.auth import CurrentUser
from app.application.ports.notification_publisher import NotificationPublisherPort
from app.application.use_cases.collect_tasks import CollectTaskUseCases
from app.domain.entities.collect_task import CollectTaskStatus
from app.domain.exceptions import ValidationError
from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.notifications.dependencies import (
    get_user_management_notification_publisher,
)
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.infrastructure.storage.dependencies import get_file_storage
from app.infrastructure.storage.file_storage import ConfiguredFileStorage
from app.presentation.dependencies.auth import get_current_user, require_content_editor
from app.presentation.schemas.collect_tasks import (
    CollectTaskFileUploadRead,
    CollectTaskRead,
    CollectTaskReviewCourseRead,
    CollectTaskReviewItemRead,
    CollectTaskReviewRequest,
    CollectTaskSubmissionRequest,
    collect_task_file_upload_read,
    collect_task_read,
    collect_task_review_read,
)
from app.presentation.schemas.content import ApiResponse

learner_router = APIRouter(tags=["Learner Collect Tasks"])
admin_router = APIRouter(tags=["Admin Collect Tasks"])
learner_files_router = APIRouter(tags=["Learner Files"])
admin_files_router = APIRouter(tags=["Admin Files"])
_section_path = "/api/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}/collect-task"
_learner_section_path = "/api/learner/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}/collect-task"


@learner_router.post(_learner_section_path + "/submissions", response_model=ApiResponse[CollectTaskRead])
async def submit_collect_task(course_slug: str, module_slug: str, section_slug: str, payload: CollectTaskSubmissionRequest, user: CurrentUser = Depends(get_current_user), uow: SqlModelUnitOfWork = Depends(get_uow)):
    task = await CollectTaskUseCases(lambda: uow).submit(user, course_slug, module_slug, section_slug, payload.text, [str(url) for url in payload.evidence_urls], file_ids=payload.file_ids)
    return ApiResponse(data=collect_task_read(task), meta={})


@learner_router.post(_learner_section_path + "/files", response_model=ApiResponse[CollectTaskFileUploadRead])
async def upload_collect_task_file(
    course_slug: str,
    module_slug: str,
    section_slug: str,
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
    storage: ConfiguredFileStorage = Depends(get_file_storage),
):
    content = await file.read(MAX_TASK_FILE_BYTES + 1)
    if len(content) > MAX_TASK_FILE_BYTES:
        raise ValidationError("each uploaded file must be between 1 byte and 25 MB")
    metadata = await CollectTaskUseCases(lambda: uow).upload_file(
        user,
        course_slug,
        module_slug,
        section_slug,
        TaskFileUpload(filename=file.filename or "", content=content),
        storage,
    )
    return ApiResponse(data=collect_task_file_upload_read(metadata), meta={})


@learner_router.delete(_learner_section_path + "/files/{file_id}", status_code=204)
async def discard_collect_task_file(
    course_slug: str,
    module_slug: str,
    section_slug: str,
    file_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
    storage: ConfiguredFileStorage = Depends(get_file_storage),
):
    await CollectTaskUseCases(lambda: uow).discard_uploaded_file(
        user, course_slug, module_slug, section_slug, file_id, storage
    )
    return Response(status_code=204)


@learner_router.post(_learner_section_path + "/submissions/files", response_model=ApiResponse[CollectTaskRead])
async def submit_collect_task_files(
    course_slug: str,
    module_slug: str,
    section_slug: str,
    text: str = Form(min_length=1, max_length=50000),
    evidence_urls: list[str] = Form(default=[]),
    files: list[UploadFile] = File(default=[]),
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
    storage: ConfiguredFileStorage = Depends(get_file_storage),
):
    if len(files) > MAX_TASK_FILES_PER_SUBMISSION:
        raise ValidationError("at most 10 files may be submitted")
    uploads = []
    total = 0
    for upload in files:
        content = await upload.read(MAX_TASK_FILE_BYTES + 1)
        total += len(content)
        if len(content) > MAX_TASK_FILE_BYTES or total > MAX_TASK_SUBMISSION_BYTES:
            raise ValidationError("uploaded files exceed the configured size limit")
        uploads.append(TaskFileUpload(filename=upload.filename or "", content=content))
    use_cases = CollectTaskUseCases(lambda: uow)
    file_ids = []
    try:
        for upload in uploads:
            metadata = await use_cases.upload_file(
                user, course_slug, module_slug, section_slug, upload, storage
            )
            file_ids.append(metadata.id)
        task = await use_cases.submit(
            user,
            course_slug,
            module_slug,
            section_slug,
            text,
            evidence_urls,
            file_ids=file_ids,
        )
    except Exception:
        for file_id in file_ids:
            try:
                await use_cases.discard_uploaded_file(
                    user, course_slug, module_slug, section_slug, file_id, storage
                )
            except Exception:
                pass
        raise
    return ApiResponse(data=collect_task_read(task), meta={})


@learner_router.get(_learner_section_path, response_model=ApiResponse[CollectTaskRead | None])
async def get_my_collect_task(course_slug: str, module_slug: str, section_slug: str, user: CurrentUser = Depends(get_current_user), uow: SqlModelUnitOfWork = Depends(get_uow)):
    task = await CollectTaskUseCases(lambda: uow).mine(user, course_slug, module_slug, section_slug)
    return ApiResponse(data=collect_task_read(task) if task else None, meta={})


@admin_router.get("/api/admin/collect-tasks/review-courses", response_model=ApiResponse[list[CollectTaskReviewCourseRead]])
async def list_collect_task_review_courses(
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    courses = await CollectTaskUseCases(lambda: uow).list_review_courses(user)
    return ApiResponse(
        data=[
            CollectTaskReviewCourseRead(id=course.id, slug=str(course.slug), title=course.title)
            for course in courses
        ],
        meta={},
    )


@admin_router.get("/api/admin/collect-tasks", response_model=ApiResponse[list[CollectTaskReviewItemRead]])
async def list_collect_tasks_for_review(
    status: list[CollectTaskStatus] | None = Query(default=None),
    course_id: UUID | None = Query(default=None),
    learner_id: list[str] | None = Query(default=None),
    learner_search: str | None = Query(default=None, max_length=255),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
):
    result = await CollectTaskUseCases(lambda: uow).list_for_review(
        user,
        status,
        course_id=course_id,
        learner_ids=learner_id,
        learner_search=learner_search,
        page=page,
        per_page=per_page,
    )
    return ApiResponse(
        data=[collect_task_review_read(item) for item in result.items],
        meta={
            "pagination": {
                "page": result.page,
                "per_page": result.per_page,
                "total": result.total,
                "total_pages": max(1, (result.total + result.per_page - 1) // result.per_page),
            }
        },
    )


@admin_router.post("/api/admin/collect-tasks/{task_id}/review", response_model=ApiResponse[CollectTaskRead])
async def review_collect_task(
    task_id: UUID,
    payload: CollectTaskReviewRequest,
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
    notification_publisher: NotificationPublisherPort = Depends(
        get_user_management_notification_publisher
    ),
):
    task = await CollectTaskUseCases(
        lambda: uow,
        notification_publisher=notification_publisher,
    ).review(user, task_id, payload.action, score=payload.score, note=payload.note)
    return ApiResponse(data=collect_task_read(task), meta={})


async def download_task_file(
    file_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    uow: SqlModelUnitOfWork = Depends(get_uow),
    storage: ConfiguredFileStorage = Depends(get_file_storage),
):
    metadata, content = await CollectTaskUseCases(lambda: uow).read_file(user, file_id, storage)
    filename = quote(metadata.original_filename, safe="")
    return Response(
        content=content,
        media_type=metadata.content_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}",
            "Content-Length": str(len(content)),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


learner_files_router.add_api_route(
    "/api/learner/files/{file_id}",
    download_task_file,
    methods=["GET"],
    name="download_learner_task_file",
)
admin_files_router.add_api_route(
    "/api/admin/files/{file_id}",
    download_task_file,
    methods=["GET"],
    dependencies=[Depends(require_content_editor)],
    name="download_admin_task_file",
)
