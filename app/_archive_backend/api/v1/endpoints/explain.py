"""
explain.py — 해설 sLLM 엔드포인트.

  POST /api/v1/explain — 해설 모드 [더 깊이 묻기] 동적 풀이 (SSE 스트리밍)
"""

import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from schemas.vn import ExplainRequest
from services.sllm_clients import get_explain_client

router = APIRouter()
logger = logging.getLogger(__name__)


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/explain")
async def explain(req: ExplainRequest):
    explain_client = get_explain_client()
    history_dicts = [m.model_dump() for m in req.history]

    async def gen():
        yield _sse({"type": "metadata", "screen_id": req.screen_id})
        try:
            async for delta in explain_client.stream_explain(
                req.screen_id, req.query, history_dicts
            ):
                yield _sse({"type": "delta", "content": delta})
        except Exception as e:
            logger.exception("explain_client.stream_explain 실패")
            yield _sse({"type": "error", "message": str(e)})
            return
        yield _sse({"type": "done"})

    return StreamingResponse(gen(), media_type="text/event-stream")
