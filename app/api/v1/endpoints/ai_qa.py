from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentContext, current_context
from app.db.database import get_db
from app.schemas.ai_qa import AiAnswerRequest, AiAnswerResponse
from app.services.ai_qa_service import answer_question, rag_search

router = APIRouter(prefix="/api/ai", tags=["AI Q&A"])


@router.post("/answer", response_model=AiAnswerResponse)
async def answer(
    payload: AiAnswerRequest,
    db: AsyncSession = Depends(get_db),
    ctx: CurrentContext = Depends(current_context),
):
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Question is required")

    sources = await rag_search(ctx.tenant_id, payload.question, limit=5, db=db)
    answer_text = await answer_question(ctx.tenant_id, payload.question, sources)
    return AiAnswerResponse(answer=answer_text, sources=sources)
