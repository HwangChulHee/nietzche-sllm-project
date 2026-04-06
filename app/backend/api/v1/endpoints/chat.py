import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import get_current_user
from db.session import get_db
from models.chat import ChatMessage, ChatRoom
from models.user import User
from schemas.chat import ChatMessageResponse, ChatRequest, ChatRoomResponse
from services import llm_service, vector_service

router = APIRouter()
logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────
# GET /chat/test — SSE 연결 확인용 더미 엔드포인트
# ───────────────────────────────────────────────────────

@router.get("/test")
async def test_chat():
    async def event_generator():
        messages = ["나의 ", "시대는 ", "아직 ", "오지 ", "않았다.", "\n- 프리드리히 니체"]
        for text in messages:
            yield f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n"
            await asyncio.sleep(0.3)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ───────────────────────────────────────────────────────
# POST /chat/ — 실제 채팅 엔드포인트 (SSE 스트리밍)
# ───────────────────────────────────────────────────────

@router.post("/")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    채팅 요청을 받아 니체 페르소나 응답을 SSE로 스트리밍.

    흐름:
      1. 채팅방 조회 또는 생성 (JWT에서 user 확인)
      2. 사용자 메시지 저장
      3. 대화 히스토리 조회 (슬라이딩 윈도우 6개)
      4. Qdrant RAG 컨텍스트 검색
      5. LLM 스트리밍 → SSE 전송
      6. 완료 후 어시스턴트 메시지 저장

    SSE 이벤트 타입:
      - init  : {"type": "init",  "room_id": "<uuid>", "text": ""}
      - token : {"type": "token", "text": "<토큰>"}
      - done  : {"type": "done",  "text": ""}
    """
    # ── 1. 채팅방 조회 또는 생성 ─────────────────────────
    if request.room_id:
        result = await db.execute(
            select(ChatRoom).where(
                ChatRoom.id == request.room_id,
                ChatRoom.user_id == current_user.id,
            )
        )
        room = result.scalar_one_or_none()
        if not room:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="채팅방을 찾을 수 없습니다.",
            )
    else:
        title = request.message[:30] + ("..." if len(request.message) > 30 else "")
        room = ChatRoom(user_id=current_user.id, title=title)
        db.add(room)
        await db.flush()

    # ── 2. 사용자 메시지 저장 ────────────────────────────
    user_msg = ChatMessage(
        room_id=room.id,
        role="user",
        content=request.message,
    )
    db.add(user_msg)
    await db.commit()
    await db.refresh(room)

    # ── 3. 대화 히스토리 조회 (슬라이딩 윈도우: 최근 6개) ──
    history_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.room_id == room.id)
        .order_by(ChatMessage.id.desc())
        .limit(6)
    )
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in reversed(history_result.scalars().all())
        if msg.content != request.message
    ]

    # ── 4. RAG 컨텍스트 검색 ────────────────────────────
    context = await vector_service.search_context(request.message)

    room_id = str(room.id)

    # ── 5 & 6. 스트리밍 제너레이터 ──────────────────────
    async def generate():
        yield _sse({"type": "init", "room_id": room_id, "text": ""})

        full_response: list[str] = []
        try:
            async for token in llm_service.stream_response(request.message, context, history):
                full_response.append(token)
                yield _sse({"type": "token", "text": token})
        except Exception as e:
            logger.error("스트리밍 중 오류: %s", e)
            yield _sse({"type": "error", "text": "응답 생성 중 오류가 발생했습니다."})
            return

        yield _sse({"type": "done", "text": ""})

        assistant_msg = ChatMessage(
            room_id=room.id,
            role="assistant",
            content="".join(full_response),
            references=[{"text": c} for c in context] if context else None,
        )
        db.add(assistant_msg)
        await db.commit()

    return StreamingResponse(generate(), media_type="text/event-stream")


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# ───────────────────────────────────────────────────────
# GET /chat/rooms — 사용자의 채팅방 목록
# ───────────────────────────────────────────────────────

@router.get("/rooms", response_model=list[ChatRoomResponse])
async def list_rooms(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatRoom)
        .where(ChatRoom.user_id == current_user.id)
        .order_by(ChatRoom.updated_at.desc())
    )
    return result.scalars().all()


# ───────────────────────────────────────────────────────
# GET /chat/rooms/{room_id}/messages — 채팅방 메시지 목록
# ───────────────────────────────────────────────────────

@router.get("/rooms/{room_id}/messages", response_model=list[ChatMessageResponse])
async def list_messages(
    room_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatRoom).where(
            ChatRoom.id == room_id,
            ChatRoom.user_id == current_user.id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="채팅방을 찾을 수 없습니다.")

    msg_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.room_id == room_id)
        .order_by(ChatMessage.id)
    )
    return msg_result.scalars().all()


# ───────────────────────────────────────────────────────
# DELETE /chat/rooms/{room_id} — 채팅방 삭제
# ───────────────────────────────────────────────────────

@router.delete("/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatRoom).where(
            ChatRoom.id == room_id,
            ChatRoom.user_id == current_user.id,
        )
    )
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="채팅방을 찾을 수 없습니다.")

    await db.delete(room)
    await db.commit()
