from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Optional
from models.user import UserRole


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=6, max_length=100)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    role: UserRole
    created_at: datetime
    token: Optional[str] = None  # 회원가입/로그인 시 발급


class UserLoginRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1)