"""
llm_client.py — 저수준 LLM 스트리밍 추상화.

LLM_MODE 환경변수로 구현체 전환:
  - mock → MockLLMClient (개발용, 고정 응답)
  - vllm → VLLMClient (실제 vLLM 서버)

이 모듈은 *원시* 메시지 리스트 → 토큰 스트리밍만 담당.
화면별 페르소나 / 해설 / 요약 같은 sLLM 컨텍스트 조립은
`services/sllm_clients.py`에서 처리한다.
"""

import asyncio
import random
from abc import ABC, abstractmethod
from typing import AsyncIterator

from core.config import settings


# ───────────────────────────────────────────────────────
# 추상 클래스
# ───────────────────────────────────────────────────────

class LLMClient(ABC):
    @abstractmethod
    async def stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        ...


# ───────────────────────────────────────────────────────
# Mock 구현체 — 일반 폴백용. sLLM별 Mock은 sllm_clients.py 참조.
# ───────────────────────────────────────────────────────

_MOCK_FALLBACK = [
    "그대의 말이 길에 닿는다. 잠시 호흡을 가다듬으라.",
    "길은 흐른다. 그대의 물음도 그렇게 흘러간다.",
]


class MockLLMClient(LLMClient):
    async def stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        response = random.choice(_MOCK_FALLBACK)
        for char in response:
            yield char
            await asyncio.sleep(0.03)


# ───────────────────────────────────────────────────────
# vLLM 구현체 (OpenAI SDK)
# ───────────────────────────────────────────────────────

class VLLMClient(LLMClient):
    """OpenAI 호환 API 호출. Phase 9에서 실 연결, Phase 2~8에선 미사용."""

    def __init__(self, base_url: str, api_key: str, model: str):
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self.model = model

    async def stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            temperature=0.5,
            max_tokens=1500,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


# ───────────────────────────────────────────────────────
# 팩토리 (싱글턴)
# ───────────────────────────────────────────────────────

_client_instance: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """LLM_MODE에 따라 저수준 LLMClient 반환 (싱글턴)."""
    global _client_instance
    if _client_instance is not None:
        return _client_instance

    if settings.LLM_MODE == "vllm":
        _client_instance = VLLMClient(
            base_url=settings.VLLM_BASE_URL,
            api_key=settings.VLLM_API_KEY,
            model=settings.VLLM_MODEL,
        )
    else:
        _client_instance = MockLLMClient()

    return _client_instance
