from pydantic import BaseModel


class AiAnswerRequest(BaseModel):
    question: str


class AiAnswerSource(BaseModel):
    id: str | int
    title: str
    snippet: str


class AiAnswerResponse(BaseModel):
    answer: str
    sources: list[AiAnswerSource]
