"""
respond.py — 페르소나 sLLM 엔드포인트 (차라투스트라).

  POST /api/v1/respond           — 학습자 발화 / 침묵 응답
  POST /api/v1/respond/auto      — 화면 진입 시 자동 발화
  POST /api/v1/respond/farewell  — [작별을 고한다] 클릭 시 마지막 발화

모두 SSE 스트리밍.
"""

import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from schemas.vn import (
    RespondAutoRequest,
    RespondFarewellRequest,
    RespondRequest,
)
from services.sllm_clients import get_persona_client

router = APIRouter()
logger = logging.getLogger(__name__)


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/respond")
async def respond(req: RespondRequest):
    persona = get_persona_client()
    history_dicts = [m.model_dump() for m in req.history]

    async def gen():
        yield _sse({"type": "metadata", "screen_id": req.screen_id, "silent": req.silent})
        try:
            async for delta in persona.stream_respond(
                req.screen_id, history_dicts, req.message, silent=req.silent
            ):
                yield _sse({"type": "delta", "content": delta})
        except Exception as e:
            logger.exception("persona.stream_respond 실패")
            yield _sse({"type": "error", "message": str(e)})
            return
        yield _sse({"type": "done"})

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/respond/auto")
async def respond_auto(req: RespondAutoRequest):
    persona = get_persona_client()
    history_dicts = [m.model_dump() for m in req.history]

    async def gen():
        yield _sse({"type": "metadata", "screen_id": req.screen_id, "kind": "auto_first"})
        try:
            async for delta in persona.stream_auto_first(req.screen_id, history_dicts):
                yield _sse({"type": "delta", "content": delta})
        except Exception as e:
            logger.exception("persona.stream_auto_first 실패")
            yield _sse({"type": "error", "message": str(e)})
            return
        yield _sse({"type": "done"})

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.post("/respond/farewell")
async def respond_farewell(req: RespondFarewellRequest):
    persona = get_persona_client()
    history_dicts = [m.model_dump() for m in req.history]

    async def gen():
        yield _sse({"type": "metadata", "screen_id": req.screen_id, "kind": "farewell"})
        try:
            async for delta in persona.stream_farewell(req.screen_id, history_dicts):
                yield _sse({"type": "delta", "content": delta})
        except Exception as e:
            logger.exception("persona.stream_farewell 실패")
            yield _sse({"type": "error", "message": str(e)})
            return
        yield _sse({"type": "done"})

    return StreamingResponse(gen(), media_type="text/event-stream")
