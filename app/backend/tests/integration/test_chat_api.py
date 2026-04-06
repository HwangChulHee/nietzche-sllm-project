"""
통합 테스트: /api/v1/chat 엔드포인트.

테스트 전략:
  - 각 테스트는 먼저 회원가입으로 token을 얻은 뒤 Authorization 헤더로 채팅 요청
  - clean_tables autouse 픽스처가 매 테스트 후 DB를 비움
  - TESTING=true → Mock LLM 지연 없음 (빠른 테스트)
"""

import json
import pytest
from httpx import AsyncClient
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.chat import ChatRoom, ChatMessage


# ── 헬퍼 ────────────────────────────────────────────

async def _create_user(client: AsyncClient, name: str = "니체_테스터") -> tuple[str, str]:
    """테스트용 사용자를 생성하고 (user_id, token)을 반환."""
    resp = await client.post(
        "/api/v1/user/signup",
        json={"name": name, "password": "password123"},
    )
    assert resp.status_code == 201, f"회원가입 실패: {resp.text}"
    data = resp.json()
    return data["id"], data["token"]


def _auth(token: str) -> dict:
    """Authorization 헤더 딕셔너리 반환."""
    return {"Authorization": f"Bearer {token}"}


async def _collect_sse(
    client: AsyncClient,
    method: str,
    url: str,
    token: str,
    **kwargs,
) -> list[dict]:
    """SSE 스트림을 모두 읽어 파싱된 이벤트 리스트로 반환."""
    events = []
    headers = {**_auth(token), **kwargs.pop("headers", {})}
    async with client.stream(method, url, headers=headers, **kwargs) as response:
        assert response.status_code == 200, f"HTTP {response.status_code}: {await response.aread()}"
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events


# ── GET /chat/test ───────────────────────────────────

class TestSseTestEndpoint:
    async def test_returns_200(self, client: AsyncClient):
        async with client.stream("GET", "/api/v1/chat/test") as resp:
            assert resp.status_code == 200

    async def test_content_type_is_event_stream(self, client: AsyncClient):
        async with client.stream("GET", "/api/v1/chat/test") as resp:
            assert "text/event-stream" in resp.headers["content-type"]

    async def test_data_contains_text_field(self, client: AsyncClient):
        events = []
        async with client.stream("GET", "/api/v1/chat/test") as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))
        assert all("text" in e for e in events)
        assert "니체" in "".join(e["text"] for e in events)


# ── POST /chat/ — 기본 동작 ──────────────────────────

