from fastapi import APIRouter, Depends

from app.core.deps import CurrentContext, current_context
from app.schemas.document import DocumentListResponse

router = APIRouter(prefix="/api/documents", tags=["Documents"])


@router.get("/", response_model=DocumentListResponse)
async def list_documents(ctx: CurrentContext = Depends(current_context)):
    # Provide an empty document list so the frontend can render without DB state
    return DocumentListResponse(items=[], total=0)
