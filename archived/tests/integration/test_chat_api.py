"""
통합 테스트: /api/v1/chat 엔드포인트.
인증 없는 구조로 변경됨.
"""

import json
import pytest
from httpx import AsyncClient
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.chat import Conversation, Message


async def _collect_sse(client: AsyncClient, **kwargs) -> list[dict]:
    events = []
    async with client.stream("POST", "/api/v1/chat", **kwargs) as response:
        assert response.status_code == 200
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                events.append(json.loads(line[6:]))
    return events


class TestChatEndpoint:
    async def test_missing_message_returns_422(self, client: AsyncClient):
        resp = await client.post("/api/v1/chat", json={})
        assert resp.status_code == 422

    async def test_empty_message_returns_422(self, client: AsyncClient):
        resp = await client.post("/api/v1/chat", json={"message": ""})
        assert resp.status_code == 422


class TestChatStreaming:
    async def test_sse_content_type(self, client: AsyncClient):
        async with client.stream(
            "POST", "/api/v1/chat",
            json={"message": "삶이란 무엇인가?"},
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]

    async def test_sse_event_sequence(self, client: AsyncClient):
        events = await _collect_sse(
            client, json={"message": "고통이란 무엇인가?"},
        )
        types = [e["type"] for e in events]
        assert types[0] == "metadata"
        assert types[-1] == "done"
        assert "delta" in types

    async def test_metadata_contains_conversation_id(self, client: AsyncClient):
        events = await _collect_sse(
            client, json={"message": "초인이란?"},
        )
        meta = events[0]
        assert meta["type"] == "metadata"
        assert "conversation_id" in meta
        assert meta["conversation_id"]

    async def test_deltas_form_non_empty_text(self, client: AsyncClient):
        events = await _collect_sse(
            client, json={"message": "힘에의 의지란?"},
        )
        full_text = "".join(e["content"] for e in events if e["type"] == "delta")
        assert len(full_text) > 0


class TestChatPersistence:
    async def test_new_chat_creates_conversation(self, client: AsyncClient, db_session: AsyncSession):
        events = await _collect_sse(
            client, json={"message": "영겁회귀란?"},
        )
        conv_id = events[0]["conversation_id"]

        result = await db_session.execute(
            select(Conversation).where(Conversation.id == conv_id)
        )
        conv = result.scalar_one_or_none()
        assert conv is not None

    async def test_chat_saves_both_messages(self, client: AsyncClient, db_session: AsyncSession):
        events = await _collect_sse(
            client, json={"message": "운명애란 무엇인가?"},
        )
        conv_id = events[0]["conversation_id"]

        result = await db_session.execute(
            select(Message)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.created_at)
        )
        messages = result.scalars().all()

        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "운명애란 무엇인가?"
        assert messages[1].role == "assistant"
        assert len(messages[1].content) > 0

    async def test_continue_existing_conversation(self, client: AsyncClient, db_session: AsyncSession):
        events1 = await _collect_sse(
            client, json={"message": "첫 번째 질문"},
        )
        conv_id = events1[0]["conversation_id"]

        await _collect_sse(
            client,
            json={"message": "두 번째 질문", "conversation_id": conv_id},
        )

        result = await db_session.execute(
            select(Message)
            .where(Message.conversation_id == conv_id)
            .order_by(Message.created_at)
        )
        messages = result.scalars().all()
        assert len(messages) == 4

    async def test_wrong_conversation_id_returns_404(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/chat",
            json={"message": "질문", "conversation_id": str(uuid4())},
        )
        assert resp.status_code == 404


class TestGetMessages:
    async def test_get_conversation_messages(self, client: AsyncClient):
        events = await _collect_sse(
            client, json={"message": "테스트 질문"},
        )
        conv_id = events[0]["conversation_id"]

        resp = await client.get(f"/api/v1/conversations/{conv_id}/messages")
        assert resp.status_code == 200
        data = resp.json()
        assert data["conversation_id"] == conv_id
        assert len(data["messages"]) == 2

    async def test_unknown_conversation_returns_404(self, client: AsyncClient):
        resp = await client.get(f"/api/v1/conversations/{uuid4()}/messages")
        assert resp.status_code == 404


class TestHealthCheck:
    async def test_health_endpoint(self, client: AsyncClient):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
