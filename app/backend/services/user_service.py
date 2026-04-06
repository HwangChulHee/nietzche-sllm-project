"""
user_service.py — 사용자 생성 비즈니스 로직.
"""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import hash_password
from models.user import User, UserRole
from schemas.user import UserCreate


async def create_user(db: AsyncSession, user_in: UserCreate) -> User:
    """이름 중복 확인 후 사용자 생성. 중복 시 400 반환."""
    result = await db.execute(select(User).where(User.name == user_in.name))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 존재하는 이름입니다. 다른 이름을 입력해주세요.",
        )

    user = User(
        name=user_in.name,
        hashed_password=hash_password(user_in.password),
        role=UserRole.USER,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user
