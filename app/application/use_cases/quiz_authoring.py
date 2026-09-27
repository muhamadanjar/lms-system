"""Author-only quiz configuration and stable question-code use cases."""

from uuid import UUID, uuid4

from app.application.ports.auth import CurrentUser
from app.domain.entities.question import Question
from app.domain.exceptions import AuthorizationError, NotFoundError
from app.domain.value_objects.content import SectionContentType
from app.domain.value_objects.quiz_assessment import AnswerPolicy


class QuizAuthoringUseCases:
    def __init__(self, uow):
        self.uow = uow

    @staticmethod
    def _require_editor(actor: CurrentUser) -> None:
        if not actor.is_superuser and not actor.has_any_role(("admin", "instructor")):
            raise AuthorizationError("content editor role is required")

    async def quiz_for_path(self, course_slug: str, module_slug: str, section_slug: str):
        course = await self.uow.courses.get_by_slug(course_slug)
        if course is None:
            raise NotFoundError("course not found")
        module = await self.uow.modules.get_by_slug(course.id, module_slug)
        if module is None:
            raise NotFoundError("module not found")
        section = await self.uow.sections.get_by_slug(module.id, section_slug)
        if section is None or section.content_type is not SectionContentType.QUIZ:
            raise NotFoundError("quiz section not found")
        quiz = await self.uow.quizzes.get_by_section(section.id)
        if quiz is None:
            raise NotFoundError("quiz not found")
        return quiz

    async def configure(self, actor: CurrentUser, course_slug: str, module_slug: str, section_slug: str, *, is_exam: bool, max_attempts: int | None, answer_policy: AnswerPolicy):
        self._require_editor(actor)
        async with self.uow as uow:
            quiz = await self.quiz_for_path(course_slug, module_slug, section_slug)
            quiz.configure_assessment(is_exam=is_exam, max_attempts=max_attempts, answer_policy=answer_policy)
            await uow.quizzes.update_quiz(quiz)
            await uow.commit()
            return quiz

    async def create_question(self, actor: CurrentUser, course_slug: str, module_slug: str, section_slug: str, *, prompt: str, question_code: str | None) -> Question:
        self._require_editor(actor)
        async with self.uow as uow:
            quiz = await self.quiz_for_path(course_slug, module_slug, section_slug)
            position = len(await uow.quizzes.list_questions(quiz.id))
            question = Question(quiz_id=quiz.id, slug=f"question-{uuid4().hex[:20]}", prompt=prompt, position=position, question_code=question_code)
            await uow.quizzes.create_question(question)
            await uow.commit()
            return question

    async def update_question_code(self, actor: CurrentUser, quiz_id: UUID, question_slug: str, question_code: str) -> Question:
        self._require_editor(actor)
        async with self.uow as uow:
            question = await uow.quizzes.get_question_by_slug(quiz_id, question_slug)
            if question is None:
                raise NotFoundError("question not found")
            question.change_question_code(question_code)
            await uow.quizzes.update_question(question)
            await uow.commit()
            return question
