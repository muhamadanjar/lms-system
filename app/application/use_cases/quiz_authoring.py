"""Author-only quiz configuration and stable question-code use cases."""

from uuid import UUID, uuid4

from app.application.ports.auth import CurrentUser
from app.domain.entities.answer import Answer
from app.domain.entities.question import Question
from app.domain.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.domain.value_objects.content import QuestionType, SectionContentType
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

    async def configure(self, actor: CurrentUser, course_slug: str, module_slug: str, section_slug: str, *, is_exam: bool, max_attempts: int | None, answer_policy: AnswerPolicy, passing_score: int | None = None):
        self._require_editor(actor)
        async with self.uow as uow:
            quiz = await self.quiz_for_path(course_slug, module_slug, section_slug)
            quiz.configure_assessment(is_exam=is_exam, max_attempts=max_attempts, answer_policy=answer_policy, passing_score=passing_score)
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

    async def list_course_questions(self, actor: CurrentUser, course_slug: str, quiz_slug: str):
        self._require_editor(actor)
        async with self.uow as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            quiz = await uow.quizzes.get_by_course_slug(course.id, quiz_slug)
            if quiz is None:
                raise NotFoundError("quiz not found")
            questions = await uow.quizzes.list_questions(quiz.id)
            result = [(question, await uow.quizzes.list_answers(question)) for question in questions]
            await uow.rollback()
            return quiz, result

    async def save_course_question(self, actor: CurrentUser, course_slug: str, quiz_slug: str, *, question_slug: str | None, prompt: str, options: list[dict[str, object]]):
        self._require_editor(actor)
        async with self.uow as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            quiz = await uow.quizzes.get_by_course_slug(course.id, quiz_slug)
            if quiz is None:
                raise NotFoundError("quiz not found")
            existing = await uow.quizzes.get_question_by_slug(quiz.id, question_slug) if question_slug else None
            if question_slug and existing is None:
                raise NotFoundError("question not found")
            if existing is not None and existing.question_type is not QuestionType.MULTICHOICE:
                raise ValidationError("only MULTICHOICE questions can be managed here")
            position = existing.position if existing else len(await uow.quizzes.list_questions(quiz.id))
            question = existing or Question(quiz_id=quiz.id, slug=f"question-{uuid4().hex[:20]}", prompt=prompt, position=position)
            question.prompt = prompt.strip()
            question.touch()
            answers = [Answer(question_id=question.id, slug=f"option-{uuid4().hex[:20]}", value=str(option["value"]), position=index, is_correct=bool(option["is_correct"])) for index, option in enumerate(options)]
            saved_question, saved_answers = await uow.quizzes.save_question_with_answers(question, answers)
            await uow.commit()
            return saved_question, saved_answers

    async def delete_course_question(self, actor: CurrentUser, course_slug: str, quiz_slug: str, question_slug: str) -> None:
        self._require_editor(actor)
        async with self.uow as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            quiz = await uow.quizzes.get_by_course_slug(course.id, quiz_slug)
            if quiz is None:
                raise NotFoundError("quiz not found")
            await uow.quizzes.delete_question(quiz.id, question_slug)
            remaining = await uow.quizzes.list_questions(quiz.id)
            if remaining:
                await uow.quizzes.reorder_questions(quiz.id, [str(item.slug) for item in remaining])
            await uow.commit()

    async def reorder_course_questions(self, actor: CurrentUser, course_slug: str, quiz_slug: str, ordered_slugs: list[str]) -> None:
        self._require_editor(actor)
        async with self.uow as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            quiz = await uow.quizzes.get_by_course_slug(course.id, quiz_slug)
            if quiz is None:
                raise NotFoundError("quiz not found")
            await uow.quizzes.reorder_questions(quiz.id, ordered_slugs)
            await uow.commit()
