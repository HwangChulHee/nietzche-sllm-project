"""
llm_service.py — vLLM(RunPod) 호출 및 니체 페르소나 스트리밍.

동작 방식:
  - RUNPOD_API_KEY 가 설정된 경우 → 실제 vLLM 엔드포인트 호출
  - 설정되지 않은 경우          → 개발용 Mock 스트리밍 응답
"""

import asyncio
import json
import logging
from typing import AsyncGenerator

import httpx

from core.config import settings

logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────
# 니체 페르소나 시스템 프롬프트
# ───────────────────────────────────────────────────────

NIETZSCHE_SYSTEM_PROMPT = """당신은 프리드리히 니체(Friedrich Nietzsche, 1844-1900)입니다.
철학자로서 다음의 원칙에 따라 응답하십시오.

[말투와 문체]
- 격언체(aphorism)를 즐겨 사용하며, 짧고 강렬한 문장으로 핵심을 꿰뚫는다.
- 직접적이고 도발적이며, 편안한 위로보다 강인한 성장을 촉구한다.
- 때때로 독일어 원문(Übermensch, Wille zur Macht, Amor Fati 등)을 인용한다.
- 한국어로 응답하되, 품위 있는 문어체를 사용한다.

[핵심 철학]
- 힘에의 의지(Wille zur Macht): 모든 생명은 자신을 극복하려는 의지를 가진다.
- 초인(Übermensch): 스스로의 가치를 창조하고 기존 도덕을 넘어서는 존재.
- 영겁회귀(Ewige Wiederkunft): 지금 이 순간을 영원히 반복해도 좋을 만큼 살아가라.
- Amor Fati(운명애): 자신의 운명을 사랑하라.

[응답 지침]
- 상대방의 고통이나 혼란을 인정하되, 그것을 성장의 재료로 전환시킨다.
- 추상적인 위로 대신 구체적인 철학적 통찰을 제공한다.
- 150~300자 내외로 간결하게 답한다.
- 참고 어록이 있다면 자연스럽게 인용한다."""


# ───────────────────────────────────────────────────────
# Mock 응답 (개발/테스트용)
# ───────────────────────────────────────────────────────

_MOCK_TOKENS = [
    "그대의 질문은 ",
    "나를 심연으로 ",
    "데려간다. ",
    "인간은 ",
    "극복되어야 할 ",
    "무언가이다. ",
    "그대가 고통 속에 있다면, ",
    "그것은 그대가 ",
    "아직 살아있다는 ",
    "증거다. ",
    "Amor Fati — ",
    "그대의 운명을 ",
    "사랑하라.",
]

_MOCK_DELAY = 0.03  # 테스트 속도를 위해 의도적으로 짧게 설정


# ───────────────────────────────────────────────────────
# Public API
# ───────────────────────────────────────────────────────

async def stream_response(
    message: str,
    context: list[str],
    history: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    """
    니체 응답을 토큰 단위로 스트리밍.

    Args:
        message: 사용자 입력 메시지
        context: Qdrant에서 검색된 니체 어록 리스트 (RAG)
        history: 이전 대화 [{role, content}, ...] 최대 6개

    Yields:
        str: 응답 토큰 조각
    """
    if settings.is_llm_available:
        async for token in _call_vllm(message, context, history):
            yield token
    else:
        logger.info("LLM Mock 모드 — RUNPOD_API_KEY 미설정")
        async for token in _mock_stream():
            yield token


# ───────────────────────────────────────────────────────
# vLLM RunPod 실제 호출
# ───────────────────────────────────────────────────────

def _build_prompt(
    message: str,
    context: list[str],
    history: list[dict] | None = None,
) -> str:
    """RAG 컨텍스트 + 대화 히스토리를 포함한 최종 프롬프트 구성."""
    context_block = ""
    if context:
        quotes = "\n".join(f"- {q}" for q in context if q)
        context_block = f"\n\n[참고 어록]\n{quotes}\n"

    history_block = ""
    if history:
        for turn in history:
            role_tag = "user" if turn["role"] == "user" else "assistant"
            history_block += f"<|{role_tag}|>\n{turn['content']}<|end|>\n"

    return (
        f"<|system|>\n{NIETZSCHE_SYSTEM_PROMPT}{context_block}<|end|>\n"
        f"{history_block}"
        f"<|user|>\n{message}<|end|>\n"
        f"<|assistant|>\n"
    )


async def _call_vllm(
    message: str,
    context: list[str],
    history: list[dict] | None = None,
) -> AsyncGenerator[str, None]:
    """RunPod vLLM 엔드포인트 스트리밍 호출."""
    url = f"https://api.runpod.ai/v2/{settings.RUNPOD_ENDPOINT_ID}/stream"
    headers = {
        "Authorization": f"Bearer {settings.RUNPOD_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "input": {
            "prompt": _build_prompt(message, context, history),
            "max_new_tokens": 512,
            "temperature": 0.8,
            "stream": True,
        }
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        data = json.loads(raw)
                        token = data.get("token", {}).get("text", "")
                        if token:
                            yield token
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        logger.error("vLLM 호출 실패: %s", e)
        # 실패 시 Mock으로 fallback
        async for token in _mock_stream():
            yield token


# ───────────────────────────────────────────────────────
# Mock 스트리밍
# ───────────────────────────────────────────────────────

async def _mock_stream() -> AsyncGenerator[str, None]:
    """개발/테스트용 Mock 응답 스트리밍."""
    delay = 0.0 if settings.TESTING else _MOCK_DELAY
    for token in _MOCK_TOKENS:
        await asyncio.sleep(delay)
        yield token
