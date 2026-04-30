"""
summarize.py — 요약 sLLM 엔드포인트.

  POST /api/v1/summarize — 차라투스트라 1인칭 회상 (세이브 / Ep 1→2 transition 백그라운드)
"""

import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from schemas.vn import SummarizeRequest
from services.sllm_clients import get_summary_client

router = APIRouter()
logger = logging.getLogger(__name__)


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/summarize")
async def summarize(req: SummarizeRequest):
    summary_client = get_summary_client()
    history_dicts = [m.model_dump() for m in req.history]

    async def gen():
        yield _sse({
            "type": "metadata",
            "episode": req.episode,
            "scene_index": req.scene_index,
        })
        try:
            async for delta in summary_client.stream_summarize(
                history_dicts, req.episode, req.scene_index
            ):
                yield _sse({"type": "delta", "content": delta})
        except Exception as e:
            logger.exception("summary_client.stream_summarize 실패")
            yield _sse({"type": "error", "message": str(e)})
            return
        yield _sse({"type": "done"})

    return StreamingResponse(gen(), media_type="text/event-stream")
