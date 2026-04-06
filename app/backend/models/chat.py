from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, DateTime, ForeignKey, func, JSON
from .base import Base
import uuid

class ChatRoom(Base):
    __tablename__ = "chat_room"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), server_default="새로운 상담")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="chat_rooms")
    messages: Mapped[list["ChatMessage"]] = relationship(back_populates="chat_room", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_message"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    room_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_room.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(20))  # 'user' 또는 'assistant'
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # RAG 검색 시 사용된 니체 저서의 구절 정보를 저장 (JSON 형태) 
    references: Mapped[dict | list] = mapped_column(JSON, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    chat_room: Mapped["ChatRoom"] = relationship(back_populates="messages")