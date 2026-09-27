"""In-memory ports used by quiz-sitting use-case tests only."""

from collections import defaultdict

from app.domain.entities.quiz_sitting_snapshot import QuizSittingQuestionSnapshot, QuizSittingResult
from app.domain.exceptions import ConflictError
from app.domain.value_objects.content import QuizAttemptState


class FakeQuizRepository:
    def __init__(self, quiz, questions, answers_by_question):
        self.quiz = quiz
        self.questions = list(questions)
        self.answers_by_question = answers_by_question

    async def get_by_id(self, quiz_id): return self.quiz if quiz_id == self.quiz.id else None
    async def list_questions(self, quiz_id): return list(self.questions) if quiz_id == self.quiz.id else []
    async def list_answers(self, question): return list(self.answers_by_question[question.id])


class FakeSittingRepository:
    def __init__(self):
        self.sittings = {}
        self.snapshots = defaultdict(list)
        self.selections = defaultdict(set)
        self.results = {}
        self.exam_counts = defaultdict(int)

    async def get_by_id(self, sitting_id): return self.sittings.get(sitting_id)
    async def get_active(self, quiz_id, learner_id):
        return next((sitting for sitting in self.sittings.values() if sitting.quiz_id == quiz_id and sitting.learner_id == learner_id and sitting.attempt_state is QuizAttemptState.IN_PROGRESS), None)
    async def create(self, sitting): self.sittings[sitting.id] = sitting; return sitting
    async def save_snapshot(self, snapshots): self.snapshots[snapshots[0].sitting_id] = list(snapshots)
    async def get_snapshot(self, sitting_id): return list(self.snapshots[sitting_id])
    async def replace_selection(self, sitting_question_id, option_ids): self.selections[sitting_question_id] = set(option_ids)
    async def selected_option_ids(self, sitting_id): return {item.id: set(self.selections[item.id]) for item in self.snapshots[sitting_id]}
    async def save_final_result(self, sitting, result): self.results.setdefault(sitting.id, result)
    async def get_final_result(self, sitting_id): return self.results.get(sitting_id)
    async def list_final_results(self, quiz_id, learner_id): return [result for result in self.results.values() if result.quiz_id == quiz_id]
    async def reserve_exam_finalization(self, quiz_id, learner_id, max_attempts):
        key = (quiz_id, learner_id)
        if self.exam_counts[key] >= max_attempts: raise ConflictError("EXAM_ATTEMPT_LIMIT_REACHED")
        self.exam_counts[key] += 1


class FakeQuizSittingUnitOfWork:
    def __init__(self, quizzes, sittings):
        self.quizzes = quizzes
        self.sittings = sittings
        self.commits = 0

    async def __aenter__(self): return self
    async def __aexit__(self, *_args): return None
    async def commit(self): self.commits += 1
    async def rollback(self): return None
