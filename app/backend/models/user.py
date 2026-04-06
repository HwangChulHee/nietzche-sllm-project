import uuid
import enum
from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, DateTime, Enum, func
from .base import Base


class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "user"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # 사용자 이름 추가 (중복 불가)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)

    hashed_password: Mapped[str | None] = mapped_column(String, nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    chat_rooms: Mapped[list["ChatRoom"]] = relationship(back_populates="user", cascade="all, delete-orphan")
