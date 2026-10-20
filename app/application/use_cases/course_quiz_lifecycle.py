from collections.abc import Callable

from app.domain.entities.quiz import KnowledgeQuiz
from app.domain.exceptions import NotFoundError, ValidationError
from app.domain.services.content_policy import validate_status_transition
from app.domain.value_objects.content import ContentStatus, Slug


class CourseQuizLifecycleUseCases:
    def __init__(self, uow_factory: Callable):
        self.uow_factory = uow_factory

    async def list(self, course_slug: str, offset: int, limit: int) -> tuple[list[tuple[KnowledgeQuiz, dict[str, str] | None]], int]:
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            quizzes = await uow.quizzes.list_by_course(course.id, offset, limit)
            total = await uow.quizzes.count_by_course(course.id)
            records = [(quiz, await uow.quizzes.get_section_reference(quiz.section_id) if quiz.section_id else None) for quiz in quizzes]
            await uow.rollback()
            return records, total

    async def create(self, course_slug: str, *, slug: str, title: str, description: str | None, status: ContentStatus) -> KnowledgeQuiz:
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            quiz = KnowledgeQuiz(course_id=course.id, slug=Slug(slug), title=title, description=description, status=status)
            result = await uow.quizzes.create_quiz(quiz)
            await uow.commit()
            return result

    async def update(self, course_slug: str, quiz_slug: str, changes: dict[str, object]) -> tuple[KnowledgeQuiz, dict[str, str] | None]:
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            quiz = await uow.quizzes.get_by_course_slug(course.id, quiz_slug)
            if quiz is None:
                raise NotFoundError("quiz not found")
            if any(key in changes for key in ("title", "description", "slug")):
                if "title" in changes and changes["title"] is None:
                    raise ValidationError("title cannot be null")
                if "slug" in changes and changes["slug"] is None:
                    raise ValidationError("slug cannot be null")
                quiz.rename(changes.get("title", quiz.title), changes.get("description", quiz.description), changes.get("slug"))
            if changes.get("status") is not None:
                target = ContentStatus(changes["status"])
                validate_status_transition(quiz.status, target)
                quiz.change_status(target)
            if any(key in changes for key in ("is_exam", "max_attempts", "answer_policy", "passing_score")):
                quiz.configure_assessment(is_exam=changes.get("is_exam", quiz.is_exam), max_attempts=changes.get("max_attempts", quiz.max_attempts), answer_policy=changes.get("answer_policy", quiz.answer_policy), passing_score=changes.get("passing_score"))
            result = await uow.quizzes.update_quiz(quiz)
            section = await uow.quizzes.get_section_reference(quiz.section_id) if quiz.section_id else None
            await uow.commit()
            return result, section

    async def delete(self, course_slug: str, quiz_slug: str) -> None:
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            await uow.quizzes.delete_standalone(course.id, quiz_slug)
            await uow.commit()

    async def link(self, course_slug: str, module_slug: str, section_slug: str, quiz_slug: str):
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            quiz = await uow.quizzes.link_to_section(course.id, quiz_slug, module_slug, section_slug)
            section = await uow.quizzes.get_section_reference(quiz.section_id)
            await uow.commit()
            return quiz, section

    async def unlink(self, course_slug: str, module_slug: str, section_slug: str) -> None:
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            await uow.quizzes.unlink_from_section(course.id, module_slug, section_slug)
            await uow.commit()
