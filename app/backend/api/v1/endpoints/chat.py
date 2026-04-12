import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models.chat import Conversation, Message
from schemas.chat import ChatMessageResponse, ChatRequest, ConversationMessagesResponse
from services.llm_client import get_llm_client, load_system_prompt

router = APIRouter()
logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────
# POST /chat — 채팅 (SSE 스트리밍)
# ───────────────────────────────────────────────────────

@router.post("/chat")
async def chat(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    # 1. conversation 조회 또는 생성
    if request.conversation_id:
        result = await db.execute(
            select(Conversation).where(Conversation.id == request.conversation_id)
        )
        conversation = result.scalar_one_or_none()
        if not conversation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="대화를 찾을 수 없습니다.",
            )
    else:
        title = request.message[:30] + ("..." if len(request.message) > 30 else "")
        conversation = Conversation(title=title)
        db.add(conversation)
        await db.flush()

    # 2. user 메시지 저장
    user_msg = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.message,
    )
    db.add(user_msg)
    await db.commit()

    # 3. 컨텍스트 조립
    system_prompt = load_system_prompt()
    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.created_at)
    )
    history = history_result.scalars().all()

    messages = [
        {"role": "system", "content": system_prompt},
        *[{"role": m.role, "content": m.content} for m in history],
    ]

    conv_id = str(conversation.id)
    llm_client = get_llm_client()

    # 4. SSE 스트리밍
    async def event_generator():
        yield _sse({"type": "metadata", "conversation_id": conv_id})

        full_response = ""
        try:
            async for delta in llm_client.stream_chat(messages):
                full_response += delta
                yield _sse({"type": "delta", "content": delta})
        except Exception as e:
            logger.error("스트리밍 중 오류: %s", e)
            yield _sse({"type": "error", "message": "LLM 응답 생성 실패"})
            return

        # assistant 메시지 저장
        assistant_msg = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=full_response,
        )
        db.add(assistant_msg)
        await db.commit()

        yield _sse({"type": "done"})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ───────────────────────────────────────────────────────
# GET /conversations/{id}/messages — 대화 복원
# ───────────────────────────────────────────────────────

@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationMessagesResponse,
)
async def get_messages(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="대화를 찾을 수 없습니다.",
        )

    msg_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()

    return ConversationMessagesResponse(
        conversation_id=conversation_id,
        messages=[ChatMessageResponse.model_validate(m) for m in messages],
    )


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


# ───────────────────────────────────────────────────────
# DELETE /conversations/{id} — 대화 삭제
# ───────────────────────────────────────────────────────

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="대화를 찾을 수 없습니다.",
        )
    await db.delete(conv)
    await db.commit()
    return {"deleted": True, "conversation_id": str(conversation_id)}

