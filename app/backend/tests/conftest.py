"""
pytest 공통 픽스처 — 테스트 DB 세션, FastAPI 테스트 클라이언트 제공.

핵심 설계:
  - event_loop (session scope): 모든 async 픽스처와 테스트가 단일 이벤트 루프 공유
    → asyncpg 연결이 루프 간 이동하며 생기는 RuntimeError 방지
  - test_engine (session scope): 전체 1회 테이블 CREATE / DROP
  - db_session (function scope): 각 테스트에 새 세션 제공
  - clean_tables (autouse): 매 테스트 후 TRUNCATE CASCADE → 데이터 격리
"""

import asyncio
import os

import pytest
import pytest_asyncio
from dotenv import load_dotenv
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

load_dotenv(
    dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env.test"),
    override=True,
)

from main import app
from db.session import get_db
from models.base import Base
from models.user import User          # noqa: F401  — Base.metadata 등록
from models.chat import ChatRoom, ChatMessage  # noqa: F401

TEST_DATABASE_URL = os.environ["DATABASE_URL"]


# ──────────────────────────────────────────────
# 단일 이벤트 루프 (세션 전체 공유)
# ──────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """
    모든 테스트가 동일한 이벤트 루프를 사용하도록 강제.
    asyncpg connection pool이 루프를 넘나드는 문제를 방지.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ──────────────────────────────────────────────
# 세션 스코프: 엔진 + 테이블 생성/삭제 (전체 1회)
# ──────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


# ──────────────────────────────────────────────
# 함수 스코프: 각 테스트마다 새 세션
# ──────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session(test_engine):
    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


# ──────────────────────────────────────────────
# autouse: 매 테스트 후 모든 테이블 TRUNCATE
# ──────────────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def clean_tables(test_engine):
    """각 테스트 종료 후 모든 테이블 비움 (데이터 격리)."""
    yield

    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(
                text(f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE')
            )


# ──────────────────────────────────────────────
# FastAPI 테스트 클라이언트
# ──────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
