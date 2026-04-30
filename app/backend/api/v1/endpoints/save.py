"""
save.py — 세이브 슬롯 엔드포인트 (단일 슬롯, id=1 고정).

  GET    /api/v1/save  — 슬롯 조회. 비어있으면 null.
  POST   /api/v1/save  — 세이브 (덮어쓰기). 내부에서 요약 sLLM 호출하여 summary 생성.
  DELETE /api/v1/save  — 슬롯 삭제. 미래 확장용.
"""

import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_db
from models.save import SaveSlot
from schemas.vn import (
    ChatMessage,
    SavePostRequest,
    SavePostResponse,
    SaveSlotResponse,
)
from services.sllm_clients import get_summary_client

router = APIRouter()
logger = logging.getLogger(__name__)

SLOT_ID = 1


async def _consume_summary(history: list[dict], episode: str, scene_index: int) -> str:
    summary_client = get_summary_client()
    chunks: list[str] = []
    async for delta in summary_client.stream_summarize(history, episode, scene_index):
        chunks.append(delta)
    return "".join(chunks)


def _slot_to_response(slot: SaveSlot) -> SaveSlotResponse:
    raw = json.loads(slot.recent_messages) if slot.recent_messages else []
    return SaveSlotResponse(
        episode=slot.episode,
        scene_index=slot.scene_index,
        summary=slot.summary,
        recent_messages=[ChatMessage(**m) for m in raw],
        timestamp=slot.timestamp,
    )


@router.get("/save")
async def get_save(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SaveSlot).where(SaveSlot.id == SLOT_ID))
    slot = result.scalar_one_or_none()
    if slot is None:
        return JSONResponse(content=None)
    return _slot_to_response(slot).model_dump(mode="json")


@router.post("/save", response_model=SavePostResponse)
async def post_save(req: SavePostRequest, db: AsyncSession = Depends(get_db)):
    history_dicts = [m.model_dump() for m in req.recent_messages]
    summary_text = await _consume_summary(history_dicts, req.episode, req.scene_index)

    result = await db.execute(select(SaveSlot).where(SaveSlot.id == SLOT_ID))
    slot = result.scalar_one_or_none()

    if slot is None:
        slot = SaveSlot(
            id=SLOT_ID,
            episode=req.episode,
            scene_index=req.scene_index,
            summary=summary_text,
            recent_messages=json.dumps(history_dicts, ensure_ascii=False),
        )
        db.add(slot)
    else:
        slot.episode = req.episode
        slot.scene_index = req.scene_index
        slot.summary = summary_text
        slot.recent_messages = json.dumps(history_dicts, ensure_ascii=False)

    await db.commit()
    return SavePostResponse(ok=True, summary_preview=summary_text[:80])


@router.delete("/save")
async def delete_save(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SaveSlot).where(SaveSlot.id == SLOT_ID))
    slot = result.scalar_one_or_none()
    if slot is None:
        return {"deleted": False}
    await db.delete(slot)
    await db.commit()
    return {"deleted": True}