class TestChatEndpoint:
    async def test_unauthorized_returns_403(self, client: AsyncClient):
        """토큰 없이 요청 → 403."""
        resp = await client.post(
            "/api/v1/chat/",
            json={"message": "안녕하세요"},
        )
        assert resp.status_code == 403

    async def test_invalid_token_returns_401(self, client: AsyncClient):
        """잘못된 토큰 → 401."""
        resp = await client.post(
            "/api/v1/chat/",
            json={"message": "안녕하세요"},
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401

    async def test_missing_message_returns_422(self, client: AsyncClient):
        """message 누락 → 422."""
        _, token = await _create_user(client, "검증_테스터")
        resp = await client.post(
            "/api/v1/chat/",
            json={},
            headers=_auth(token),
        )
        assert resp.status_code == 422

    async def test_empty_message_returns_422(self, client: AsyncClient):
        """빈 문자열 message → 422."""
        _, token = await _create_user(client, "빈메시지_테스터")
        resp = await client.post(
            "/api/v1/chat/",
            json={"message": ""},
            headers=_auth(token),
        )
        assert resp.status_code == 422


# ── POST /chat/ — SSE 스트리밍 ───────────────────────

class TestChatStreaming:
    async def test_sse_content_type(self, client: AsyncClient):
        """응답 Content-Type이 text/event-stream."""
        _, token = await _create_user(client, "sse_타입_테스터")
        async with client.stream(
            "POST", "/api/v1/chat/",
            json={"message": "삶이란 무엇인가?"},
            headers=_auth(token),
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]

    async def test_sse_event_sequence(self, client: AsyncClient):
        """이벤트 순서: init → token(1개 이상) → done."""
        _, token = await _create_user(client, "시퀀스_테스터")
        events = await _collect_sse(
            client, "POST", "/api/v1/chat/",
            token=token,
            json={"message": "고통이란 무엇인가?"},
        )

        types = [e["type"] for e in events]
        assert types[0] == "init",   "첫 이벤트는 init이어야 함"
        assert types[-1] == "done",  "마지막 이벤트는 done이어야 함"
        assert "token" in types,     "token 이벤트가 1개 이상 있어야 함"

    async def test_init_contains_room_id(self, client: AsyncClient):
        """init 이벤트에 room_id 포함."""
        _, token = await _create_user(client, "룸id_테스터")
        events = await _collect_sse(
            client, "POST", "/api/v1/chat/",
            token=token,
            json={"message": "초인이란?"},
        )
        init_event = events[0]
        assert init_event["type"] == "init"
        assert "room_id" in init_event
        assert init_event["room_id"]

    async def test_tokens_form_non_empty_text(self, client: AsyncClient):
        """token 이벤트들을 합치면 비어있지 않은 응답."""
        _, token = await _create_user(client, "텍스트_테스터")
        events = await _collect_sse(
            client, "POST", "/api/v1/chat/",
            token=token,
            json={"message": "힘에의 의지란?"},
        )
        full_text = "".join(e["text"] for e in events if e["type"] == "token")
        assert len(full_text) > 0


# ── POST /chat/ — DB 저장 검증 ───────────────────────

class TestChatPersistence:
    async def test_new_chat_creates_room(self, client: AsyncClient, db_session: AsyncSession):
        """새 채팅 → ChatRoom 생성."""
        _, token = await _create_user(client, "룸생성_테스터")
        events = await _collect_sse(
            client, "POST", "/api/v1/chat/",
            token=token,
            json={"message": "영겁회귀란?"},
        )
        room_id = events[0]["room_id"]

        result = await db_session.execute(
            select(ChatRoom).where(ChatRoom.id == room_id)
        )
        room = result.scalar_one_or_none()
        assert room is not None
        assert "영겁회귀" in room.title

    async def test_chat_saves_both_messages(self, client: AsyncClient, db_session: AsyncSession):
        """채팅 완료 후 user + assistant 메시지가 DB에 저장됨."""
        _, token = await _create_user(client, "메시지저장_테스터")
        events = await _collect_sse(
            client, "POST", "/api/v1/chat/",
            token=token,
            json={"message": "운명애란 무엇인가?"},
        )
        room_id = events[0]["room_id"]

        result = await db_session.execute(
            select(ChatMessage)
            .where(ChatMessage.room_id == room_id)
            .order_by(ChatMessage.id)
        )
        messages = result.scalars().all()

        assert len(messages) == 2,              "user + assistant 메시지 2개"
        assert messages[0].role == "user"
        assert messages[0].content == "운명애란 무엇인가?"
        assert messages[1].role == "assistant"
        assert len(messages[1].content) > 0

    async def test_continue_existing_room(self, client: AsyncClient, db_session: AsyncSession):
        """기존 room_id로 대화 이어가기 → 메시지 누적."""
        _, token = await _create_user(client, "대화연속_테스터")

        events1 = await _collect_sse(
            client, "POST", "/api/v1/chat/",
            token=token,
            json={"message": "첫 번째 질문"},
        )
        room_id = events1[0]["room_id"]

        await _collect_sse(
            client, "POST", "/api/v1/chat/",
            token=token,
            json={"message": "두 번째 질문", "room_id": room_id},
        )

        result = await db_session.execute(
            select(ChatMessage)
            .where(ChatMessage.room_id == room_id)
            .order_by(ChatMessage.id)
        )
        messages = result.scalars().all()
        assert len(messages) == 4, "메시지 4개 (user+assistant × 2회)"

    async def test_wrong_room_id_returns_404(self, client: AsyncClient):
        """타인의 room_id로 접근 시 404."""
        _, token = await _create_user(client, "권한_테스터")
        resp = await client.post(
            "/api/v1/chat/",
            json={"message": "질문", "room_id": str(uuid4())},
            headers=_auth(token),
        )
        assert resp.status_code == 404
