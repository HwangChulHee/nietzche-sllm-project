"""
sllm_clients.py — sLLM별 고수준 클라이언트 (페르소나 / 해설 / 요약).

각 sLLM은 *Mock 구현체* 와 *VLLM 구현체* 두 가지를 가지며,
환경변수 `LLM_MODE`로 토글한다.

  - LLM_MODE=mock : `services/mock_data.py` 의 풀에서 응답 yield
  - LLM_MODE=vllm : 시스템 프롬프트 + 화면 컨텍스트 조립 → VLLMClient 호출 (Phase 9)

Phase 2 시점에선 Mock 구현만 검증한다. VLLM 구현은 구조만 갖추고
LLM_MODE=vllm 토글은 Phase 9에서.
"""

import asyncio
import random
from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncIterator

from core.config import settings
from services import mock_data
from services.llm_client import LLMClient, get_llm_client


# ───────────────────────────────────────────────────────
# 시스템 프롬프트 로더 (파일 → 메모리 캐시)
# ───────────────────────────────────────────────────────

_prompt_cache: dict[str, str] = {}


def _load_prompt(relative_path: str) -> str:
    if relative_path in _prompt_cache:
        return _prompt_cache[relative_path]
    base_dir = Path(__file__).parent.parent
    path = base_dir / relative_path
    if not path.exists():
        raise FileNotFoundError(f"system prompt 파일 없음: {path}")
    text = path.read_text(encoding="utf-8").strip()
    _prompt_cache[relative_path] = text
    return text


# ───────────────────────────────────────────────────────
# Mock 스트리밍 헬퍼
# ───────────────────────────────────────────────────────

async def _mock_stream(text: str, delay: float = 0.025) -> AsyncIterator[str]:
    for char in text:
        yield char
        await asyncio.sleep(delay)


def _count_assistant_turns(history: list[dict]) -> int:
    return sum(1 for m in history if m.get("role") == "assistant")


# ═══════════════════════════════════════════════════════
# Persona — 차라투스트라
# ═══════════════════════════════════════════════════════

class PersonaClient(ABC):
    @abstractmethod
    async def stream_respond(
        self, screen_id: str, history: list[dict], user_message: str, *, silent: bool
    ) -> AsyncIterator[str]: ...

    @abstractmethod
    async def stream_auto_first(
        self, screen_id: str, history: list[dict]
    ) -> AsyncIterator[str]: ...

    @abstractmethod
    async def stream_farewell(
        self, screen_id: str, history: list[dict]
    ) -> AsyncIterator[str]: ...


class MockPersonaClient(PersonaClient):
    async def stream_respond(self, screen_id, history, user_message, *, silent):
        if silent:
            text = random.choice(mock_data.PERSONA_SILENT_REPLIES)
        else:
            replies = mock_data.PERSONA_REPLIES.get(
                screen_id, mock_data.PERSONA_REPLIES["default"]
            )
            idx = _count_assistant_turns(history) % len(replies)
            text = replies[idx]
        async for chunk in _mock_stream(text):
            yield chunk

    async def stream_auto_first(self, screen_id, history):
        text = mock_data.PERSONA_AUTO_FIRST.get(
            screen_id, "길은 흐른다."
        )
        async for chunk in _mock_stream(text):
            yield chunk

    async def stream_farewell(self, screen_id, history):
        text = mock_data.PERSONA_FAREWELL.get(
            screen_id, mock_data.PERSONA_FAREWELL["default"]
        )
        async for chunk in _mock_stream(text):
            yield chunk


class VLLMPersonaClient(PersonaClient):
    """vLLM 백엔드 호출. Phase 9에서 검증."""

    def __init__(self, llm: LLMClient, base_prompt: str):
        self.llm = llm
        self.base_prompt = base_prompt

    def _compose_system(self, screen_id: str, *, mode: str) -> str:
        # Phase 9에서 화면별 컨텍스트 슬롯 채우기
        return f"{self.base_prompt}\n\n# 현재 화면\n{screen_id}\n# 모드\n{mode}"

    async def stream_respond(self, screen_id, history, user_message, *, silent):
        system = self._compose_system(screen_id, mode="silent" if silent else "reply")
        messages = [{"role": "system", "content": system}, *history]
        if silent:
            messages.append({"role": "user", "content": "[침묵]"})
        else:
            messages.append({"role": "user", "content": user_message})
        async for delta in self.llm.stream_chat(messages):
            yield delta

    async def stream_auto_first(self, screen_id, history):
        system = self._compose_system(screen_id, mode="auto_first")
        messages = [{"role": "system", "content": system}, *history]
        messages.append({"role": "user", "content": "[화면 진입 — 자동 발화]"})
        async for delta in self.llm.stream_chat(messages):
            yield delta

    async def stream_farewell(self, screen_id, history):
        system = self._compose_system(screen_id, mode="farewell")
        messages = [{"role": "system", "content": system}, *history]
        messages.append({"role": "user", "content": "[작별 — 마지막 발화]"})
        async for delta in self.llm.stream_chat(messages):
            yield delta


