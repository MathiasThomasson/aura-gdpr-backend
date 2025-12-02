import hashlib
import json
from typing import Optional
from hashlib import sha256

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import log_event
from app.core.config import settings


async def log_ai_call(db: AsyncSession, tenant_id: Optional[int], user_id: Optional[int], input_text: Optional[str], model: str, endpoint: str, high_risk: bool, status: str, error: Optional[str] = None):
    """Central helper to create audit logs for AI calls.

    - Will NOT store raw input by default.
    - Controlled by env: AI_AUDIT_STORE_INPUT and AI_AUDIT_INPUT_MAX_LENGTH.
    - If input stored it will be truncated and marked in metadata.

    Warning: Storing `input_text` may contain PII. Keep `AI_AUDIT_STORE_INPUT` disabled in production unless you have a clear policy.
    """

    meta = {
        "model": model,
        "endpoint": endpoint,
        "input_length": len(input_text) if input_text is not None else 0,
        "high_risk": bool(high_risk),
        "status": status,
    }

    if error:
        meta["error"] = str(error)

    level = (settings.AI_LOGGING_LEVEL or "hash").lower()
    if settings.AI_DISABLE_PROMPT_STORAGE and not settings.AI_AUDIT_STORE_INPUT:
        level = "hash"
    if settings.AI_AUDIT_STORE_INPUT and level == "hash":
        level = "truncated"
    if level == "full" and settings.AI_AUDIT_STORE_INPUT:
        max_len = int(settings.AI_AUDIT_INPUT_MAX_LENGTH or 512)
        truncated = None
        if input_text and len(input_text) > max_len:
            truncated = input_text[:max_len]
        meta["input_text"] = truncated if truncated is not None else input_text
        meta["input_truncated"] = bool(input_text and truncated is not None)
    elif level == "truncated":
        max_len = int(settings.AI_AUDIT_INPUT_MAX_LENGTH or 512)
        if input_text:
            meta["input_text"] = input_text[:max_len]
            meta["input_truncated"] = len(input_text) > max_len
    elif level == "hash":
        if input_text:
            digest = sha256(input_text.encode("utf-8")).hexdigest()
            meta["input_hash_sha256"] = digest
    else:
        # level none: no content stored
        pass

    # Use existing log_event function
    await log_event(db, tenant_id or None, user_id or None, "ai_call", None, "analyze_gdpr_text", meta)
