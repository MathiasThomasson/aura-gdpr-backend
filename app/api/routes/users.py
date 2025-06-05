from fastapi import APIRouter, Depends
from app.core.auth import get_current_user

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    return current_user
