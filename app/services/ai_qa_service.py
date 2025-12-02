from typing import List

from app.services.ai_client import ai_chat_completion
from app.services import rag_service
from app.schemas.ai_qa import AiAnswerSource


async def rag_search(tenant_id: int, question: str, limit: int, db) -> List[AiAnswerSource]:
    results = await rag_service.search(db, tenant_id, question, top_k=limit)
    sources: List[AiAnswerSource] = []
    for item in results:
        if len(item) == 3:
            score, chunk, emb = item
        elif len(item) == 2:
            score, chunk = item
        else:
            continue
        title = getattr(chunk, "section_title", None) or "Document"
        snippet = (chunk.content or "")[:400]
        sources.append(AiAnswerSource(id=chunk.id, title=title, snippet=snippet))
    return sources


async def answer_question(tenant_id: int, question: str, sources: List[AiAnswerSource]) -> str:
    context_lines = []
    for idx, src in enumerate(sources, start=1):
        context_lines.append(f"[{idx}] {src.title}: {src.snippet}")
    context_blob = "\n".join(context_lines) if context_lines else "No context available."

    system_msg = (
        "You are an AI assistant for GDPR compliance. "
        "Answer ONLY using the provided context snippets. If the answer is not present, say you do not know."
    )
    user_msg = f"Question: {question}\nContext:\n{context_blob}"
    messages = [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}]
    return await ai_chat_completion(messages, tenant_id=tenant_id)
