from pydantic import BaseModel, Field

from app.domain.value_objects.quiz_assessment import AnswerPolicy


class QuizConfigurationRequest(BaseModel):
    is_exam: bool = False
    max_attempts: int | None = Field(default=None, ge=1)
    answer_policy: AnswerPolicy = AnswerPolicy.SINGLE
