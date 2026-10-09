from collections.abc import Callable
from uuid import UUID

from app.domain.exceptions import AuthorizationError, NotFoundError, ValidationError
from app.domain.services.learning_progression import first_blocking_section, require_sequential_access
from app.domain.value_objects.content import ContentStatus, SectionContentType
from app.domain.value_objects.learning_policy import ProgressionMode
from app.domain.value_objects.learning_policy import CompletionMode
from app.application.dto.learner_progress import (
    CourseProgressDTO,
    CourseWatchPositionDTO,
    SectionProgressDTO,
)
from app.domain.entities.collect_task import CollectTaskStatus
from app.domain.entities.enrollment import EnrollmentStatus


class LearnerProgressUseCases:
    """Learner section access and explicit text-material completion workflows."""

    def __init__(self, uow_factory: Callable):
        self.uow_factory = uow_factory

    async def assert_section_access(self, learner_id: str, course_id: UUID, target_section_id: UUID) -> None:
        async with self.uow_factory() as uow:
            await self._assert_section_access(uow, learner_id, course_id, target_section_id)
            await uow.rollback()

    async def mark_text_complete(self, learner_id: str, course_slug: str, module_slug: str, section_slug: str):
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(course_slug)
            module = await uow.modules.get_by_slug(course.id, module_slug) if course else None
            section = await uow.sections.get_by_slug(module.id, section_slug) if module else None
            if section is None or section.content_type is not SectionContentType.MATERIAL:
                raise NotFoundError("text material section not found")
            if course.status is not ContentStatus.PUBLISHED or module.status is not ContentStatus.PUBLISHED or section.status is not ContentStatus.PUBLISHED:
                raise NotFoundError("text material section not found")
            enrollment = await uow.enrollments.get_live(learner_id, course.id)
            if enrollment is None:
                raise AuthorizationError("active course enrollment is required")
            await self._assert_section_access(uow, learner_id, course.id, section.id)
            result = await uow.learning_progress.mark_section_complete(learner_id, section.id)
            await self._refresh_self_learning_completion(uow, learner_id, course)
            await uow.commit()
            return result

    async def section_access_map(self, learner_id: str, course_id: UUID, sections: list) -> dict[UUID, bool]:
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_id(course_id)
            if course is None:
                raise NotFoundError("course not found")
            if course.progression_mode is ProgressionMode.FREE:
                await uow.rollback()
                return {section.id: True for section in sections}
            enrollment = await uow.enrollments.get_live(learner_id, course.id)
            if enrollment is None:
                history = await uow.enrollments.list_history(learner_id, course.id)
                if history and history[0].status == EnrollmentStatus.COMPLETED:
                    await uow.rollback()
                    return {section.id: True for section in sections}
                await uow.rollback()
                return {section.id: False for section in sections}
            hierarchy = await uow.courses.get_hierarchy(course.id)
            ordered = [item for module in (hierarchy.modules if hierarchy else []) if module.status.value == "PUBLISHED" for item in hierarchy.sections_by_module.get(module.id, []) if item.status.value == "PUBLISHED"]
            access: dict[UUID, bool] = {}
            completion = {section.id: await self._section_gate_complete(uow, learner_id, section) for section in ordered}
            for index, section in enumerate(ordered):
                access[section.id] = first_blocking_section(course, ordered[:index], lambda item: completion.get(item.id, False)) is None
            await uow.rollback()
            return {section.id: access.get(section.id, False) for section in sections}

    async def completion_eligible(self, course_slug: str, learner_id: str) -> bool:
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            eligible = await self._completion_eligible(uow, learner_id, course)
            await uow.rollback()
            return eligible

    async def course_progress(self, course_slug: str, learner_id: str) -> CourseProgressDTO:
        """Build the learner's Course Watch state from authoritative LMS records."""
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None:
                raise NotFoundError("course not found")
            history = await uow.enrollments.list_history(learner_id, course.id)
            enrollment = history[0] if history else None
            if enrollment is None or enrollment.status not in {EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED}:
                raise AuthorizationError("active course enrollment is required")
            hierarchy = await uow.courses.get_hierarchy(course.id)
            ordered = [
                (module, section)
                for module in (hierarchy.modules if hierarchy else [])
                if module.status is ContentStatus.PUBLISHED
                for section in hierarchy.sections_by_module.get(module.id, [])
                if section.status is ContentStatus.PUBLISHED
            ]
            section_states = {section.id: await self._section_states(uow, learner_id, section) for _, section in ordered}
            result: list[SectionProgressDTO] = []
            last_opened: CourseWatchPositionDTO | None = None
            for index, (module, section) in enumerate(ordered):
                accessible = enrollment is not None and enrollment.status in {EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED}
                if accessible and course.progression_mode is ProgressionMode.SEQUENTIAL:
                    accessible = first_blocking_section(course, [item for _, item in ordered[:index]], lambda item: section_states.get(item.id, (False, False))[1]) is None
                complete = section_states[section.id][0]
                if section.id == enrollment.last_opened_section_id and accessible:
                    last_opened = CourseWatchPositionDTO(
                        module_slug=str(module.slug),
                        section_slug=str(section.slug),
                    )
                task = await uow.learning_progress.get_task(learner_id, section.id) if section.content_type is SectionContentType.LAB_TASK else None
                if not accessible:
                    state = "LOCKED"
                elif section.content_type is SectionContentType.MATERIAL:
                    state = "COMPLETED" if complete else "AVAILABLE"
                elif section.content_type is SectionContentType.LAB_TASK:
                    state = str(task.status) if task is not None else "AVAILABLE"
                else:
                    quiz = await uow.quizzes.get_by_section(section.id)
                    records = await uow.sittings.list_final_results(quiz.id, learner_id) if quiz is not None else []
                    best_result = max(records, key=lambda record: record.total_score, default=None)
                    percentage = (best_result.total_score / max(1, len(best_result.available_question_codes)) * 100) if best_result is not None else None
                    passed = percentage is not None and (not section.requires_pass or percentage >= quiz.passing_score)
                    exhausted = bool(quiz and quiz.is_exam and quiz.max_attempts and len(records) >= quiz.max_attempts and not passed)
                    state = "ATTEMPTS_EXHAUSTED" if exhausted else "PASSED" if passed else "FAILED" if records else "AVAILABLE"
                result.append(SectionProgressDTO(
                    module_slug=str(module.slug), section_slug=str(section.slug), content_type=str(section.content_type),
                    is_accessible=accessible, is_complete=complete, requires_pass=section.requires_pass, state=state,
                ))
            if enrollment is not None and enrollment.status == EnrollmentStatus.COMPLETED:
                course_state = "COMPLETED"
            elif enrollment is not None and await self._completion_eligible(uow, learner_id, course):
                course_state = "PENDING_ADMIN_REVIEW" if course.completion_mode is CompletionMode.ADMIN_REVIEW else "ELIGIBLE_FOR_COMPLETION"
            else:
                course_state = "IN_PROGRESS"
            await uow.rollback()
            return CourseProgressDTO(
                enrollment_status=enrollment.status if enrollment else None,
                course_state=course_state,
                progression_mode=str(course.progression_mode), completion_mode=str(course.completion_mode),
                sections=tuple(result), last_opened=last_opened,
            )

    async def record_position(
        self, course_slug: str, learner_id: str, module_slug: str, section_slug: str
    ) -> CourseWatchPositionDTO:
        async with self.uow_factory() as uow:
            course = await uow.courses.get_by_slug(course_slug)
            if course is None or course.status is not ContentStatus.PUBLISHED:
                raise NotFoundError("course not found")
            module = await uow.modules.get_by_slug(course.id, module_slug)
            if module is None or module.status is not ContentStatus.PUBLISHED:
                raise NotFoundError("section not found")
            section = await uow.sections.get_by_slug(module.id, section_slug)
            if section is None or section.status is not ContentStatus.PUBLISHED:
                raise NotFoundError("section not found")
            history = await uow.enrollments.list_history(learner_id, course.id)
            enrollment = history[0] if history else None
            if enrollment is None or enrollment.status not in {EnrollmentStatus.ENROLLED, EnrollmentStatus.COMPLETED}:
                raise AuthorizationError("active course enrollment is required")
            await self._assert_section_access(uow, learner_id, course.id, section.id)
            enrollment.last_opened_section_id = section.id
            await uow.enrollments.update(enrollment)
            await uow.commit()
            return CourseWatchPositionDTO(
                module_slug=str(module.slug),
                section_slug=str(section.slug),
            )

    async def refresh_self_learning_completion(self, uow, learner_id: str, course_id: UUID) -> None:
        course = await uow.courses.get_by_id(course_id)
        if course is not None:
            await self._refresh_self_learning_completion(uow, learner_id, course)

    async def _completion_eligible(self, uow, learner_id: str, course) -> bool:
        enrollment = await uow.enrollments.get_live(learner_id, course.id)
        if enrollment is None:
            raise NotFoundError("enrollment not found")
        hierarchy = await uow.courses.get_hierarchy(course.id)
        if hierarchy is None:
            return False
        sections = [section for module in hierarchy.modules if module.status.value == "PUBLISHED" for section in hierarchy.sections_by_module.get(module.id, []) if section.status.value == "PUBLISHED"]
        for section in sections:
            if section.content_type is SectionContentType.QUIZ:
                quiz = await uow.quizzes.get_by_section(section.id)
                if quiz is not None and quiz.is_exam:
                    continue
            if not await self._section_complete(uow, learner_id, section):
                return False
        return True

    async def _refresh_self_learning_completion(self, uow, learner_id: str, course) -> None:
        if course.completion_mode is not CompletionMode.SELF_LEARNING:
            return
        enrollment = await uow.enrollments.get_live(learner_id, course.id)
        if enrollment is None:
            return
        if not await self._completion_eligible(uow, learner_id, course):
            return
        from app.domain.entities.base import utc_now
        enrollment.complete(utc_now())
        await uow.enrollments.update(enrollment)

    async def _assert_section_access(self, uow, learner_id: str, course_id: UUID, target_section_id: UUID) -> None:
        course = await uow.courses.get_by_id(course_id)
        if course is None:
            raise NotFoundError("course not found")
        if course.progression_mode is ProgressionMode.FREE:
            return
        enrollment = await uow.enrollments.get_live(learner_id, course.id)
        if enrollment is None:
            history = await uow.enrollments.list_history(learner_id, course.id)
            if history and history[0].status == EnrollmentStatus.COMPLETED:
                return
            raise AuthorizationError("active course enrollment is required")
        hierarchy = await uow.courses.get_hierarchy(course.id)
        ordered = [section for module in (hierarchy.modules if hierarchy else []) if module.status.value == "PUBLISHED" for section in hierarchy.sections_by_module.get(module.id, []) if section.status.value == "PUBLISHED"]
        target_index = next((i for i, section in enumerate(ordered) if section.id == target_section_id), None)
        if target_index is None:
            raise NotFoundError("section not found")
        completion = {section.id: await self._section_gate_complete(uow, learner_id, section) for section in ordered[:target_index]}
        require_sequential_access(course, ordered, ordered[target_index], lambda item: completion.get(item.id, False))

    async def _section_complete(self, uow, learner_id: str, section) -> bool:
        complete, _ = await self._section_states(uow, learner_id, section)
        return complete

    async def _section_gate_complete(self, uow, learner_id: str, section) -> bool:
        _, gate_complete = await self._section_states(uow, learner_id, section)
        return gate_complete

    async def _section_states(self, uow, learner_id: str, section) -> tuple[bool, bool]:
        if section.content_type is SectionContentType.MATERIAL:
            complete = await uow.learning_progress.section_is_complete(learner_id, section.id)
            return complete, complete
        if section.content_type is SectionContentType.QUIZ:
            quiz = await uow.quizzes.get_by_section(section.id)
            if quiz is None:
                return True, True
            results = await uow.sittings.list_final_results(quiz.id, learner_id)
            if not results:
                return False, quiz.is_exam
            if quiz.is_exam:
                return True, True
            passed = any(
                (result.total_score / max(1, len(result.available_question_codes))) * 100 >= quiz.passing_score
                for result in results
            )
            complete = not section.requires_pass or passed
            return complete, complete
        if section.content_type is SectionContentType.LAB_TASK:
            task = await uow.learning_progress.get_task(learner_id, section.id)
            if task is None:
                return False, False
            gate_complete = True
            reviewed = task.status in {CollectTaskStatus.REVIEWED, CollectTaskStatus.PASSED}
            complete = reviewed and (not section.requires_pass or task.status is CollectTaskStatus.PASSED)
            return complete, gate_complete
        return True, True
