from typing import List, Optional
from pydantic import BaseModel


class RAGSearchRequest(BaseModel):
    query: str
    top_k: int = 5


class RAGSearchResult(BaseModel):
    chunk_id: int
    document_id: int
    content: str
    score: float
    chunk_index: int
    model: str
    section_title: str | None = None


class RAGAnswer(BaseModel):
    answer: str
    citations: List[RAGSearchResult]
