from fastapi import APIRouter, Depends, Response, status
from uuid import UUID

from app.application.dto.quiz_sittings import AnswerSelectionInput, QuizSittingResultDTO
from app.application.ports.auth import CurrentUser
from app.application.use_cases.quiz_authoring import QuizAuthoringUseCases
from app.application.use_cases.quiz_sittings import QuizSittingUseCases
from app.application.use_cases.course_quiz_lifecycle import CourseQuizLifecycleUseCases
from app.domain.entities.answer import Answer
from app.domain.entities.question import Question
from app.domain.exceptions import ValidationError
from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.presentation.dependencies.auth import get_current_user, require_content_editor
from app.presentation.schemas.content import ApiResponse, PaginationQuery
from app.presentation.schemas.quiz_attempt_policy import QuizConfigurationRequest
from app.presentation.schemas.quiz_lifecycle import QuizCreateRequest, QuizLinkRequest, QuizRead, QuizUpdateRequest, quiz_read
from app.presentation.schemas.quiz_questions import QuizQuestionAuthoringInput, QuizQuestionAuthoringRead, QuizQuestionCreate, QuizQuestionOrderRequest, QuizQuestionRead, QuizQuestionUpdate
from app.presentation.schemas.quiz_sittings import (
    QuizResultSummaryRead,
    QuizSittingContentRead,
    QuizSittingDraftRead,
    QuizSittingResultRead,
    SaveSelectionsRequest,
    content_read,
    draft_read,
    result_read,
    summary_read,
)


admin_router = APIRouter(tags=["Admin Quizzes"])
learner_router = APIRouter(tags=["Learner Quizzes"])
_nested_prefix = "/api/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}/quiz"
_admin_nested_prefix = "/api/admin/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}/quiz"
_learner_nested_prefix = "/api/learner/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}/quiz"


def _authoring_question_read(question: Question, options: list[Answer]) -> QuizQuestionAuthoringRead:
    return QuizQuestionAuthoringRead(
        id=str(question.id), slug=str(question.slug), prompt=question.prompt,
        question_code=str(question.question_code), position=question.position,
        options=[{"id": str(option.id), "slug": str(option.slug), "value": option.value, "position": option.position, "is_correct": bool(option.is_correct)} for option in options],
    )


@admin_router.get("/api/admin/courses/{course_slug}/quizzes/{quiz_slug}/questions", response_model=ApiResponse[list[QuizQuestionAuthoringRead]])
async def list_course_quiz_questions(course_slug: str, quiz_slug: str, user: CurrentUser = Depends(require_content_editor), uow: SqlModelUnitOfWork = Depends(get_uow)):
    _quiz, records = await QuizAuthoringUseCases(uow).list_course_questions(user, course_slug, quiz_slug)
    return ApiResponse(data=[_authoring_question_read(question, options) for question, options in records], meta={})


@admin_router.post("/api/admin/courses/{course_slug}/quizzes/{quiz_slug}/questions", response_model=ApiResponse[QuizQuestionAuthoringRead], status_code=status.HTTP_201_CREATED)
async def create_course_quiz_question(course_slug: str, quiz_slug: str, payload: QuizQuestionAuthoringInput, user: CurrentUser = Depends(require_content_editor), uow: SqlModelUnitOfWork = Depends(get_uow)):
    question, options = await QuizAuthoringUseCases(uow).save_course_question(user, course_slug, quiz_slug, question_slug=None, prompt=payload.prompt, options=[option.model_dump() for option in payload.options])
    return ApiResponse(data=_authoring_question_read(question, options), meta={})


@admin_router.put("/api/admin/courses/{course_slug}/quizzes/{quiz_slug}/questions/order", response_model=ApiResponse[dict[str, str]])
async def reorder_course_quiz_questions(course_slug: str, quiz_slug: str, payload: QuizQuestionOrderRequest, user: CurrentUser = Depends(require_content_editor), uow: SqlModelUnitOfWork = Depends(get_uow)):
    items = sorted(payload.items, key=lambda item: item.position)
    if [item.position for item in items] != list(range(len(items))):
        raise ValidationError("positions must be contiguous and start at zero")
    await QuizAuthoringUseCases(uow).reorder_course_questions(user, course_slug, quiz_slug, [item.slug for item in items])
    return ApiResponse(data={"status": "ok"}, meta={})


@admin_router.put("/api/admin/courses/{course_slug}/quizzes/{quiz_slug}/questions/{question_slug}", response_model=ApiResponse[QuizQuestionAuthoringRead])
async def update_course_quiz_question(course_slug: str, quiz_slug: str, question_slug: str, payload: QuizQuestionAuthoringInput, user: CurrentUser = Depends(require_content_editor), uow: SqlModelUnitOfWork = Depends(get_uow)):
    question, options = await QuizAuthoringUseCases(uow).save_course_question(user, course_slug, quiz_slug, question_slug=question_slug, prompt=payload.prompt, options=[option.model_dump() for option in payload.options])
    return ApiResponse(data=_authoring_question_read(question, options), meta={})


