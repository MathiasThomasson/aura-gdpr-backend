from fastapi import APIRouter

router = APIRouter(prefix="/api/documents", tags=["Documents"])

@router.get("/")
def get_docs():
    return {"msg": "Documents placeholder"}
