from pydantic import BaseModel, Field


class QuizQuestionCreate(BaseModel):
    prompt: str = Field(min_length=1, max_length=5000)
    question_code: str | None = Field(default=None, max_length=80)


class QuizQuestionUpdate(BaseModel):
    question_code: str = Field(min_length=1, max_length=80)


class QuizQuestionRead(BaseModel):
    id: str
    slug: str
    prompt: str
    question_code: str
