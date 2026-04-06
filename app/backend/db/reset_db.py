"""
DB 초기화 스크립트.

사용법:
  poetry run python db/reset_db.py           # 개발 DB 완전 초기화 (drop → create)
  poetry run python db/reset_db.py --init    # 테이블만 생성 (없으면)
  poetry run python db/reset_db.py --test    # 테스트 DB 초기화

주의: reset은 모든 데이터가 삭제됩니다. 개발 환경 전용으로만 사용하세요.
"""

import asyncio
import sys
import os

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine

from models.base import Base
from models.user import User          # noqa: F401 — Base.metadata 등록용
from models.chat import ChatRoom, ChatMessage  # noqa: F401


def _get_db_url(use_test: bool) -> str:
    """환경변수에서 DB URL을 읽음."""
    env_file = ".env.test" if use_test else ".env"
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), env_file)

    from dotenv import load_dotenv
    load_dotenv(env_path, override=True)

    url = os.environ.get("DATABASE_URL")
    if not url:
        print(f"❌ DATABASE_URL이 {env_file}에 없습니다.")
        sys.exit(1)
    return url


async def init_db(db_url: str) -> None:
    """테이블이 없으면 생성 (기존 데이터 유지)."""
    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        print("🔨 테이블 생성 중 (없는 경우에만)...")
        await conn.run_sync(Base.metadata.create_all)
        print("✅ 완료!")
    await engine.dispose()


async def reset_db(db_url: str) -> None:
    """모든 테이블 삭제 후 재생성 — 데이터 전부 삭제."""
    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        print("⚠️  모든 테이블 삭제 중...")
        await conn.run_sync(Base.metadata.drop_all)
        print("🔨 테이블 재생성 중...")
        await conn.run_sync(Base.metadata.create_all)
        print("✅ DB 초기화 완료!")
    await engine.dispose()


if __name__ == "__main__":
    args = sys.argv[1:]
    use_test = "--test" in args
    init_only = "--init" in args

    label = "테스트" if use_test else "개발"
    db_url = _get_db_url(use_test)

    print(f"📦 대상 DB: [{label}] {db_url.split('@')[-1]}")  # 비밀번호 숨김

    if init_only:
        print("▶ 모드: 테이블 초기 생성")
        asyncio.run(init_db(db_url))
    else:
        confirm = input(f"⚠️  [{label}] DB를 완전히 초기화합니다. 계속하시겠습니까? (yes/no): ")
        if confirm.strip().lower() != "yes":
            print("취소되었습니다.")
            sys.exit(0)
        asyncio.run(reset_db(db_url))
