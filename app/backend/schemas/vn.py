"""
schemas/vn.py — 비주얼 노벨 백엔드 입출력 스키마.

엔드포인트 매트릭스:
  POST /api/v1/respond           — 페르소나 sLLM (학습자 발화 / 침묵 응답)
  POST /api/v1/respond/auto      — 화면 진입 자동 발화
  POST /api/v1/respond/farewell  — 작별 시 마지막 발화
  POST /api/v1/explain           — 해설 모드 동적 풀이
  POST /api/v1/summarize         — 차라투스트라 1인칭 회상 (세이브 / transition)
  GET  /api/v1/save              — 단일 슬롯 조회
  POST /api/v1/save              — 세이브 (자동 요약 포함)
  DELETE /api/v1/save            — 세이브 삭제

스트리밍 엔드포인트는 SSE (`text/event-stream`)로 반환.
세이브 GET/POST/DELETE는 JSON.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ───────────────────────────────────────────────────────
# 공통 메시지 형식
# ───────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


# ───────────────────────────────────────────────────────
# Persona — /respond 계열
# ───────────────────────────────────────────────────────

class RespondRequest(BaseModel):
    screen_id: str
    message: str = Field(default="", max_length=500)
    silent: bool = False
    history: list[ChatMessage] = Field(default_factory=list)


class RespondAutoRequest(BaseModel):
    screen_id: str
    history: list[ChatMessage] = Field(default_factory=list)


class RespondFarewellRequest(BaseModel):
    screen_id: str
    history: list[ChatMessage] = Field(default_factory=list)


# ───────────────────────────────────────────────────────
# Explain — /explain
# ───────────────────────────────────────────────────────

class ExplainRequest(BaseModel):
    screen_id: str
    query: str = Field(min_length=1, max_length=500)
    history: list[ChatMessage] = Field(default_factory=list)


# ───────────────────────────────────────────────────────
# Summarize — /summarize
# ───────────────────────────────────────────────────────

class SummarizeRequest(BaseModel):
    episode: Literal["ep1", "ep2"]
    scene_index: int
    history: list[ChatMessage] = Field(default_factory=list)


# ───────────────────────────────────────────────────────
# Save — /save GET/POST/DELETE
# ───────────────────────────────────────────────────────

class SavePostRequest(BaseModel):
    episode: Literal["ep1", "ep2"]
    scene_index: int
    recent_messages: list[ChatMessage] = Field(default_factory=list)


class SaveSlotResponse(BaseModel):
    episode: str
    scene_index: int
    summary: str
    recent_messages: list[ChatMessage]
    timestamp: datetime


class SavePostResponse(BaseModel):
    ok: bool
    summary_preview: str
