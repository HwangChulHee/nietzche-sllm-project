"""
llm_client.py — LLM 클라이언트 추상화.

LLM_MODE 환경변수로 구현체 전환:
  - mock → MockLLMClient (개발용)
  - vllm → VLLMClient (실제 vLLM 서버)
"""

import asyncio
import random
from abc import ABC, abstractmethod
from pathlib import Path
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
# Mock 구현체
# ───────────────────────────────────────────────────────

_MOCK_RESPONSES = [
    (
        "그대는 지금 권태의 심연을 들여다보고 있구나. "
        "하지만 권태야말로 위대한 사상이 잉태되는 자궁이다. "
        "이 무의미함을 직시하라. 그것이 그대를 더 강하게 만들 것이다."
    ),
    (
        "고통이란 무엇인가? 그것은 삶이 그대에게 건네는 질문이다. "
        "Amor Fati — 그대의 운명을 사랑하라. "
        "고통 속에서 도망치는 자는 영원히 노예로 남는다."
    ),
    (
        "인간은 극복되어야 할 무언가이다. "
        "그대가 지금 느끼는 혼란은 Übermensch를 향한 산고(産苦)다. "
        "스스로의 가치를 창조하라. 기존의 도덕에 기대지 마라."
    ),
    (
        "영겁회귀를 상상하라 — 지금 이 순간이 영원히 반복된다면, "
        "그대는 이 삶을 기꺼이 다시 살겠는가? "
        "그 질문에 '그렇다'고 답할 수 있을 때, 그대는 자유롭다."
    ),
    (
        "그대의 질문은 나를 심연으로 데려간다. "
        "인간은 극복되어야 할 무언가이다. "
        "그대가 고통 속에 있다면, 그것은 그대가 아직 살아있다는 증거다. "
        "Amor Fati — 그대의 운명을 사랑하라."
    ),
]


class MockLLMClient(LLMClient):
    """개발용. 미리 준비한 가짜 응답을 한 글자씩 yield."""

    async def stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        response = random.choice(_MOCK_RESPONSES)
        for char in response:
            yield char
            await asyncio.sleep(0.03)


# ───────────────────────────────────────────────────────
# vLLM 구현체 (OpenAI SDK)
# ───────────────────────────────────────────────────────

class VLLMClient(LLMClient):
    """실제 vLLM 서버 호출. OpenAI 호환 API 사용."""

    def __init__(self, base_url: str, api_key: str, model: str):
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        self.model = model

    async def stream_chat(self, messages: list[dict]) -> AsyncIterator[str]:
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
            temperature=0.8,
            max_tokens=512,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


# ───────────────────────────────────────────────────────
# 팩토리 + 시스템 프롬프트 로더
# ───────────────────────────────────────────────────────

_client_instance: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """LLM_MODE에 따라 적절한 클라이언트 반환 (싱글턴)."""
    global _client_instance
    if _client_instance is not None:
        return _client_instance

    if settings.LLM_MODE == "vllm":
        _client_instance = VLLMClient(
            base_url=settings.LLM_BASE_URL,
            api_key=settings.LLM_API_KEY,
            model=settings.LLM_MODEL,
        )
    else:
        _client_instance = MockLLMClient()

    return _client_instance


_system_prompt_cache: str | None = None


def load_system_prompt() -> str:
    """시스템 프롬프트 파일을 로드하고 캐시."""
    global _system_prompt_cache
    if _system_prompt_cache is not None:
        return _system_prompt_cache

    base_dir = Path(__file__).parent.parent
    prompt_path = base_dir / settings.SYSTEM_PROMPT_FILE

    if prompt_path.exists():
        _system_prompt_cache = prompt_path.read_text(encoding="utf-8").strip()
    else:
        fallback = base_dir / "prompts" / "default.txt"
        _system_prompt_cache = fallback.read_text(encoding="utf-8").strip()

    return _system_prompt_cache
