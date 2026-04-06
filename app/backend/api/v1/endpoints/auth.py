from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import create_access_token, verify_password
from db.session import get_db
from models.user import User
from schemas.user import UserLoginRequest, UserResponse

router = APIRouter()


@router.post("/login", response_model=UserResponse)
async def login(body: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.name == body.name))
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이름 또는 비밀번호가 올바르지 않습니다.",
        )

    response = UserResponse.model_validate(user)
    response.token = create_access_token(user.id)
    return response
