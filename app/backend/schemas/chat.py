from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class ChatRequest(BaseModel):
    """채팅 요청 — 사용자 메시지 + 컨텍스트 정보."""
    message: str = Field(min_length=1, max_length=2000, description="사용자 질문")
    room_id: Optional[UUID] = Field(None, description="기존 채팅방 ID. None이면 새 방 생성")


class ChatStreamChunk(BaseModel):
    """SSE 스트리밍 청크 — 토큰 단위로 전송."""
    type: str           # "init" | "token" | "done"
    text: str = ""
    room_id: Optional[str] = None   # init 청크에만 포함


class ChatRoomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    references: Optional[list] = None
    created_at: datetime