# ═══════════════════════════════════════════════════════
# Explain — 외부 해설자
# ═══════════════════════════════════════════════════════

class ExplainClient(ABC):
    @abstractmethod
    async def stream_explain(
        self, screen_id: str, query: str, history: list[dict]
    ) -> AsyncIterator[str]: ...


class MockExplainClient(ExplainClient):
    async def stream_explain(self, screen_id, query, history):
        text = mock_data.EXPLAIN_RESPONSES.get(
            screen_id, mock_data.EXPLAIN_RESPONSES["default"]
        )
        async for chunk in _mock_stream(text):
            yield chunk


class VLLMExplainClient(ExplainClient):
    def __init__(self, llm: LLMClient, base_prompt: str):
        self.llm = llm
        self.base_prompt = base_prompt

    async def stream_explain(self, screen_id, query, history):
        system = (
            f"{self.base_prompt}\n\n"
            f"# 현재 화면\n{screen_id}\n"
            f"# 학습자 질문\n{query}"
        )
        messages = [{"role": "system", "content": system}, *history]
        messages.append({"role": "user", "content": query})
        async for delta in self.llm.stream_chat(messages):
            yield delta


# ═══════════════════════════════════════════════════════
# Summary — 차라투스트라 1인칭 회상
# ═══════════════════════════════════════════════════════

class SummaryClient(ABC):
    @abstractmethod
    async def stream_summarize(
        self, history: list[dict], episode: str, scene_index: int
    ) -> AsyncIterator[str]: ...


class MockSummaryClient(SummaryClient):
    async def stream_summarize(self, history, episode, scene_index):
        async for chunk in _mock_stream(mock_data.SUMMARY_TEMPLATE):
            yield chunk


class VLLMSummaryClient(SummaryClient):
    def __init__(self, llm: LLMClient, base_prompt: str):
        self.llm = llm
        self.base_prompt = base_prompt

    async def stream_summarize(self, history, episode, scene_index):
        history_text = "\n".join(
            f"{m.get('role', '?')}: {m.get('content', '')}" for m in history
        )
        system = self.base_prompt
        user = f"{episode} 화면 #{scene_index} 까지의 동행을 회상하라.\n\n# 대화 이력\n{history_text}"
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        async for delta in self.llm.stream_chat(messages):
            yield delta


# ═══════════════════════════════════════════════════════
# 팩토리 (싱글턴)
# ═══════════════════════════════════════════════════════

_persona_instance: PersonaClient | None = None
_explain_instance: ExplainClient | None = None
_summary_instance: SummaryClient | None = None


def get_persona_client() -> PersonaClient:
    global _persona_instance
    if _persona_instance is not None:
        return _persona_instance
    if settings.LLM_MODE == "vllm":
        _persona_instance = VLLMPersonaClient(
            llm=get_llm_client(),
            base_prompt=_load_prompt(settings.PERSONA_PROMPT_FILE),
        )
    else:
        _persona_instance = MockPersonaClient()
    return _persona_instance


def get_explain_client() -> ExplainClient:
    global _explain_instance
    if _explain_instance is not None:
        return _explain_instance
    if settings.LLM_MODE == "vllm":
        _explain_instance = VLLMExplainClient(
            llm=get_llm_client(),
            base_prompt=_load_prompt(settings.EXPLAIN_PROMPT_FILE),
        )
    else:
        _explain_instance = MockExplainClient()
    return _explain_instance


def get_summary_client() -> SummaryClient:
    global _summary_instance
    if _summary_instance is not None:
        return _summary_instance
    if settings.LLM_MODE == "vllm":
        _summary_instance = VLLMSummaryClient(
            llm=get_llm_client(),
            base_prompt=_load_prompt(settings.SUMMARY_PROMPT_FILE),
        )
    else:
        _summary_instance = MockSummaryClient()
    return _summary_instance
