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


class QuizOptionInput(BaseModel):
    value: str = Field(min_length=1, max_length=5000)
    is_correct: bool


class QuizQuestionAuthoringInput(BaseModel):
    prompt: str = Field(max_length=5000)
    options: list[QuizOptionInput] = Field(default_factory=list, max_length=100)


class QuizOptionRead(BaseModel):
    id: str
    slug: str
    value: str
    position: int
    is_correct: bool


class QuizQuestionOrderItem(BaseModel):
    slug: str = Field(min_length=1, max_length=160)
    position: int = Field(ge=0)


class QuizQuestionOrderRequest(BaseModel):
    items: list[QuizQuestionOrderItem] = Field(min_length=1)


class QuizQuestionAuthoringRead(BaseModel):
    id: str
    slug: str
    prompt: str
    question_code: str
    position: int
    options: list[QuizOptionRead]