@admin_router.delete("/api/admin/courses/{course_slug}/quizzes/{quiz_slug}/questions/{question_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course_quiz_question(course_slug: str, quiz_slug: str, question_slug: str, user: CurrentUser = Depends(require_content_editor), uow: SqlModelUnitOfWork = Depends(get_uow)):
    await QuizAuthoringUseCases(uow).delete_course_question(user, course_slug, quiz_slug, question_slug)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_router.patch(_admin_nested_prefix, response_model=ApiResponse[dict[str, object]])
async def configure_quiz(course_slug: str, module_slug: str, section_slug: str, payload: QuizConfigurationRequest, user: CurrentUser = Depends(require_content_editor), uow: SqlModelUnitOfWork = Depends(get_uow)):
    quiz = await QuizAuthoringUseCases(uow).configure(user, course_slug, module_slug, section_slug, is_exam=payload.is_exam, max_attempts=payload.max_attempts, answer_policy=payload.answer_policy, passing_score=payload.passing_score)
    return ApiResponse(data={"id": str(quiz.id), "is_exam": quiz.is_exam, "max_attempts": quiz.max_attempts, "passing_score": quiz.passing_score, "answer_policy": str(quiz.answer_policy)}, meta={})


@admin_router.post(_admin_nested_prefix + "/questions", response_model=ApiResponse[QuizQuestionRead], status_code=status.HTTP_201_CREATED)
async def create_quiz_question(course_slug: str, module_slug: str, section_slug: str, payload: QuizQuestionCreate, user: CurrentUser = Depends(require_content_editor), uow: SqlModelUnitOfWork = Depends(get_uow)):
    question = await QuizAuthoringUseCases(uow).create_question(user, course_slug, module_slug, section_slug, prompt=payload.prompt, question_code=payload.question_code)
    return ApiResponse(data=QuizQuestionRead(id=str(question.id), slug=str(question.slug), prompt=question.prompt, question_code=str(question.question_code)), meta={})


@admin_router.patch(_admin_nested_prefix + "/questions/{question_slug}", response_model=ApiResponse[QuizQuestionRead])
async def update_quiz_question(course_slug: str, module_slug: str, section_slug: str, question_slug: str, payload: QuizQuestionUpdate, user: CurrentUser = Depends(require_content_editor), uow: SqlModelUnitOfWork = Depends(get_uow)):
    authoring = QuizAuthoringUseCases(uow)
    async with uow:
        quiz = await authoring.quiz_for_path(course_slug, module_slug, section_slug)
        await uow.rollback()
    question = await authoring.update_question_code(user, quiz.id, question_slug, payload.question_code)
    return ApiResponse(data=QuizQuestionRead(id=str(question.id), slug=str(question.slug), prompt=question.prompt, question_code=str(question.question_code)), meta={})


@learner_router.post(_learner_nested_prefix + "/sittings", response_model=ApiResponse[QuizSittingDraftRead])
async def start_sitting(course_slug: str, module_slug: str, section_slug: str, response: Response, user: CurrentUser = Depends(get_current_user), uow: SqlModelUnitOfWork = Depends(get_uow)):
    sitting, created = await QuizSittingUseCases(uow).start_or_resume_for_path(course_slug, module_slug, section_slug, user.id)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return ApiResponse(data=draft_read(sitting), meta={"resumed": not created})


@learner_router.put("/api/learner/quiz-sittings/{sitting_id}/answers", response_model=ApiResponse[QuizSittingDraftRead])
async def save_sitting_answers(sitting_id: UUID, payload: SaveSelectionsRequest, user: CurrentUser = Depends(get_current_user), uow: SqlModelUnitOfWork = Depends(get_uow)):
    inputs = tuple(AnswerSelectionInput(question_code=item.question_code, option_ids=tuple(item.option_ids)) for item in payload.answers)
    draft = await QuizSittingUseCases(uow).save_selections(sitting_id, user.id, inputs)
    return ApiResponse(data=draft_read(draft), meta={})


@learner_router.post("/api/learner/quiz-sittings/{sitting_id}/finalize", response_model=ApiResponse[QuizSittingResultRead])
async def finalize_sitting(sitting_id: UUID, user: CurrentUser = Depends(get_current_user), uow: SqlModelUnitOfWork = Depends(get_uow)):
    result = await QuizSittingUseCases(uow).finalize(sitting_id, user.id)
    quiz = await uow.quizzes.get_by_id(result.quiz_id)
    return ApiResponse(data=result_read(result, include_question_feedback=not quiz.is_exam if quiz else False), meta={})


@learner_router.get("/api/learner/quiz-sittings/{sitting_id}", response_model=ApiResponse[QuizSittingDraftRead | QuizSittingResultRead])
async def get_sitting(sitting_id: UUID, user: CurrentUser = Depends(get_current_user), uow: SqlModelUnitOfWork = Depends(get_uow)):
    value = await QuizSittingUseCases(uow).get(sitting_id, user.id)
    if isinstance(value, QuizSittingResultDTO):
        quiz = await uow.quizzes.get_by_id(value.quiz_id)
        data = result_read(value, include_question_feedback=not quiz.is_exam if quiz else False)
    else:
        data = draft_read(value)
    return ApiResponse(data=data, meta={})


@learner_router.get("/api/learner/quiz-sittings/{sitting_id}/content", response_model=ApiResponse[QuizSittingContentRead])
async def get_sitting_content(sitting_id: UUID, user: CurrentUser = Depends(get_current_user), uow: SqlModelUnitOfWork = Depends(get_uow)):
    content = await QuizSittingUseCases(uow).content(sitting_id, user.id)
    return ApiResponse(data=content_read(content), meta={})


@learner_router.get(_learner_nested_prefix + "/result", response_model=ApiResponse[QuizResultSummaryRead])
async def get_quiz_result_summary(course_slug: str, module_slug: str, section_slug: str, user: CurrentUser = Depends(get_current_user), uow: SqlModelUnitOfWork = Depends(get_uow)):
    summary = await QuizSittingUseCases(uow).summary_for_path(course_slug, module_slug, section_slug, user.id)
    return ApiResponse(data=summary_read(summary), meta={})


@admin_router.get("/api/admin/courses/{course_slug}/quizzes", response_model=ApiResponse[list[QuizRead]])
async def list_course_quizzes(course_slug: str, query: PaginationQuery = Depends(), _user: CurrentUser = Depends(require_content_editor), uow: SqlModelUnitOfWork = Depends(get_uow)):
    records, total = await CourseQuizLifecycleUseCases(lambda: uow).list(course_slug, (query.page - 1) * query.page_size, query.page_size)
    return ApiResponse(data=[quiz_read(quiz, section) for quiz, section in records], meta={"page": query.page, "page_size": query.page_size, "total": total})


@admin_router.post("/api/admin/courses/{course_slug}/quizzes", response_model=ApiResponse[QuizRead], status_code=status.HTTP_201_CREATED)
async def create_course_quiz(course_slug: str, payload: QuizCreateRequest, _user: CurrentUser = Depends(require_content_editor), uow: SqlModelUnitOfWork = Depends(get_uow)):
    quiz = await CourseQuizLifecycleUseCases(lambda: uow).create(course_slug, slug=payload.slug, title=payload.title, description=payload.description, status=payload.status)
    return ApiResponse(data=quiz_read(quiz), meta={})


@admin_router.patch("/api/admin/courses/{course_slug}/quizzes/{quiz_slug}", response_model=ApiResponse[QuizRead])
async def update_course_quiz(course_slug: str, quiz_slug: str, payload: QuizUpdateRequest, _user: CurrentUser = Depends(require_content_editor), uow: SqlModelUnitOfWork = Depends(get_uow)):
    quiz, section = await CourseQuizLifecycleUseCases(lambda: uow).update(course_slug, quiz_slug, payload.model_dump(exclude_unset=True))
    return ApiResponse(data=quiz_read(quiz, section), meta={})


@admin_router.delete("/api/admin/courses/{course_slug}/quizzes/{quiz_slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course_quiz(course_slug: str, quiz_slug: str, _user: CurrentUser = Depends(require_content_editor), uow: SqlModelUnitOfWork = Depends(get_uow)):
    await CourseQuizLifecycleUseCases(lambda: uow).delete(course_slug, quiz_slug)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@admin_router.put("/api/admin/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}/quiz", response_model=ApiResponse[QuizRead])
async def link_course_quiz(course_slug: str, module_slug: str, section_slug: str, payload: QuizLinkRequest, _user: CurrentUser = Depends(require_content_editor), uow: SqlModelUnitOfWork = Depends(get_uow)):
    quiz, section = await CourseQuizLifecycleUseCases(lambda: uow).link(course_slug, module_slug, section_slug, payload.quiz_slug)
    return ApiResponse(data=quiz_read(quiz, section), meta={})


@admin_router.delete("/api/admin/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}/quiz", status_code=status.HTTP_204_NO_CONTENT)
async def unlink_course_quiz(course_slug: str, module_slug: str, section_slug: str, _user: CurrentUser = Depends(require_content_editor), uow: SqlModelUnitOfWork = Depends(get_uow)):
    await CourseQuizLifecycleUseCases(lambda: uow).unlink(course_slug, module_slug, section_slug)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
    content_read,
