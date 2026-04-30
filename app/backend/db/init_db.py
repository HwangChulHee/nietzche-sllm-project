import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.base import Base
from models.save import SaveSlot  # noqa: F401
from db.session import engine


async def init_models():
    async with engine.begin() as conn:
        print("테이블 생성 중...")
        await conn.run_sync(Base.metadata.create_all)
        print("테이블 생성 완료!")


if __name__ == "__main__":
    asyncio.run(init_models())
