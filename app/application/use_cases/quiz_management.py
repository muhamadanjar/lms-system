from app.domain.entities.answer import Answer
from app.domain.entities.question import Question
from app.domain.entities.quiz import Quiz
from app.domain.entities.quiz_sitting import QuizSitting
from app.domain.services.content_policy import validate_publication


class QuizManagementUseCases:
    def __init__(self, uow_factory):
        self.uow_factory = uow_factory

    async def create_quiz(self, quiz: Quiz) -> Quiz:
        async with self.uow_factory() as uow:
            result = await uow.quizzes.create_quiz(quiz)
            await uow.commit()
            return result

    async def add_question(self, question: Question) -> Question:
        async with self.uow_factory() as uow:
            result = await uow.quizzes.create_question(question)
            await uow.commit()
            return result

    async def add_answer(self, answer: Answer) -> Answer:
        async with self.uow_factory() as uow:
            result = await uow.quizzes.create_answer(answer)
            await uow.commit()
            return result

    async def create_sitting(self, sitting: QuizSitting) -> QuizSitting:
        async with self.uow_factory() as uow:
            result = await uow.sittings.create(sitting)
            await uow.commit()
            return result

    async def transition_sitting(self, sitting: QuizSitting, target) -> QuizSitting:
        sitting.transition(target)
        async with self.uow_factory() as uow:
            result = await uow.sittings.update(sitting)
            await uow.commit()
            return result

    @staticmethod
    def validate_question_publication(question: Question, answers: list[Answer]) -> None:
        validate_publication(question, answers)
