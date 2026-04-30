"""
DB 초기화 스크립트.

사용법:
  poetry run python db/reset_db.py           # 개발 DB 완전 초기화 (drop -> create)
  poetry run python db/reset_db.py --init    # 테이블만 생성 (없으면)
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine

from models.base import Base
from models.save import SaveSlot  # noqa: F401


def _get_db_url() -> str:
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    from dotenv import load_dotenv
    load_dotenv(env_path, override=True)

    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL이 .env에 없습니다.")
        sys.exit(1)
    return url


async def init_db(db_url: str) -> None:
    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        print("테이블 생성 중 (없는 경우에만)...")
        await conn.run_sync(Base.metadata.create_all)
        print("완료!")
    await engine.dispose()


async def reset_db(db_url: str) -> None:
    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        print("모든 테이블 삭제 중...")
        await conn.run_sync(Base.metadata.drop_all)
        print("테이블 재생성 중...")
        await conn.run_sync(Base.metadata.create_all)
        print("DB 초기화 완료!")
    await engine.dispose()


if __name__ == "__main__":
    args = sys.argv[1:]
    init_only = "--init" in args
    db_url = _get_db_url()

    print(f"대상 DB: {db_url.split('@')[-1]}")

    if init_only:
        asyncio.run(init_db(db_url))
    else:
        confirm = input("DB를 완전히 초기화합니다. 계속하시겠습니까? (yes/no): ")
        if confirm.strip().lower() != "yes":
            print("취소되었습니다.")
            sys.exit(0)
        asyncio.run(reset_db(db_url))
