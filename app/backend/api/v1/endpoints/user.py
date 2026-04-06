from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import create_access_token
from db.session import get_db
from schemas.user import UserCreate, UserResponse
from services import user_service

router = APIRouter()


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    user = await user_service.create_user(db, user_in)
    response = UserResponse.model_validate(user)
    response.token = create_access_token(user.id)
    return response
