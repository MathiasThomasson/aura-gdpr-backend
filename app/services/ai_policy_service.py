from typing import Tuple

from app.schemas.ai_policies import PolicyGenerateRequest, PolicyGenerateResponse
from app.services.ai_client import ai_chat_completion


def _parse_policy_text(text: str) -> Tuple[str, str, str]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    title = lines[0] if lines else "Generated Policy"
    content = text.strip()
    # summary: take first few sentences
    summary_sentences = []
    for sentence in content.replace("\n", " ").split("."):
        s = sentence.strip()
        if s:
            summary_sentences.append(s)
        if len(summary_sentences) >= 3:
            break
    summary = ". ".join(summary_sentences).strip()
    if summary and not summary.endswith("."):
        summary += "."
    return title, summary or "Generated summary not available.", content or "No content generated."


async def generate_policy(tenant_id: int, payload: PolicyGenerateRequest) -> PolicyGenerateResponse:
    system_prompt = (
        "You are an AI assistant generating GDPR-aligned policies. "
        "Provide concise, clear, and actionable text. Use English. "
        "Return a structured draft policy ready for review."
    )
    user_prompt = (
        f"Policy type: {payload.policy_type}\n"
        f"Context: {payload.context_description or 'No additional context provided.'}\n"
        "Language: English\n"
        "Please draft a complete policy with headings and sections."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    raw = await ai_chat_completion(messages, tenant_id=tenant_id)
    title, summary, content = _parse_policy_text(raw)
    return PolicyGenerateResponse(title=title, summary=summary, content=content)
