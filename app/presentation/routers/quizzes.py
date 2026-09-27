from fastapi import APIRouter, Depends, Response, status
from uuid import UUID

from app.application.dto.quiz_sittings import AnswerSelectionInput, QuizSittingResultDTO
from app.application.ports.auth import CurrentUser
from app.application.use_cases.quiz_authoring import QuizAuthoringUseCases
from app.application.use_cases.quiz_sittings import QuizSittingUseCases
from app.infrastructure.database.dependencies import get_uow
from app.infrastructure.persistence.unit_of_work import SqlModelUnitOfWork
from app.presentation.dependencies.auth import get_current_user
from app.presentation.schemas.content import ApiResponse
from app.presentation.schemas.quiz_attempt_policy import QuizConfigurationRequest
from app.presentation.schemas.quiz_questions import QuizQuestionCreate, QuizQuestionRead, QuizQuestionUpdate
from app.presentation.schemas.quiz_sittings import (
    QuizResultSummaryRead,
    QuizSittingDraftRead,
    QuizSittingResultRead,
    SaveSelectionsRequest,
    draft_read,
    result_read,
    summary_read,
)


router = APIRouter(tags=["Quizzes"])
_nested_prefix = "/api/courses/{course_slug}/modules/{module_slug}/sections/{section_slug}/quiz"


@router.patch(_nested_prefix, response_model=ApiResponse[dict[str, object]])
async def configure_quiz(course_slug: str, module_slug: str, section_slug: str, payload: QuizConfigurationRequest, user: CurrentUser = Depends(get_current_user), uow: SqlModelUnitOfWork = Depends(get_uow)):
    quiz = await QuizAuthoringUseCases(uow).configure(user, course_slug, module_slug, section_slug, is_exam=payload.is_exam, max_attempts=payload.max_attempts, answer_policy=payload.answer_policy)
    return ApiResponse(data={"id": str(quiz.id), "is_exam": quiz.is_exam, "max_attempts": quiz.max_attempts, "answer_policy": str(quiz.answer_policy)}, meta={})


@router.post(_nested_prefix + "/questions", response_model=ApiResponse[QuizQuestionRead], status_code=status.HTTP_201_CREATED)
async def create_quiz_question(course_slug: str, module_slug: str, section_slug: str, payload: QuizQuestionCreate, user: CurrentUser = Depends(get_current_user), uow: SqlModelUnitOfWork = Depends(get_uow)):
    question = await QuizAuthoringUseCases(uow).create_question(user, course_slug, module_slug, section_slug, prompt=payload.prompt, question_code=payload.question_code)
    return ApiResponse(data=QuizQuestionRead(id=str(question.id), slug=str(question.slug), prompt=question.prompt, question_code=str(question.question_code)), meta={})


@router.patch(_nested_prefix + "/questions/{question_slug}", response_model=ApiResponse[QuizQuestionRead])
async def update_quiz_question(course_slug: str, module_slug: str, section_slug: str, question_slug: str, payload: QuizQuestionUpdate, user: CurrentUser = Depends(get_current_user), uow: SqlModelUnitOfWork = Depends(get_uow)):
    authoring = QuizAuthoringUseCases(uow)
    async with uow:
        quiz = await authoring.quiz_for_path(course_slug, module_slug, section_slug)
        await uow.rollback()
    question = await authoring.update_question_code(user, quiz.id, question_slug, payload.question_code)
    return ApiResponse(data=QuizQuestionRead(id=str(question.id), slug=str(question.slug), prompt=question.prompt, question_code=str(question.question_code)), meta={})


@router.post(_nested_prefix + "/sittings", response_model=ApiResponse[QuizSittingDraftRead])
async def start_sitting(course_slug: str, module_slug: str, section_slug: str, response: Response, user: CurrentUser = Depends(get_current_user), uow: SqlModelUnitOfWork = Depends(get_uow)):
    sitting, created = await QuizSittingUseCases(uow).start_or_resume_for_path(course_slug, module_slug, section_slug, user.id)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return ApiResponse(data=draft_read(sitting), meta={"resumed": not created})


@router.put("/api/quiz-sittings/{sitting_id}/answers", response_model=ApiResponse[QuizSittingDraftRead])
async def save_sitting_answers(sitting_id: UUID, payload: SaveSelectionsRequest, user: CurrentUser = Depends(get_current_user), uow: SqlModelUnitOfWork = Depends(get_uow)):
    inputs = tuple(AnswerSelectionInput(question_code=item.question_code, option_ids=tuple(item.option_ids)) for item in payload.answers)
    draft = await QuizSittingUseCases(uow).save_selections(sitting_id, user.id, inputs)
    return ApiResponse(data=draft_read(draft), meta={})


@router.post("/api/quiz-sittings/{sitting_id}/finalize", response_model=ApiResponse[QuizSittingResultRead])
async def finalize_sitting(sitting_id: UUID, user: CurrentUser = Depends(get_current_user), uow: SqlModelUnitOfWork = Depends(get_uow)):
    result = await QuizSittingUseCases(uow).finalize(sitting_id, user.id)
    return ApiResponse(data=result_read(result), meta={})


@router.get("/api/quiz-sittings/{sitting_id}", response_model=ApiResponse[QuizSittingDraftRead | QuizSittingResultRead])
async def get_sitting(sitting_id: UUID, user: CurrentUser = Depends(get_current_user), uow: SqlModelUnitOfWork = Depends(get_uow)):
    value = await QuizSittingUseCases(uow).get(sitting_id, user.id)
    data = result_read(value) if isinstance(value, QuizSittingResultDTO) else draft_read(value)
    return ApiResponse(data=data, meta={})


@router.get(_nested_prefix + "/result", response_model=ApiResponse[QuizResultSummaryRead])
async def get_quiz_result_summary(course_slug: str, module_slug: str, section_slug: str, user: CurrentUser = Depends(get_current_user), uow: SqlModelUnitOfWork = Depends(get_uow)):
    summary = await QuizSittingUseCases(uow).summary_for_path(course_slug, module_slug, section_slug, user.id)
    return ApiResponse(data=summary_read(summary), meta={})
